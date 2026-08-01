"""Query models on a leaderboard prompt set and score them.

Usage (frontier, via OpenAI-compatible API):
    OPENAI_API_KEY=... python run_models.py \
        --set data/hard_ladder.jsonl --provider openai \
        --models o4-mini gpt-5.6-sol claude-sonnet-5 --score

Local open models via ollama:
    python run_models.py --set data/hard_ladder.jsonl --provider ollama \
        --models qwen2.5-coder:32b llama3:8b --score

Writes one submission per model (JSONL {id, prediction}) to --outdir. With
--score, also prints JOINT accuracy overall and BROKEN DOWN BY DIFFICULTY (the
accuracy-vs-difficulty curve that tells us whether/where the frontier drops
below 100%). Needs gold in the set (the hard_ladder has it); for a blind test
set omit --score and score server-side.
"""
import argparse
import json
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from nafbench.answer import parse_answer, parse_answer_reasoning  # noqa
from leaderboard.evaluate import evaluate, normalize  # noqa

REASONING_PREFIXES = ("gpt-5", "o1", "o3", "o4", "deepseek-r1", "claude-sonnet-5")


def ask(client, model, prompt):
    is_reasoning = any(model.startswith(p) for p in ("gpt-5", "o1", "o3", "o4"))
    for attempt in range(3):
        try:
            if is_reasoning:
                r = client.chat.completions.create(
                    model=model, messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=16384)
            else:
                r = client.chat.completions.create(
                    model=model, messages=[{"role": "user", "content": prompt}],
                    temperature=0, max_tokens=2048)
            return r.choices[0].message.content
        except Exception as e:  # noqa
            if attempt == 2:
                return f"<error: {e}>"
            time.sleep(2 * (attempt + 1))


def run_model(model, items, base_url, api_key, workers, reasoning):
    client = OpenAI(base_url=base_url, api_key=api_key)
    parse = parse_answer_reasoning if reasoning else parse_answer
    preds = {}

    def do(it):
        txt = ask(client, model, it["prompt"])
        return it["id"], parse(txt)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(do, it) for it in items]
        for i, f in enumerate(as_completed(futs), 1):
            tid, ans = f.result()
            preds[tid] = ans
            if i % 50 == 0:
                print(f"  [{model}] {i}/{len(items)}", flush=True)
    return preds


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, help="JSONL with id, prompt (and gold for --score)")
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--provider", choices=["openai", "ollama"], default="openai")
    ap.add_argument("--outdir", default=os.path.join(HERE, "submissions"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--score", action="store_true")
    args = ap.parse_args()

    if args.provider == "ollama":
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        api_key = "ollama"
    else:
        base_url = os.environ.get("OPENAI_BASE_URL")
        api_key = os.environ.get("OPENAI_API_KEY") or sys.exit("OPENAI_API_KEY not set")

    items = [json.loads(l) for l in open(args.set) if l.strip()]
    os.makedirs(args.outdir, exist_ok=True)

    for model in args.models:
        reasoning = any(model.startswith(p) for p in REASONING_PREFIXES)
        print(f"=== {model} ({len(items)} prompts) ===", flush=True)
        preds = run_model(model, items, base_url, api_key, args.workers, reasoning)
        safe = model.replace("/", "_").replace(":", "_")
        with open(os.path.join(args.outdir, safe + ".jsonl"), "w") as f:
            for tid, p in preds.items():
                f.write(json.dumps({"id": tid, "prediction": p}) + "\n")
        if args.score and all("gold" in it for it in items):
            overall, per_diff = score_by_difficulty(preds, items)
            print(f"  JOINT={overall['joint_accuracy']}%  per-prompt={overall['per_prompt_accuracy']}%")
            print("  JOINT by difficulty:")
            for (axis, d), (nj, nt) in sorted(per_diff.items()):
                pct = round(100 * nj / nt) if nt else 0
                print(f"    {axis:8} {str(d):12} {nj:>2}/{nt:<2} = {pct}%")
        print()


if __name__ == "__main__":
    main()
