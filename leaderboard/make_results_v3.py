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
    ("Qwen2.5-Coder 32B", "submissions_v3_open/logs/qwen2.5-coder_32b.stats.json", True),
    ("DeepSeek-R1 32B", "submissions_v3_open/logs/deepseek-r1_32b.stats.json", True),
    ("Llama3 8B", "submissions_v3_open/logs/llama3_8b.stats.json", True),
]
FAMILIES = ["cnf", "parity", "coupled", "loopy", "decided", "easy_pad"]


def fam_of(key):
    return key.split("/")[0]


def main():
    rows = []
    for disp, path, is_open in SOURCES:
        p = os.path.join(HERE, path)
        if not os.path.exists(p):
            rows.append((disp, is_open, None, None, None))
            continue
        d = json.load(open(p))
        fam = defaultdict(lambda: [0, 0])
        for k, v in d.get("by_difficulty", {}).items():
            f = fam_of(k)
            fam[f][0] += v["joint"]
            fam[f][1] += v["n"]
        rows.append((disp, is_open, d.get("joint_accuracy"),
                     d.get("per_prompt_accuracy"), fam))

    lines = [
        "# NAF-Bench Leaderboard — hard set (v3)",
        "",
        "Primary metric: **JOINT accuracy** on `hard_v3` (mixed certified signatures,",
        "so the answer key is not guessable from the condition; includes a real search",
        "family `cnf` = 3-SAT near the phase transition). o4-mini is Agnieszka's",
        "frontier run; the open models are local (ollama).",
        "",
        "| Model | open | JOINT % | per-prompt % |",
        "|---|---|---|---|",
    ]
    for disp, is_open, joint, pp, fam in sorted(
            rows, key=lambda r: (r[2] is None, -(r[2] or 0))):
        j = "—" if joint is None else f"**{joint}**"
        p = "—" if pp is None else f"{pp}"
        lines.append(f"| {disp} | {'✓' if is_open else '—'} | {j} | {p} |")
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
              "`cnf` (search) and `loopy` crush every model; `decided` (stratified,",
              "answer varies by program) is where reading the program actually pays off",
              "— note Qwen's JOINT is almost entirely `decided`. v3 gives a real spread",
              "(o4-mini > Qwen > Llama3), unlike v2 whose answer key was guessable."]

    out = os.path.join(HERE, "RESULTS_v3.md")
    open(out, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
