"""Multi-cycle analysis: does accuracy fall as the number of cycles (and stable
models) grows, for independent vs interdependent structures?"""
import json, glob
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

ev = {e["task_id"]: e for e in json.load(open("data/multicycle.json"))}
models = {}
for f in glob.glob("data/mc_answers/*.json"):
    if f.endswith("raw.json"): continue
    d = json.load(open(f)); models[d["model"]] = d["answers"]
SUBS = ["independent", "interdependent"]
NC = sorted({e["n_cycles"] for e in ev.values()})

def acc(m, sub, n):  # over cred/skept/wfs (gold defined)
    sub_e = [e for e in ev.values() if e["subtype"] == sub and e["n_cycles"] == n
             and e["gold"] is not None and e["task_id"] in models[m]]
    return np.mean([models[m][e["task_id"]] == e["gold"] for e in sub_e]) if sub_e else float("nan")

print("=== accuracy vs number of cycles (avg cred/skept/wfs) ===")
for sub in SUBS:
    nmods = {n: next(e["n_stable_models"] for e in ev.values()
                     if e["subtype"] == sub and e["n_cycles"] == n) for n in NC}
    print(f"\n  {sub} (n_cycles -> stable models: "
          + ", ".join(f"{n}:{nmods[n]}" for n in NC) + ")")
    for m in sorted(models):
        print(f"    {m:18s} " + "  ".join(f"n{n}:{acc(m,sub,n):.0%}" for n in NC))

fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
for ax, sub in zip(axes, SUBS):
    for m in sorted(models):
        ax.plot(NC, [acc(m, sub, n) for n in NC], marker="o", label=m)
    ax.set_title(f"{sub} multi-cycle"); ax.set_xlabel("number of cycles")
    ax.set_ylim(0, 1.05); ax.set_ylabel("accuracy"); ax.grid(alpha=.3)
axes[0].legend(fontsize=7)
plt.tight_layout(); plt.savefig("data/multicycle.png", dpi=130)
print("\nSaved -> data/multicycle.png")
