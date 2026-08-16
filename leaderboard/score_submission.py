"""Score one NAF-Bench submission against the PRIVATE hidden gold on HF.

Used by the GitHub Actions scoring workflow (free backend). The gold lives in a
private HF dataset and is pulled with the HF_TOKEN secret, so it is never public.

    HF_TOKEN=... python leaderboard/score_submission.py \
        --submission submissions/myteam__8k-lite.jsonl --subtask 8k-lite

Submission: JSONL, one line per prompt: {"id": ..., "prediction": "A|B|C"}.
Prints a human summary and, with --json, a metrics line for the workflow.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from evaluate import evaluate  # noqa: E402
from score_traces import trace_stats  # noqa: E402


def load_submission_objects(path):
    """id -> full record ({prediction, trace?}); backward compatible with answer-only."""
    out = {}
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if r.get("id") is not None:
            out[r["id"]] = r
    return out

GOLD_REPO = os.environ.get("GOLD_REPO", "qbao775/naf-bench-gold")
SUBTASKS = ["8k-lite", "16k", "full"]


def load_gold(subtask):
    from huggingface_hub import hf_hub_download
    token = os.environ.get("HF_TOKEN")
    path = hf_hub_download(GOLD_REPO, f"gold_{subtask}.json", repo_type="dataset",
                           token=token)
    return json.load(open(path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--submission", required=True)
    ap.add_argument("--subtask", required=True, choices=SUBTASKS)
    ap.add_argument("--team", default=None, help="team/model name for the row")
    ap.add_argument("--json", action="store_true", help="also print a METRICS_JSON line")
    args = ap.parse_args()

    gold = load_gold(args.subtask)
    objs = load_submission_objects(args.submission)
    preds = {rid: r.get("prediction") for rid, r in objs.items()}
    m = evaluate(preds, gold)
    ts = trace_stats(objs, gold)  # None for answer-only submissions

    print(f"Subtask: {args.subtask}")
    print(f"  JOINT accuracy : {m['joint_accuracy']}%   <-- primary")
    print(f"  per-prompt     : {m['per_prompt_accuracy']}%")
    print(f"  coverage       : {m['coverage']}%   format-valid: {m['format_valid_rate']}%")
    print(f"  by reading     : sldnf {m['sldnf_accuracy']} / cred {m['cred_accuracy']} "
          f"/ skept {m['skept_accuracy']} / wfs {m['wfs_accuracy']}")
    if ts:
        print(f"  trace-sound (aux): {ts['reasoned_soundly']}%   "
              f"(regex approx; traces on {ts['trace_coverage']} prompts)")
    else:
        print("  trace-sound (aux): – (answer-only submission; add a `trace` field for this auxiliary signal)")
    print(f"  programs       : {m['n_programs']}")

    if args.json:
        row = {"team": args.team or "unknown", "subtask": args.subtask,
               "joint_accuracy": m["joint_accuracy"],
               "per_prompt_accuracy": m["per_prompt_accuracy"],
               "coverage": m["coverage"],
               "reasoned_soundly": ts["reasoned_soundly"] if ts else None,
               "trace_coverage": ts["trace_coverage"] if ts else 0,
               "sldnf": m["sldnf_accuracy"], "cred": m["cred_accuracy"],
               "skept": m["skept_accuracy"], "wfs": m["wfs_accuracy"]}
        print("METRICS_JSON " + json.dumps(row))


if __name__ == "__main__":
    main()
