"""Depth x effective-width accuracy heatmap (per model), from the v3 grid.
Visual companion to Exp. 13/15: shows that accuracy is ~flat across depth/width
(the semantics bin, not size, drives difficulty)."""
import json, glob
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

ev = {e["task_id"]: e for e in json.load(open("data/v3_full.json"))}
models = {}
for f in glob.glob("data/v3_answers/*.json"):
    if f.endswith("raw.json"): continue
    d = json.load(open(f)); models[d["model"]] = d["answers"]

DEPTHS = sorted({e["depth"] for e in ev.values()})
WIDTHS = sorted({e["width"] for e in ev.values()})
scored = [e for e in ev.values() if e["cond"] != "none"]   # cred/skept/wfs/closed_world

def cell_acc(m, d, w):
    sub = [models[m].get(e["task_id"]) == e["gold"]
           for e in scored if e["depth"] == d and e["width"] == w
           and e["task_id"] in models[m]]
    return np.mean(sub) if sub else np.nan

order = sorted(models)
fig, axes = plt.subplots(1, len(order), figsize=(3.6 * len(order), 3.6))
if len(order) == 1: axes = [axes]
for ax, m in zip(axes, order):
    M = np.array([[cell_acc(m, d, w) for w in WIDTHS] for d in DEPTHS])
    im = ax.imshow(M, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(WIDTHS))); ax.set_xticklabels(WIDTHS)
    ax.set_yticks(range(len(DEPTHS))); ax.set_yticklabels(DEPTHS)
    ax.set_xlabel("effective width"); ax.set_ylabel("depth")
    ax.set_title(m, fontsize=10)
    for i in range(len(DEPTHS)):
        for j in range(len(WIDTHS)):
            ax.text(j, i, f"{M[i,j]:.0%}", ha="center", va="center", fontsize=9,
                    color="black")
fig.suptitle("Accuracy over depth x effective-width (avg over 4 bins x cred/skept/wfs/CWA x 2 themes)\n"
             "— nearly flat: size is not the difficulty lever", fontsize=11)
plt.tight_layout(rect=[0, 0, 1, 0.92])
plt.savefig("data/depthwidth_heatmap.png", dpi=130)
print("Saved -> data/depthwidth_heatmap.png")
for m in order:
    vals = [cell_acc(m, d, w) for d in DEPTHS for w in WIDTHS]
    print(f"  {m:20s} cell range {min(vals):.0%}..{max(vals):.0%}")
