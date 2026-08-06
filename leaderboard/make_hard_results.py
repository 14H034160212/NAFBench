"""Build the open-model hard-set results table (RESULTS_hard.md).

Reads a hard sample (with gold) and the per-model submissions in submissions/,
and tabulates per-difficulty-level accuracy for the open models. On the hard set
JOINT is ~0 for open models (uninformative), so the informative view is
per-prompt and per-reading (cred / skept / wfs) accuracy by level, which shows
where each model breaks (typically skeptical, as the number of cycles grows).

    python make_hard_results.py --sample /tmp/hv2_sample.jsonl
"""
import argparse
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from evaluate import normalize  # noqa

MODELS = [("Qwen2.5-Coder 32B", "qwen2.5-coder_32b"),
          ("Llama3 8B", "llama3_8b"),
          ("DeepSeek-R1 32B", "deepseek-r1_32b")]
LEVELS = ["disj_n2", "disj_n3", "disj_n4", "disj_n5", "disj_n6",
          "conj_n2", "conj_n3", "conj_n4", "conj_n5", "conj_n6",
          "coupled_n2", "coupled_n3", "coupled_n4", "coupled_n5"]


def load_preds(tag):
    p = os.path.join(HERE, "submissions", tag + ".jsonl")
    if not os.path.exists(p):
        return None
    return {json.loads(l)["id"]: json.loads(l).get("prediction")
            for l in open(p) if l.strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", default="/tmp/hv2_sample.jsonl")
    args = ap.parse_args()
    gold = {json.loads(l)["id"]: json.loads(l)
            for l in open(args.sample) if l.strip()}

    lines = ["# Open-model results on the hard set (`hard_v2`, sampled)", "",
             "Per-prompt accuracy by difficulty level. JOINT is ~0 for open models",
             "here (they never get a whole program right), so this shows the",
             "per-reading detail: **skeptical (gold B)** is the discriminating reading;",
             "credulous (A) and WFS (C) are often reachable by defaulting.",
             f"Sample: {len(gold)} prompts (combo axis, cred/skept/wfs, 3 programs/level).", ""]

    for disp, tag in MODELS:
        preds = load_preds(tag)
        if preds is None:
            lines.append(f"## {disp}\n\n_(no submission found)_\n")
            continue
        lines += [f"## {disp}", "",
                  "| level | stable models | overall | cred (A) | skept (B) | WFS (C) |",
                  "|---|---|---|---|---|---|"]
        for lvl in LEVELS:
            acc = defaultdict(lambda: [0, 0])
            nmods = "?"
            for tid, it in gold.items():
                if it["difficulty"] != lvl or it["gold"] is None:
                    continue
                nmods = it.get("n_stable_models", "?")
                ok = normalize(preds.get(tid)) == str(it["gold"]).upper()
                acc[it["cond"]][0] += ok
                acc[it["cond"]][1] += 1
            tot = [sum(acc[c][0] for c in acc), sum(acc[c][1] for c in acc)]

            def pc(x):
                return f"{round(100*x[0]/x[1])}%" if x[1] else "-"
            lines.append(f"| {lvl} | {nmods} | {pc(tot)} | {pc(acc['cred'])} "
                         f"| {pc(acc['skept'])} | {pc(acc['wfs'])} |")
        lines.append("")

    out = os.path.join(HERE, "RESULTS_hard.md")
    open(out, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
