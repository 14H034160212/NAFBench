"""Accuracy vs cycle length, per bin and model (is a longer cycle harder?)."""
import json, glob
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

ev = {e["task_id"]: e for e in json.load(open("data/cyclesweep.json"))}
models = {}
for f in glob.glob("data/cyc_answers/*.json"):
    if f.endswith("raw.json"): continue
    d = json.load(open(f)); models[d["model"]] = d["answers"]
BINS = ["even_one_sided", "odd", "even_both_sided"]

def acc(m, b, k):
    sub = [models[m].get(e["task_id"]) == e["gold"]
           for e in ev.values() if e["divergence_bin"] == b and e["cycle_len"] == k
           and e["task_id"] in models[m]]
    return np.mean(sub) if sub else float("nan")

print("=== accuracy vs cycle length (avg over cred/skept/wfs) ===")
for b in BINS:
    ks = sorted({e["cycle_len"] for e in ev.values() if e["divergence_bin"] == b})
    print(f"\n  {b} (cycles {ks}):")
    for m in sorted(models):
        print(f"    {m:18s} " + "  ".join(f"k{k}:{acc(m,b,k):.0%}" for k in ks))

fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
for ax, b in zip(axes, BINS):
    ks = sorted({e["cycle_len"] for e in ev.values() if e["divergence_bin"] == b})
    for m in sorted(models):
        ax.plot(ks, [acc(m, b, k) for k in ks], marker="o", label=m)
    ax.set_title(b); ax.set_xlabel("cycle length"); ax.set_ylim(0, 1.05)
    ax.set_ylabel("accuracy"); ax.grid(alpha=.3)
axes[0].legend(fontsize=7)
plt.tight_layout(); plt.savefig("data/cyclesweep.png", dpi=130)
print("\nSaved -> data/cyclesweep.png")
