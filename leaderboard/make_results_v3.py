"""Build RESULTS_v3.md from the per-model stats.json logs on hard_v3.

Reads the logged stats (joint_accuracy + by_difficulty) written by
run_models_logged.py for each model and tabulates overall JOINT + per-family
JOINT. o4-mini comes from Agnieszka's frontier run (submissions_v3_full);
the open models from the local run (submissions_v3_open).
"""
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))

# display name, stats.json path, open?
SOURCES = [
    ("o4-mini", "submissions_v3_full/logs/o4-mini.stats.json", False),
    ("DeepSeek-V4-Flash", "submissions_v3_open/logs/deepseek-v4-flash.stats.json", True),
    ("Qwen2.5-Coder 32B", "submissions_v3_open/logs/qwen2.5-coder_32b.stats.json", True),
    ("DeepSeek-R1 32B", "submissions_v3_open/logs/deepseek-r1_32b.stats.json", True),
    ("Qwen3.6", "submissions_v3_open/logs/qwen3.6_latest.stats.json", True),
    ("Qwen3.5 35B", "submissions_v3_open/logs/qwen3.5_35b.stats.json", True),
    ("Gemma4 31B", "submissions_v3_open/logs/gemma4_31b.stats.json", True),
    ("Llama3 8B", "submissions_v3_open/logs/llama3_8b.stats.json", True),
]
FAMILIES = ["cnf", "parity", "coupled", "loopy", "decided", "easy_pad"]
# The prohibitively-large 3-SAT tiers were dropped from the hard set (see
# make_hard_v3.py): 2^14 / 2^22 search spaces that no model can do in context.
# Exclude them here too, and recompute overall JOINT from the kept tiers (the
# stored joint_accuracy is over the old full set).
EXCLUDE_TIERS = {"cnf_n14", "cnf_n22"}


def fam_of(key):
    return key.split("/")[0]


def tier_of(key):
    return key.split("/")[-1]


def main():
    rows = []
    for disp, path, is_open in SOURCES:
        p = os.path.join(HERE, path)
        if not os.path.exists(p):
            rows.append((disp, is_open, None, None, None))
            continue
        d = json.load(open(p))
        fam = defaultdict(lambda: [0, 0])
        j_sum = n_sum = 0
        for k, v in d.get("by_difficulty", {}).items():
            if tier_of(k) in EXCLUDE_TIERS:
                continue
            f = fam_of(k)
            fam[f][0] += v["joint"]
            fam[f][1] += v["n"]
            j_sum += v["joint"]
            n_sum += v["n"]
        joint = round(100.0 * j_sum / n_sum, 1) if n_sum else None
        rows.append((disp, is_open, joint,
                     d.get("per_prompt_accuracy"), fam))

    lines = [
        "# NAF-Bench Leaderboard — hard set (v3)",
        "",
        "Primary metric: **JOINT accuracy** on `hard_v3` (mixed certified signatures,",
        "so the answer key is not guessable from the condition; includes a bounded",
        "search family `cnf_n8` = 8-variable 3-SAT). The prohibitively-large 3-SAT",
        "tiers `cnf_n14`/`cnf_n22` (2^14/2^22 search spaces) are excluded as",
        "uninformative. o4-mini is Agnieszka's frontier run; the open models are local",
        "(ollama).",
        "",
        "Decoding: temperature 0 (greedy) for all models, with a token budget large",
        "enough for each model to conclude (verbose reasoning models get up to 16k).",
        "`Qwen3.6`* is the sole exception, run at its recommended temp 0.6 — see note.",
        "",
        "| Model | open | JOINT % |",
        "|---|---|---|",
    ]
    for disp, is_open, joint, pp, fam in sorted(
            rows, key=lambda r: (r[2] is None, -(r[2] or 0))):
        j = "—" if joint is None else f"**{joint}**"
        lines.append(f"| {disp} | {'✓' if is_open else '—'} | {j} |")
    lines += ["", "JOINT by family (solved / total):", "",
              "| Model | " + " | ".join(FAMILIES) + " |",
              "|---|" + "|".join(["---"] * len(FAMILIES)) + "|"]
    for disp, is_open, joint, pp, fam in rows:
        if fam is None:
            lines.append(f"| {disp} (pending) | " + " | ".join(["—"] * len(FAMILIES)) + " |")
            continue
        cells = []
        for f in FAMILIES:
            if fam[f][1]:
                cells.append(f"{fam[f][0]}/{fam[f][1]}")
            else:
                cells.append("—")
        lines.append(f"| {disp} | " + " | ".join(cells) + " |")
    lines += ["",
              "**Read of the board.** The hard set gives a genuine spread with a *tight",
              "frontier gap*: o4-mini leads (68.8) but three open models cluster right",
              "behind — DeepSeek-V4-Flash 62.3, Gemma4 58.4, Qwen3.5 54.5 — far closer",
              "than on easier sets.",
              "",
              "Per family: even the bounded `cnf_n8` (3-SAT search) defeats almost every",
              "open model (0/11; Qwen2.5-Coder scrapes 1/11), and o4-mini manages only",
              "1/11 — search stays the hardest family. The combinatorial families",
              "`parity`/`coupled` are almost exclusively o4-mini's (4/6, 4/4), with",
              "**Qwen3.5 the only open model to score there** (1/6, 2/4). On `loopy`,",
              "open models actually *win*: **V4-Flash (19/20) and Gemma4 (16/20) beat",
              "o4-mini's 11/20**. `decided` (stratified, answer varies by program) is",
              "where most models earn their score — reading the program pays off there.",
              "",
              "\\* **Qwen3.6 (1.0) is a non-termination result, not a reasoning score.**",
              "It is extraordinarily verbose: even at its recommended temp 0.6 with a",
              "16k-token budget, ~50% of readings never finish, so the all-four JOINT",
              "metric collapses (per-reading it concludes ~49%). Reported for",
              "completeness with this caveat rather than as a capability estimate."]

    out = os.path.join(HERE, "RESULTS_v3.md")
    open(out, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
