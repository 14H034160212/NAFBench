"""Decompose LENGTH vs STRUCTURE using the length-matched padding triples:
   length effect    = acc(low_pad) - acc(low_nat)   (same structure, +length)
   structure effect = acc(high_nat) - acc(low_pad)   (same length, +structure)
"""
import json, glob
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

ev = {e["task_id"]: e for e in json.load(open("data/padtest.json"))}
models = {}
for f in glob.glob("data/pad_answers/*.json"):
    if f.endswith("raw.json"): continue
    d = json.load(open(f)); models[d["model"]] = d["answers"]
MM = sorted(models)

def acc(m, variant):
    sub = [models[m].get(e["task_id"]) == e["gold"]
           for e in ev.values() if e["variant"] == variant and e["task_id"] in models[m]]
    return np.mean(sub) if sub else float("nan")

print(f"{'model':20s} low_nat  low_pad  high_nat | length_eff  structure_eff")
rows = []
for m in MM:
    a0, a1, a2 = acc(m, "low_nat"), acc(m, "low_pad"), acc(m, "high_nat")
    le, se = a1 - a0, a2 - a1
    rows.append((m, a0, a1, a2, le, se))
    print(f"{m:20s} {a0:5.0%}    {a1:5.0%}    {a2:5.0%}   | {le:+5.0%}      {se:+5.0%}")

les = np.mean([r[4] for r in rows]); ses = np.mean([r[5] for r in rows])
print(f"\nmean length effect    (low_pad - low_nat)  = {les:+.0%}")
print(f"mean structure effect (high_nat - low_pad) = {ses:+.0%}")
print("=> " + ("STRUCTURE dominates length" if abs(ses) > abs(les) else "LENGTH dominates"))

# plot
fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(MM)); w = 0.25
for i, (v, lbl, col) in enumerate([("low_nat", "low structure, short", "#55a868"),
                                   ("low_pad", "low structure, padded to long", "#dd8452"),
                                   ("high_nat", "high structure, long", "#c44e52")]):
    ax.bar(x + (i - 1) * w, [acc(m, v) for m in MM], w, label=lbl, color=col)
ax.set_xticks(x); ax.set_xticklabels(MM, rotation=15, ha="right"); ax.set_ylim(0, 1.05)
ax.set_ylabel("semantic-following accuracy")
ax.set_title("Length vs structure (length-matched padding)\n"
             "low_pad ≈ high_nat in tokens; gap low_pad→high_nat is pure structure")
ax.legend(fontsize=9); ax.grid(alpha=.3)
plt.tight_layout(); plt.savefig("data/padtest.png", dpi=130)
print("\nSaved -> data/padtest.png")
