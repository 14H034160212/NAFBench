"""Seed the diagnostic leaderboard from the models already evaluated in the paper.

Scores each model's stored answers with the leaderboard evaluator (primary =
JOINT accuracy) and writes a ranked table to RESULTS.md. This is the v1
"diagnostic" board: the frontier is jointly saturated (that is the finding), and
the ranking is meaningful across the rest of the field.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from evaluate import evaluate  # noqa

ANS_DIR = os.path.join(ROOT, "data/production_answers/run1")
MODELS = [  # display name, answer file, metadata
    ("Claude Sonnet 5", "claude-sonnet-5", dict(track="standard", open=False)),
    ("GPT-5.6 Sol", "gpt-5.6-sol", dict(track="standard", open=False)),
    ("o4-mini", "o4-mini", dict(track="standard", open=False)),
    ("Qwen2.5-Coder 32B", "qwen2.5-coder_32b", dict(track="standard", open=True)),
    ("DeepSeek-R1 32B", "deepseek-r1_32b", dict(track="standard", open=True)),
    ("Llama3 8B", "llama3_8b", dict(track="standard", open=True)),
]


def main():
    gold = {it["task_id"]: {"gold": it["gold"], "cond": it["cond"],
                            "divergence_bin": it["divergence_bin"],
                            "rec_id": it["rec_id"]}
            for it in json.load(open(os.path.join(ROOT, "data/production_set.json")))}

    rows = []
    for disp, fn, meta in MODELS:
        path = os.path.join(ANS_DIR, fn + ".json")
        if not os.path.exists(path):
            continue
        answers = json.load(open(path)).get("answers", {})
        m = evaluate(answers, gold)
        rows.append((disp, meta, m))
    rows.sort(key=lambda r: r[2]["joint_accuracy"], reverse=True)

    lines = [
        "# NAF-Bench Leaderboard — diagnostic board (v1)",
        "",
        "Primary metric: **JOINT accuracy** — a program counts only if the model",
        "answers all four readings (SLDNF / WFS / credulous / skeptical) correctly.",
        "Scored on the paper's evaluation set (120 programs). The frontier is jointly",
        "saturated by design; a harder hidden tier is in preparation.",
        "",
        "| # | Model | Open | JOINT % | per-prompt % | cred | skept | WFS | SLDNF | fmt-valid |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, (disp, meta, m) in enumerate(rows, 1):
        lines.append(
            f"| {i} | {disp} | {'✓' if meta['open'] else '—'} | "
            f"**{m['joint_accuracy']}** | {m['per_prompt_accuracy']} | "
            f"{m['cred_accuracy']} | {m['skept_accuracy']} | {m['wfs_accuracy']} | "
            f"{m['sldnf_accuracy']} | {m['format_valid_rate']} |")
    lines += ["",
              "JOINT by divergence bin (control / even-1 / odd / even-2):", ""]
    lines.append("| Model | control | even-1 | odd | even-2 |")
    lines.append("|---|---|---|---|---|")
    for disp, meta, m in rows:
        lines.append(f"| {disp} | {m['joint_control']} | {m['joint_even_one_sided']} "
                     f"| {m['joint_odd']} | {m['joint_even_both_sided']} |")
    out = os.path.join(HERE, "RESULTS.md")
    open(out, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
