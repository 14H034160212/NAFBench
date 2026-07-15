"""Batch-API NAF-Bench evaluation harness (50% price vs run_eval.py).

Submits one batch per model, polls until done, and writes the same two
output files as run_eval.py so every analyzer keeps working unchanged:
  <outdir>/<safe>.json      {"model", "provider", "answers", "completion_tokens"}
  <outdir>/<safe>.raw.json  {task_id: raw_text}

Providers:
  * openai     — OpenAI Batches API (JSONL upload -> poll -> download)
  * anthropic  — native Message Batches API (the OpenAI-compat layer has no batching)

Resumability: a state file <outdir>/<safe>.batch_state.json is written at
submission. Re-running the same command resumes polling the in-flight batch
instead of resubmitting; --force resubmits fresh. The state file is removed
only after both output files are written.

Usage:
  OPENAI_API_KEY=...    python run_eval_batch.py --provider openai --models gpt-4o-mini o4-mini
  ANTHROPIC_API_KEY=... python run_eval_batch.py --provider anthropic --models claude-opus-4-8 --max-tokens 16384
"""
import argparse
import datetime
import json
import os
import sys
import time

from run_eval import SYSTEM, _is_reasoning  # single source of truth for the prompt + model split
from nafbench.answer import parse_answer

OPENAI_TERMINAL = {"completed", "failed", "expired", "cancelled"}


def safe_name(model):
    return model.replace("/", "_").replace(":", "_")


def state_path(outdir, model):
    return os.path.join(outdir, f"{safe_name(model)}.batch_state.json")


def save_state(path, state):
    tmp = path + ".tmp"
    json.dump(state, open(tmp, "w"), indent=1)
    os.replace(tmp, path)


# ---------------------------------------------------------------- OpenAI

def build_body_openai(model, prompt, temperature, max_tokens):
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt}]
    if _is_reasoning(model):
        # reasoning models: no temperature; budget covers hidden reasoning too
        return {"model": model, "messages": msgs, "max_completion_tokens": 16384}
    return {"model": model, "messages": msgs,
            "temperature": temperature, "max_tokens": max_tokens}


def openai_submit(client, model, items, cid_map, temperature, max_tokens):
    lines = []
    for cid, item in zip(cid_map, items):
        lines.append(json.dumps({
            "custom_id": cid, "method": "POST", "url": "/v1/chat/completions",
            "body": build_body_openai(model, item["prompt"], temperature, max_tokens)}))
    f = client.files.create(
        file=(f"{safe_name(model)}.batch.jsonl", "\n".join(lines).encode()),
        purpose="batch")
    b = client.batches.create(input_file_id=f.id, endpoint="/v1/chat/completions",
                              completion_window="24h")
    return b.id, f.id


def openai_check(client, batch_id):
    b = client.batches.retrieve(batch_id)
    rc = b.request_counts
    counts = f"{rc.completed}/{rc.total} done, {rc.failed} failed" if rc else "?"
    return b, b.status, counts


def openai_fetch(client, batch):
    """Return {custom_id: (text, completion_tokens, error)}."""
    out = {}
    for file_id in (batch.output_file_id, batch.error_file_id):
        if not file_id:
            continue
        for line in client.files.content(file_id).text.splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            cid = obj["custom_id"]
            resp = obj.get("response")
            if obj.get("error"):
                out[cid] = (None, None, json.dumps(obj["error"]))
            elif resp and resp.get("status_code") == 200:
                body = resp["body"]
                text = body["choices"][0]["message"]["content"]
                ctoks = (body.get("usage") or {}).get("completion_tokens")
                out[cid] = (text, ctoks, None)
            else:
                out[cid] = (None, None, f"http {resp.get('status_code') if resp else '?'}")
    return out


# ------------------------------------------------------------- Anthropic

def anthropic_submit(client, model, items, cid_map, max_tokens):
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
    # No temperature (newest Claude models reject non-default sampling params)
    # and no thinking config (omitting it is correct on every current model).
    requests = [
        Request(custom_id=cid,
                params=MessageCreateParamsNonStreaming(
                    model=model, max_tokens=max_tokens, system=SYSTEM,
                    messages=[{"role": "user", "content": item["prompt"]}]))
        for cid, item in zip(cid_map, items)]
    b = client.messages.batches.create(requests=requests)
    return b.id


def anthropic_check(client, batch_id):
    b = client.messages.batches.retrieve(batch_id)
    rc = b.request_counts
    counts = f"{rc.succeeded} ok, {rc.errored} err, {rc.processing} processing"
    status = "completed" if b.processing_status == "ended" else b.processing_status
    return b, status, counts


def anthropic_fetch(client, batch):
    """Return {custom_id: (text, output_tokens, error)}."""
    out = {}
    for result in client.messages.batches.results(batch.id):
        cid = result.custom_id
        rtype = result.result.type
        if rtype == "succeeded":
            msg = result.result.message
            if msg.stop_reason == "refusal":
                out[cid] = (None, None, "refusal")
                continue
            text = "".join(b.text for b in msg.content if b.type == "text")
            # output_tokens includes thinking tokens on thinking-enabled models,
            # analogous to completion_tokens covering hidden reasoning on o-series
            out[cid] = (text, msg.usage.output_tokens, None)
        elif rtype == "errored":
            out[cid] = (None, None, str(result.result.error))
        else:  # canceled / expired
            out[cid] = (None, None, rtype)
    return out


# ------------------------------------------------------------------ I/O

def write_outputs(outdir, model, provider, cid_map, fetched):
    results, raw, ctokens = {}, {}, {}
    for cid, tid in cid_map.items():
        text, ctoks, err = fetched.get(cid, (None, None, "missing from batch results"))
        if err is not None:
            results[tid], raw[tid], ctokens[tid] = None, f"<error: {err}>", None
        else:
            results[tid], raw[tid], ctokens[tid] = parse_answer(text), text, ctoks
    safe = safe_name(model)
    out = {"model": model, "provider": provider, "answers": results,
           "completion_tokens": ctokens}
    json.dump(out, open(f"{outdir}/{safe}.json", "w"), indent=1)
    json.dump(raw, open(f"{outdir}/{safe}.raw.json", "w"), indent=1)
    print(f"  saved {outdir}/{safe}.json", flush=True)


# ----------------------------------------------------------------- main

def make_client(provider):
    if provider == "openai":
        from openai import OpenAI
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise SystemExit("OPENAI_API_KEY not set in environment")
        return OpenAI(base_url=os.environ.get("OPENAI_BASE_URL"), api_key=api_key)
    import anthropic
    return anthropic.Anthropic()  # resolves ANTHROPIC_API_KEY or an `ant auth login` profile


def submit_or_resume(client, args, model, eval_items):
    spath = state_path(args.outdir, model)
    if os.path.exists(spath) and not args.force:
        state = json.load(open(spath))
        if state["set"] != args.set:
            raise SystemExit(
                f"{spath} is for set {state['set']}, not {args.set}; "
                f"use --force to resubmit or point --outdir elsewhere")
        print(f"  [{model}] resuming batch {state['batch_id']}", flush=True)
        return state
    cids = [f"t{i:04d}" for i in range(len(eval_items))]
    if args.provider == "openai":
        batch_id, file_id = openai_submit(client, model, eval_items, cids,
                                          args.temperature, args.max_tokens)
    else:
        batch_id = anthropic_submit(client, model, eval_items, cids, args.max_tokens)
        file_id = None
    state = {"provider": args.provider, "model": model, "set": args.set,
             "batch_id": batch_id, "input_file_id": file_id,
             "custom_id_map": {c: it["task_id"] for c, it in zip(cids, eval_items)},
             "submitted_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    save_state(spath, state)
    print(f"  [{model}] submitted batch {batch_id} ({len(eval_items)} prompts)", flush=True)
    return state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--provider", choices=["openai", "anthropic"], required=True)
    ap.add_argument("--set", default="data/eval_set.json", help="eval set JSON")
    ap.add_argument("--outdir", default="data/auto_answers", help="output dir")
    ap.add_argument("--temperature", type=float, default=0.0,
                    help="OpenAI non-reasoning models only")
    ap.add_argument("--max-tokens", type=int, default=8192,
                    help="use >=16384 for thinking-heavy Anthropic models")
    ap.add_argument("--poll-interval", type=int, default=60)
    ap.add_argument("--submit-only", action="store_true",
                    help="submit and exit; rerun later to poll and fetch")
    ap.add_argument("--force", action="store_true",
                    help="resubmit even if a batch state file exists")
    args = ap.parse_args()

    client = make_client(args.provider)
    check = openai_check if args.provider == "openai" else anthropic_check
    fetch = openai_fetch if args.provider == "openai" else anthropic_fetch

    eval_items = json.load(open(args.set))
    os.makedirs(args.outdir, exist_ok=True)

    pending = {}
    for model in args.models:
        print(f"=== {args.provider}:{model} ({len(eval_items)} prompts) ===", flush=True)
        pending[model] = submit_or_resume(client, args, model, eval_items)

    if args.submit_only:
        print("submitted; rerun the same command (without --submit-only) to collect", flush=True)
        return

    failed = []
    while pending:
        for model, state in list(pending.items()):
            batch, status, counts = check(client, state["batch_id"])
            print(f"  [{model}] {status} ({counts})", flush=True)
            if status == "failed":  # OpenAI hard failure: no output file
                print(f"  [{model}] batch failed: {getattr(batch, 'errors', None)}; "
                      f"state kept at {state_path(args.outdir, model)}", flush=True)
                failed.append(model)
                del pending[model]
            elif status in OPENAI_TERMINAL:  # completed / expired / cancelled -> fetch what exists
                write_outputs(args.outdir, model, args.provider,
                              state["custom_id_map"], fetch(client, batch))
                os.remove(state_path(args.outdir, model))
                del pending[model]
        if pending:
            time.sleep(args.poll_interval)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
