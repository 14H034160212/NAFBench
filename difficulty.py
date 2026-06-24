"""Difficulty-axis curves: accuracy vs negation depth and vs rule depth.

Reads data/ladder_answers/*.json (automated models) and the ladder gold, then
plots accuracy as a function of each controlled axis (averaged over themes).
"""
import json
import glob
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import defaultdict

ladder = json.load(open("data/ladder_set.json"))
by_task = {e["task_id"]: e for e in ladder}

models = {}
for f in glob.glob("data/ladder_answers/*.json"):
    if f.endswith(".raw.json"):
        continue
    d = json.load(open(f))
    models[d["model"]] = d["answers"]

AXES = ["negation_depth", "rule_depth"]


def curve(model_ans, axis):
    # accuracy at each axis value, averaged over themes
    hits = defaultdict(list)
    for e in ladder:
        if e["axis"] != axis:
            continue
        a = model_ans.get(e["task_id"])
        hits[e["axis_value"]].append(1 if a == e["gold"] else 0)
    xs = sorted(hits)
    ys = [sum(hits[x]) / len(hits[x]) for x in xs]
    return xs, ys


print("=== accuracy by depth (averaged over themes) ===")
for axis in AXES:
    print(f"\n-- {axis} --")
    for m, ans in sorted(models.items()):
        xs, ys = curve(ans, axis)
        print(f"  {m:22s} " + " ".join(f"{x}:{y:.0%}" for x, y in zip(xs, ys)))

fig, axes = plt.subplots(1, 2, figsize=(13, 5))
titles = {"negation_depth": "Nested-negation depth\n(alternating 'not' stack; gold alternates A/B)",
          "rule_depth": "Rule (chain) depth\n(default-with-exception under explicit CWA; gold=A)"}
markers = ["o", "s", "^", "D", "v", "P"]
for ax, axis in zip(axes, AXES):
    for i, (m, ans) in enumerate(sorted(models.items())):
        xs, ys = curve(ans, axis)
        ax.plot(xs, ys, marker=markers[i % len(markers)], label=m)
    ax.set_title(titles[axis])
    ax.set_xlabel(axis.replace("_", " "))
    ax.set_ylabel("accuracy vs certified gold")
    ax.set_ylim(0, 1.08)
    ax.axhline(0.5, ls="--", color="gray", lw=1)
    ax.grid(alpha=0.3)
axes[0].legend(fontsize=8, loc="lower left")
plt.tight_layout()
plt.savefig("data/difficulty_curves.png", dpi=130)
print("\nSaved -> data/difficulty_curves.png")
