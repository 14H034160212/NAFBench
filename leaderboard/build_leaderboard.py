"""Score every submission under submissions/ and (re)write LEADERBOARD.md.

Run by the update-leaderboard GitHub Action on push to main. Pulls the private
gold from HF (HF_TOKEN secret), scores each submission, keeps the best JOINT per
(team, subtask), and renders a markdown leaderboard.

Submission files: submissions/<team>__<subtask>.jsonl  (subtask in 8k-lite/16k/full)
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from evaluate import evaluate  # noqa: E402
from score_submission import load_gold, SUBTASKS  # noqa: E402
from score_traces import trace_stats  # noqa: E402


def load_submission_objects(path):
    """id -> full record ({prediction, trace?}). Backward compatible: a line may be
    {id, prediction} (answer-only) or {id, prediction, trace}."""
    out = {}
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        rid = r.get("id")
        if rid is not None:
            out[rid] = r
    return out


def main():
    subs = sorted(glob.glob(os.path.join(ROOT, "submissions", "*__*.jsonl")))
    gold_cache = {}
    # best[(team, subtask)] = metrics
    best = {}
    for path in subs:
        base = os.path.basename(path)[:-6]  # strip .jsonl
        if "__" not in base:
            continue
        team, subtask = base.rsplit("__", 1)
        if subtask not in SUBTASKS:
            continue
        if subtask not in gold_cache:
            gold_cache[subtask] = load_gold(subtask)
        objs = load_submission_objects(path)
        preds = {rid: r.get("prediction") for rid, r in objs.items()}
        m = evaluate(preds, gold_cache[subtask])
        ts = trace_stats(objs, gold_cache[subtask])  # None if answer-only submission
        m["reasoned_soundly"] = ts["reasoned_soundly"] if ts else None
        m["trace_coverage"] = ts["trace_coverage"] if ts else 0
        key = (team, subtask)
        if key not in best or m["joint_accuracy"] > best[key]["joint_accuracy"]:
            best[key] = m

    lines = ["# NAF-Bench Leaderboard", "",
             "Primary metric: **JOINT accuracy** (a program counts only if all four",
             "specified readings are correct). Scored server-side against a hidden test",
             "set (`hard`: 385 prompts; the prohibitively-large 3-SAT instances",
             "`cnf_n14`/`cnf_n22` are excluded as uninformative).", ""]
    for subtask in SUBTASKS:
        rows = sorted(((t, m) for (t, s), m in best.items() if s == subtask),
                      key=lambda x: -x[1]["joint_accuracy"])
        lines += ["## Results", "",
                  "| # | team | JOINT % | trace-sound %ᵃᵘˣ | per-prompt % | sldnf | cred | skept | wfs |",
                  "|---|---|---|---|---|---|---|---|---|"]
        if not rows:
            lines.append("| — | _(no submissions yet)_ | | | | | | | |")
        for i, (team, m) in enumerate(rows, 1):
            rs = m.get("reasoned_soundly")
            rs_cell = "–" if rs is None else f"{rs}"
            lines.append(f"| {i} | {team} | **{m['joint_accuracy']}** | {rs_cell} | "
                         f"{m['per_prompt_accuracy']} | {m['sldnf_accuracy']} | "
                         f"{m['cred_accuracy']} | {m['skept_accuracy']} | {m['wfs_accuracy']} |")
        lines.append("")
    lines += ["> Ranking is by **JOINT %** only.", "",
              "> **trace-sound %ᵃᵘˣ** is *auxiliary information, not a ranking criterion.*"
              " Of the programs a model got right *and* submitted a reasoning `trace` for,"
              " the share whose trace commits to the certified query verdict (and, on odd"
              " cycles, registers that there is no stable model). The check is **regex-based"
              " and imperfect — a rough approximation of soundness**, not a verified proof"
              " audit. `–` = answer-only submission.", ""]

    out = os.path.join(HERE, "LEADERBOARD.md")
    open(out, "w").write("\n".join(lines) + "\n")

    # machine-readable feed for the static HF Space
    feed = [{"team": t, "subtask": s,
             "reasoned_soundly": m.get("reasoned_soundly"),
             "trace_coverage": m.get("trace_coverage", 0),
             **{k: m[k] for k in (
                 "joint_accuracy", "per_prompt_accuracy", "sldnf_accuracy",
                 "cred_accuracy", "skept_accuracy", "wfs_accuracy")}}
            for (t, s), m in best.items()]
    feed.sort(key=lambda r: (r["subtask"], -r["joint_accuracy"]))
    open(os.path.join(HERE, "leaderboard.json"), "w").write(json.dumps(feed, indent=1))
    print(f"wrote {out} ({len(best)} entries over {len(subs)} submissions)")


if __name__ == "__main__":
    main()
