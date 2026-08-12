"""Query models on a leaderboard prompt set, score them, and log everything.

Same submission output as run_models.py -- JSONL {id, prediction} per model in
--outdir -- plus a per-call raw log: response text, reasoning trace, token
counts, latency, retries and finish_reason.

Three providers:
    OPENAI_API_KEY=... python run_models_logged.py \
        --set data/hard_v2.jsonl --provider openai --models o4-mini --score

    ANTHROPIC_API_KEY=... python run_models_logged.py \
        --set data/hard_v2.jsonl --provider anthropic --models claude-opus-5 --score

    python run_models_logged.py --set data/hard_v2.jsonl --provider ollama \
        --models qwen2.5-coder:32b --score

Pilot a set before committing to a full run:
    ... --set data/hard_v2.jsonl --models o4-mini --limit 20

Batch mode (--batch) submits the whole set to the provider's Batch API at 50%
of standard price, with a 24h completion window. Same outputs, same scoring;
submit and collect can be separate invocations:
    ... --models o4-mini --batch --submit-only     # submit, exit
    ... --models o4-mini --batch                   # resume: poll + collect

Writes to --logdir (default <outdir>/logs):
    <model>.raw.jsonl          one record per call
    <model>.stats.json         totals: tokens, wall time, failures, accuracy
    <model>.batch_state.json   batch mode only; removed once outputs are written

In sync mode the raw log is appended and flushed per call, so a run that dies
at prompt 600/720 keeps its first 600 records; --resume skips ids already in it.
In batch mode it is written in one go when the batch is collected.

Reasoning traces differ by provider. Anthropic returns a summarized thinking
trace as content, logged in full as "reasoning_text"; OpenAI's o-series and
gpt-5 do NOT return their hidden chain of thought, so "text" is the visible
answer and "reasoning_tokens" is the only measure of the hidden part.
Conversely Anthropic bills thinking inside output_tokens without breaking it
out, so reasoning_tokens is null there. Neither provider gives you both.
"""
import argparse
import datetime
import json
import os
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from nafbench.answer import parse_answer, parse_answer_reasoning  # noqa
from leaderboard.evaluate import evaluate, normalize  # noqa

REASONING_PREFIXES = ("gpt-5", "o1", "o3", "o4", "deepseek-r1", "claude")

# Anthropic models taking adaptive thinking. Older ones (haiku-4-5, sonnet-4-5,
# opus-4-5) need {"type": "enabled", "budget_tokens": N}; on these that shape
# returns a 400.
ADAPTIVE_THINKING = (
    "claude-opus-5", "claude-opus-4-8", "claude-opus-4-7", "claude-opus-4-6",
    "claude-sonnet-5", "claude-sonnet-4-6", "claude-fable-5", "claude-mythos-5",
)

OPENAI_TERMINAL = {"completed", "failed", "expired", "cancelled"}


def safe_name(model):
    return model.replace("/", "_").replace(":", "_")


def _openai_is_reasoning(model):
    return any(model.startswith(p) for p in ("gpt-5", "o1", "o3", "o4"))


# ------------------------------------------------------- request builders
# Single source of truth for what goes on the wire. The sync path passes these
# straight to create()/stream(); the batch path embeds them in a batch request.
# Keeping one builder per provider is what stops sync and batch results from
# quietly diverging.

def build_openai_body(model, prompt, args):
    msgs = [{"role": "user", "content": prompt}]
    if _openai_is_reasoning(model):
        # reasoning models reject temperature; the budget covers hidden reasoning
        return {"model": model, "messages": msgs,
                "max_completion_tokens": args.max_completion_tokens}
    body = {"model": model, "messages": msgs,
            "temperature": args.temperature, "max_tokens": args.max_tokens}
    if args.top_p is not None:
        body["top_p"] = args.top_p
    return body


def thinking_config(model, args):
    """Anthropic thinking param, or None to leave it at the model default."""
    if args.no_thinking:
        return {"type": "disabled"}
    if any(model.startswith(p) for p in ADAPTIVE_THINKING):
        # display="summarized" opts back into readable reasoning; the default
        # ("omitted") streams thinking blocks with empty text
        return {"type": "adaptive", "display": "summarized"}
    # pre-4.6 models: fixed budget, must be < max_tokens and >= 1024
    budget = max(1024, min(args.thinking_budget, args.max_completion_tokens - 1024))
    return {"type": "enabled", "budget_tokens": budget}


def build_anthropic_params(model, prompt, args):
    # no temperature: current Claude models reject non-default sampling params
    params = {"model": model, "max_tokens": args.max_completion_tokens,
              "messages": [{"role": "user", "content": prompt}]}
    thinking = thinking_config(model, args)
    if thinking:
        params["thinking"] = thinking
    if args.effort:
        params["output_config"] = {"effort": args.effort}
    return params


# ------------------------------------------------------ response -> record
# Both providers deliver the same data in different wrappers depending on
# sync vs batch, so each is normalized exactly once.

def _meta_openai(body):
    """body: a chat.completion as a plain dict (sync: .model_dump(), batch: JSON).
    Returns (text, meta)."""
    u = body.get("usage") or {}
    det = u.get("completion_tokens_details") or {}
    pdet = u.get("prompt_tokens_details") or {}
    choice = (body.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    meta = {
        "prompt_tokens": u.get("prompt_tokens"),
        "completion_tokens": u.get("completion_tokens"),
        "reasoning_tokens": det.get("reasoning_tokens"),
        "cached_prompt_tokens": pdet.get("cached_tokens"),
        "cache_write_tokens": None,
        "finish_reason": choice.get("finish_reason"),
    }
    # deepseek / some ollama builds do expose the reasoning text
    for field in ("reasoning_content", "reasoning"):
        val = msg.get(field)
        if isinstance(val, str) and val:
            meta["reasoning_text"] = val
            break
    return msg.get("content"), meta


def _meta_anthropic(msg):
    """msg: an anthropic Message (sync and batch both yield one).
    Returns (text, meta)."""
    text = "\n".join(b.text for b in msg.content if b.type == "text")
    trace = "\n".join(b.thinking for b in msg.content
                      if b.type == "thinking" and getattr(b, "thinking", ""))
    u = msg.usage
    meta = {
        "prompt_tokens": getattr(u, "input_tokens", None),
        # thinking is billed inside output_tokens and not broken out
        "completion_tokens": getattr(u, "output_tokens", None),
        "reasoning_tokens": None,
        "cached_prompt_tokens": getattr(u, "cache_read_input_tokens", None),
        "cache_write_tokens": getattr(u, "cache_creation_input_tokens", None),
        "finish_reason": msg.stop_reason,
    }
    if trace:
        meta["reasoning_text"] = trace
    if msg.stop_reason == "refusal" and getattr(msg, "stop_details", None):
        meta["stop_details"] = msg.stop_details.to_dict()
    return text, meta


def _empty_meta(finish_reason, errors):
    return {"prompt_tokens": None, "completion_tokens": None, "reasoning_tokens": None,
            "cached_prompt_tokens": None, "cache_write_tokens": None,
            "finish_reason": finish_reason, "errors": errors}


# ------------------------------------------------------------ sync driver

def ask_openai(client, model, prompt, args):
    t0, errors = time.time(), []
    body = build_openai_body(model, prompt, args)
    for attempt in range(args.retries):
        try:
            r = client.chat.completions.create(**body)
            text, meta = _meta_openai(r.model_dump())
            meta.update({"latency_s": round(time.time() - t0, 2),
                         "attempts": attempt + 1, "errors": errors})
            return text, meta
        except Exception as e:  # noqa
            errors.append(f"{type(e).__name__}: {e}")
            if attempt == args.retries - 1:
                meta = _empty_meta("error", errors)
                meta.update({"latency_s": round(time.time() - t0, 2),
                             "attempts": attempt + 1})
                return f"<error: {e}>", meta
            time.sleep(2 * (attempt + 1))


def ask_anthropic(client, model, prompt, args):
    """Streams so a large max_tokens can't trip the SDK's timeout guard."""
    t0, errors = time.time(), []
    params = build_anthropic_params(model, prompt, args)
    for attempt in range(args.retries):
        try:
            with client.messages.stream(**params) as stream:
                msg = stream.get_final_message()
            text, meta = _meta_anthropic(msg)
            meta.update({"latency_s": round(time.time() - t0, 2),
                         "attempts": attempt + 1, "errors": errors})
            return text, meta
        except Exception as e:  # noqa
            errors.append(f"{type(e).__name__}: {e}")
            if attempt == args.retries - 1:
                meta = _empty_meta("error", errors)
                meta.update({"latency_s": round(time.time() - t0, 2),
                             "attempts": attempt + 1})
                return f"<error: {e}>", meta
            time.sleep(2 * (attempt + 1))


def make_client(args):
    if args.provider == "anthropic":
        import anthropic
        # api_key=None lets the SDK resolve ANTHROPIC_AUTH_TOKEN or an
        # `ant auth login` profile
        key = os.environ.get("ANTHROPIC_API_KEY")
        return anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()
    from openai import OpenAI
    if args.provider == "ollama":
        return OpenAI(base_url=os.environ.get("OLLAMA_BASE_URL",
                                              "http://localhost:11434/v1"),
                      api_key="ollama")
    key = os.environ.get("OPENAI_API_KEY") or sys.exit("OPENAI_API_KEY not set")
    return OpenAI(base_url=os.environ.get("OPENAI_BASE_URL"), api_key=key)


def record_for(it, text, meta, parse):
    rec = {"id": it["id"], "prediction": parse(text), "text": text}
    for k in ("rec_id", "axis", "difficulty", "cond"):
        if k in it:
            rec[k] = it[k]
    rec.update(meta)
    return rec


def run_sync(model, items, raw_path, args):
    client = make_client(args)
    ask = ask_anthropic if args.provider == "anthropic" else ask_openai
    parse = parse_answer_reasoning if any(
        model.startswith(p) for p in REASONING_PREFIXES) else parse_answer
    preds, metas = {}, []
    lock = threading.Lock()
    raw_f = open(raw_path, "a" if args.resume else "w")

    def do(it):
        txt, meta = ask(client, model, it["prompt"], args)
        rec = record_for(it, txt, meta, parse)
        with lock:
            raw_f.write(json.dumps(rec) + "\n")
            raw_f.flush()
        return it["id"], rec["prediction"], meta

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(do, it) for it in items]
        for i, f in enumerate(as_completed(futs), 1):
            tid, ans, meta = f.result()
            preds[tid] = ans
            metas.append(meta)
            if i % args.progress_every == 0 or i == len(items):
                ct = sum(m["completion_tokens"] or 0 for m in metas)
                print(f"  [{model}] {i}/{len(items)}  {ct} output tok  "
                      f"{time.time() - t0:.0f}s", flush=True)
    raw_f.close()
    return preds, metas, time.time() - t0


# ----------------------------------------------------------- batch driver

def batch_state_path(logdir, model):
    return os.path.join(logdir, safe_name(model) + ".batch_state.json")


def save_state(path, state):
    tmp = path + ".tmp"
    json.dump(state, open(tmp, "w"), indent=1)
    os.replace(tmp, path)


def params_fingerprint(args):
    """Params that change what the model is asked. A resume against a state
    file with a different fingerprint is refused rather than silently mixing
    differently-parameterized results."""
    return {"max_completion_tokens": args.max_completion_tokens,
            "max_tokens": args.max_tokens, "effort": args.effort,
            "no_thinking": args.no_thinking, "thinking_budget": args.thinking_budget}


def batch_submit(client, model, items, cids, args):
    """Returns (batch_id, input_file_id)."""
    if args.provider == "openai":
        lines = [json.dumps({"custom_id": cid, "method": "POST",
                             "url": "/v1/chat/completions",
                             "body": build_openai_body(model, it["prompt"], args)})
                 for cid, it in zip(cids, items)]
        f = client.files.create(
            file=(safe_name(model) + ".batch.jsonl", "\n".join(lines).encode()),
            purpose="batch")
        b = client.batches.create(input_file_id=f.id,
                                  endpoint="/v1/chat/completions",
                                  completion_window="24h")
        return b.id, f.id
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
    reqs = [Request(custom_id=cid,
                    params=MessageCreateParamsNonStreaming(
                        **build_anthropic_params(model, it["prompt"], args)))
            for cid, it in zip(cids, items)]
    b = client.messages.batches.create(requests=reqs)
    return b.id, None


def batch_check(client, batch_id, provider):
    """Returns (batch, status, human-readable counts)."""
    if provider == "openai":
        b = client.batches.retrieve(batch_id)
        rc = b.request_counts
        counts = f"{rc.completed}/{rc.total} done, {rc.failed} failed" if rc else "?"
        return b, b.status, counts
    b = client.messages.batches.retrieve(batch_id)
    rc = b.request_counts
    counts = f"{rc.succeeded} ok, {rc.errored} err, {rc.processing} processing"
    return b, ("completed" if b.processing_status == "ended" else b.processing_status), counts


def batch_fetch(client, batch, provider):
    """Returns {custom_id: (text, meta, error)}."""
    out = {}
    if provider == "openai":
        for file_id in (batch.output_file_id, batch.error_file_id):
            if not file_id:
                continue
            for line in client.files.content(file_id).text.splitlines():
                if not line.strip():
                    continue
                obj = json.loads(line)
                cid, resp = obj["custom_id"], obj.get("response")
                if obj.get("error"):
                    out[cid] = (None, None, json.dumps(obj["error"]))
                elif resp and resp.get("status_code") == 200:
                    text, meta = _meta_openai(resp["body"])
                    out[cid] = (text, meta, None)
                else:
                    out[cid] = (None, None,
                                f"http {resp.get('status_code') if resp else '?'}")
        return out
    for result in client.messages.batches.results(batch.id):
        cid, rtype = result.custom_id, result.result.type
        if rtype == "succeeded":
            text, meta = _meta_anthropic(result.result.message)
            out[cid] = (text, meta, None)
        elif rtype == "errored":
            out[cid] = (None, None, str(result.result.error))
        else:  # canceled / expired
            out[cid] = (None, None, rtype)
    return out


def batch_submit_or_resume(client, model, items, args, logdir):
    spath = batch_state_path(logdir, model)
    if os.path.exists(spath) and not args.force:
        state = json.load(open(spath))
        if state["set"] != os.path.abspath(args.set):
            sys.exit(f"{spath} is for set {state['set']}, not {os.path.abspath(args.set)}; "
                     f"use --force to resubmit or point --logdir elsewhere")
        if state.get("params") != params_fingerprint(args):
            sys.exit(f"{spath} was submitted with different params "
                     f"({state.get('params')}); use --force to resubmit")
        if state["n_items"] != len(items):
            sys.exit(f"{spath} covers {state['n_items']} prompts, this run has "
                     f"{len(items)}; use --force to resubmit")
        print(f"  [{model}] resuming batch {state['batch_id']}", flush=True)
        return state
    cids = [f"p{i:05d}" for i in range(len(items))]
    batch_id, file_id = batch_submit(client, model, items, cids, args)
    state = {"provider": args.provider, "model": model,
             "set": os.path.abspath(args.set), "batch_id": batch_id,
             "input_file_id": file_id, "n_items": len(items),
             "params": params_fingerprint(args),
             "custom_id_map": {c: it["id"] for c, it in zip(cids, items)},
             "submitted_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    save_state(spath, state)
    print(f"  [{model}] submitted batch {batch_id} ({len(items)} prompts)", flush=True)
    return state


def batch_collect(model, items, state, fetched, raw_path, args):
    """Turn batch results into the same preds/metas/raw log the sync path writes."""
    parse = parse_answer_reasoning if any(
        model.startswith(p) for p in REASONING_PREFIXES) else parse_answer
    by_id = {it["id"]: it for it in items}
    preds, metas = {}, []
    with open(raw_path, "w") as raw_f:
        for cid, tid in state["custom_id_map"].items():
            text, meta, err = fetched.get(cid, (None, None, "missing from batch results"))
            if err is not None:
                text, meta = f"<error: {err}>", _empty_meta("error", [err])
            else:
                meta = dict(meta, errors=[])
            # batch has no meaningful per-call wall clock and retries the
            # provider handles internally
            meta.update({"latency_s": None, "attempts": None,
                         "batch_id": state["batch_id"]})
            rec = record_for(by_id[tid], text, meta, parse)
            raw_f.write(json.dumps(rec) + "\n")
            preds[tid] = rec["prediction"]
            metas.append(meta)
    return preds, metas


# ------------------------------------------------------------- scoring/IO

def summarize(model, metas, wall_s, args, extra=None):
    def total(k):
        return sum(m.get(k) or 0 for m in metas)

    n = len(metas)
    lat = sorted(m["latency_s"] for m in metas if m.get("latency_s") is not None)
    truncated = {"length", "max_tokens"}  # OpenAI / Anthropic spellings
    stats = {
        "model": model,
        "provider": args.provider,
        "mode": "batch" if args.batch else "sync",
        "n_calls": n,
        "wall_s": round(wall_s, 1),
        "prompt_tokens": total("prompt_tokens"),
        "completion_tokens": total("completion_tokens"),
        "reasoning_tokens": total("reasoning_tokens"),  # OpenAI only; 0 on Anthropic
        "cached_prompt_tokens": total("cached_prompt_tokens"),
        "cache_write_tokens": total("cache_write_tokens"),
        "n_reasoning_traces": sum(1 for m in metas if m.get("reasoning_text")),
        "latency_s": {
            "mean": round(sum(lat) / len(lat), 2),
            "median": lat[len(lat) // 2],
            "p90": lat[int(0.9 * (len(lat) - 1))],
            "max": lat[-1],
        } if lat else None,   # null in batch mode: no per-call wall clock
        "n_errors": sum(1 for m in metas if m["finish_reason"] == "error"),
        "n_refusals": sum(1 for m in metas if m["finish_reason"] == "refusal"),
        "n_retried": sum(1 for m in metas if (m.get("attempts") or 1) > 1),
        "n_truncated": sum(1 for m in metas if m["finish_reason"] in truncated),
        "n_unparsed": None,  # filled by caller
    }
    stats.update(extra or {})
    return stats


def score_by_difficulty(preds, items):
    """JOINT accuracy per difficulty level (program solved iff all specified
    readings correct)."""
    gold = {it["id"]: {"gold": it["gold"], "cond": it["cond"],
                       "divergence_bin": it["divergence_bin"], "rec_id": it["rec_id"]}
            for it in items}
    overall = evaluate(preds, gold)
    # per-difficulty joint
    diff_of = {it["rec_id"]: (it.get("axis", "?"), it.get("difficulty", "?"))
               for it in items}
    by_prog = defaultdict(dict)
    for it in items:
        if it["cond"] in ("closed_world", "cred", "skept", "wfs") and it["gold"] is not None:
            n = normalize(preds.get(it["id"]))
            by_prog[it["rec_id"]][it["cond"]] = (n == str(it["gold"]).upper())
    per_diff = defaultdict(lambda: [0, 0])
    SPEC = ["closed_world", "cred", "skept", "wfs"]
    for rid, d in by_prog.items():
        solved = all(c in d and d[c] for c in SPEC)
        per_diff[diff_of[rid]][1] += 1
        per_diff[diff_of[rid]][0] += solved
    return overall, per_diff


def finish_model(model, preds, metas, wall, items, args, logdir, raw_path, extra=None):
    """Write submission + stats and print the summary. Shared by both modes."""
    sub_path = os.path.join(args.outdir, safe_name(model) + ".jsonl")
    with open(sub_path, "w") as f:
        for tid, p in preds.items():
            f.write(json.dumps({"id": tid, "prediction": p}) + "\n")

    stats = summarize(model, metas, wall, args, extra)
    stats["n_unparsed"] = sum(1 for p in preds.values() if p is None)
    stats["set"] = os.path.abspath(args.set)
    stats["submission"] = os.path.abspath(sub_path)
    stats["raw_log"] = os.path.abspath(raw_path)

    if args.score and all("gold" in it for it in items):
        overall, per_diff = score_by_difficulty(preds, items)
        stats["joint_accuracy"] = overall["joint_accuracy"]
        stats["per_prompt_accuracy"] = overall["per_prompt_accuracy"]
        stats["by_difficulty"] = {f"{a}/{d}": {"joint": nj, "n": nt}
                                  for (a, d), (nj, nt) in sorted(per_diff.items())}
        print(f"  JOINT={overall['joint_accuracy']}%  "
              f"per-prompt={overall['per_prompt_accuracy']}%")
        print("  JOINT by difficulty:")
        for (axis, d), (nj, nt) in sorted(per_diff.items()):
            pct = round(100 * nj / nt) if nt else 0
            print(f"    {axis:8} {str(d):12} {nj:>2}/{nt:<2} = {pct}%")

    with open(os.path.join(logdir, safe_name(model) + ".stats.json"), "w") as f:
        json.dump(stats, f, indent=1)

    reason = (f"{stats['reasoning_tokens']} reasoning tok" if stats["reasoning_tokens"]
              else f"{stats['n_reasoning_traces']} reasoning traces")
    print(f"  tokens: {stats['prompt_tokens']} in / {stats['completion_tokens']} out"
          f"  ({reason})")
    if stats["latency_s"]:
        print(f"  wall {stats['wall_s']}s, latency median {stats['latency_s']['median']}s"
              f" / p90 {stats['latency_s']['p90']}s")
    else:
        print(f"  wall {stats['wall_s']}s (batch turnaround; no per-call latency)")
    print(f"  errors={stats['n_errors']} refusals={stats['n_refusals']} "
          f"retried={stats['n_retried']} truncated={stats['n_truncated']} "
          f"unparsed={stats['n_unparsed']}")
    print(f"  raw log: {raw_path}")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, help="JSONL with id, prompt (and gold for --score)")
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--provider", choices=["openai", "anthropic", "ollama"], default="openai")
    ap.add_argument("--outdir", default=os.path.join(HERE, "submissions"))
    ap.add_argument("--logdir", default=None, help="default <outdir>/logs")
    ap.add_argument("--workers", type=int, default=4, help="sync mode only")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--limit", type=int, default=None, help="only the first N prompts (pilot runs)")
    ap.add_argument("--resume", action="store_true",
                    help="sync mode: skip ids already in the raw log and append to it")
    ap.add_argument("--retries", type=int, default=3, help="sync mode only")
    ap.add_argument("--max-completion-tokens", type=int, default=16384,
                    help="reasoning models and all Anthropic models: thinking + answer")
    ap.add_argument("--max-tokens", type=int, default=2048,
                    help="non-reasoning OpenAI-compatible models")
    ap.add_argument("--temperature", type=float, default=0,
                    help="openai/ollama sampling temperature (default 0 = greedy)")
    ap.add_argument("--top-p", type=float, default=None,
                    help="openai/ollama top_p (unset = provider default)")
    ap.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"], default=None,
                    help="anthropic: output_config.effort (unset = model default, high)")
    ap.add_argument("--no-thinking", action="store_true",
                    help="anthropic: disable thinking (rejected above --effort high on opus-5)")
    ap.add_argument("--thinking-budget", type=int, default=8192,
                    help="anthropic pre-4.6 models only (haiku-4-5, sonnet-4-5, opus-4-5)")
    ap.add_argument("--progress-every", type=int, default=50)
    # batch mode
    ap.add_argument("--batch", action="store_true",
                    help="submit via the provider's Batch API (50%% price, 24h window)")
    ap.add_argument("--submit-only", action="store_true",
                    help="batch: submit and exit; rerun the same command to collect")
    ap.add_argument("--force", action="store_true",
                    help="batch: resubmit even if a batch state file exists")
    ap.add_argument("--poll-interval", type=int, default=60, help="batch: seconds between polls")
    args = ap.parse_args()

    # fail fast rather than burning a full run of 400s: disabled thinking is
    # only accepted at effort high or below
    if args.no_thinking and args.effort in ("xhigh", "max"):
        sys.exit(f"--no-thinking is rejected at --effort {args.effort}; use high or lower")
    if args.batch and args.provider == "ollama":
        sys.exit("--batch needs a provider with a Batch API (openai or anthropic)")
    if args.batch and args.resume:
        sys.exit("--resume is sync-mode only; batch resumes from its own state file")

    items = [json.loads(l) for l in open(args.set) if l.strip()]
    if args.limit:
        items = items[:args.limit]
    os.makedirs(args.outdir, exist_ok=True)
    logdir = args.logdir or os.path.join(args.outdir, "logs")
    os.makedirs(logdir, exist_ok=True)

    if args.batch:
        return run_batch(items, logdir, args)

    for model in args.models:
        raw_path = os.path.join(logdir, safe_name(model) + ".raw.jsonl")
        done_preds, done_metas, todo = {}, [], items
        if args.resume and os.path.exists(raw_path):
            for line in open(raw_path):
                if not line.strip():
                    continue
                rec = json.loads(line)
                done_preds[rec["id"]] = rec["prediction"]
                done_metas.append(rec)
            todo = [it for it in items if it["id"] not in done_preds]
            print(f"=== {model}: resuming, {len(done_preds)} logged, {len(todo)} to go ===",
                  flush=True)
        else:
            print(f"=== {args.provider}:{model} ({len(items)} prompts) ===", flush=True)

        preds, metas, wall = ({}, [], 0.0)
        if todo:
            preds, metas, wall = run_sync(model, todo, raw_path, args)
        finish_model(model, {**done_preds, **preds}, done_metas + metas, wall,
                     items, args, logdir, raw_path)


def run_batch(items, logdir, args):
    client = make_client(args)
    pending = {}
    for model in args.models:
        print(f"=== {args.provider}:{model} ({len(items)} prompts, batch) ===", flush=True)
        pending[model] = batch_submit_or_resume(client, model, items, args, logdir)

    if args.submit_only:
        print("submitted; rerun the same command without --submit-only to collect",
              flush=True)
        return

    failed = []
    while pending:
        for model, state in list(pending.items()):
            batch, status, counts = batch_check(client, state["batch_id"], args.provider)
            print(f"  [{model}] {status} ({counts})", flush=True)
            if status == "failed":  # OpenAI hard failure: no output file
                print(f"  [{model}] batch failed: {getattr(batch, 'errors', None)}; "
                      f"state kept at {batch_state_path(logdir, model)}", flush=True)
                failed.append(model)
                del pending[model]
                continue
            if status not in OPENAI_TERMINAL:
                continue
            # completed / expired / cancelled -> collect whatever exists
            raw_path = os.path.join(logdir, safe_name(model) + ".raw.jsonl")
            fetched = batch_fetch(client, batch, args.provider)
            preds, metas = batch_collect(model, items, state, fetched, raw_path, args)
            submitted = datetime.datetime.fromisoformat(state["submitted_at"])
            wall = (datetime.datetime.now(datetime.timezone.utc) - submitted).total_seconds()
            finish_model(model, preds, metas, wall, items, args, logdir, raw_path,
                         extra={"batch_id": state["batch_id"],
                                "batch_status": status,
                                "submitted_at": state["submitted_at"]})
            os.remove(batch_state_path(logdir, model))
            del pending[model]
        if pending:
            time.sleep(args.poll_interval)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
