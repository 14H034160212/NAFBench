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
from evaluate import evaluate, load_submission  # noqa: E402
from score_submission import load_gold, SUBTASKS  # noqa: E402


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
        m = evaluate(load_submission(path), gold_cache[subtask])
        key = (team, subtask)
        if key not in best or m["joint_accuracy"] > best[key]["joint_accuracy"]:
            best[key] = m

    lines = ["# NAF-Bench Leaderboard", "",
             "Primary metric: **JOINT accuracy** (a program counts only if all four",
             "specified readings are correct). Scored server-side against a hidden test",
             "set. Three subtasks by context budget: `8k-lite` ⊂ `16k` ⊂ `full`.", ""]
    for subtask in SUBTASKS:
        rows = sorted(((t, m) for (t, s), m in best.items() if s == subtask),
                      key=lambda x: -x[1]["joint_accuracy"])
        lines += [f"## Subtask: `{subtask}`", "",
                  "| # | team | JOINT % | per-prompt % | sldnf | cred | skept | wfs |",
                  "|---|---|---|---|---|---|---|---|"]
        if not rows:
            lines.append("| — | _(no submissions yet)_ | | | | | | |")
        for i, (team, m) in enumerate(rows, 1):
            lines.append(f"| {i} | {team} | **{m['joint_accuracy']}** | "
                         f"{m['per_prompt_accuracy']} | {m['sldnf_accuracy']} | "
                         f"{m['cred_accuracy']} | {m['skept_accuracy']} | {m['wfs_accuracy']} |")
        lines.append("")

    out = os.path.join(HERE, "LEADERBOARD.md")
    open(out, "w").write("\n".join(lines) + "\n")
    print(f"wrote {out} ({len(best)} entries over {len(subs)} submissions)")


if __name__ == "__main__":
    main()
