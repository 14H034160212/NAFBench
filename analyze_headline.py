"""Headline metrics with 95% Wilson CIs over instance x theme x sampling-run."""
import json, glob, math, os
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

RUNS = [d for d in ["data/hl_run1", "data/hl_run2", "data/hl_run3"] if os.path.isdir(d)]
ev = {e["task_id"]: e for e in json.load(open("data/headline.json"))}
# models present in run1
models = sorted({os.path.basename(f)[:-5] for f in glob.glob(f"{RUNS[0]}/*.json")
                 if not f.endswith("raw.json")})

def ans(modelfile, run, tid):
    p = f"{run}/{modelfile}.json"
    if not os.path.exists(p): return None
    return json.load(open(p))["answers"].get(tid)

def wilson(k, n, z=1.96):
    if n == 0: return (float("nan"),) * 3
    p = k / n; d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return p, max(0, c-h), min(1, c+h)

CONDS = ["closed_world", "cred", "skept", "wfs"]
print(f"=== headline accuracy +/- 95% Wilson CI (n = 3 bins x 3 themes x {len(RUNS)} runs) ===")
acc_ci = {}
for m in models:
    print(f"\n  {m}")
    for c in CONDS:
        trials = [ (ans(m, r, t) == ev[t]["gold"])
                   for r in RUNS for t, e in ev.items() if e["cond"] == c ]
        trials = [x for x in trials]
        k, n = sum(trials), len(trials)
        p, lo, hi = wilson(k, n)
        acc_ci[(m, c)] = (p, lo, hi)
        print(f"    {c:13s} {p:.0%}  [{lo:.0%}, {hi:.0%}]   ({k}/{n})")

print("\n=== default-semantics reversion +/- 95% CI ===")
rev_ci = {}
for m in models:
    conf = rev = 0
    for r in RUNS:
        for rid in {e["rec_id"] for e in ev.values()}:
            d = ans(m, r, f"{rid}::none")
            if d is None: continue
            for c in CONDS:
                g = ev[f"{rid}::{c}"]["gold"]
                if g is not None and g != d:
                    conf += 1
                    if ans(m, r, f"{rid}::{c}") == d: rev += 1
    p, lo, hi = wilson(rev, conf)
    rev_ci[m] = (p, lo, hi)
    print(f"  {m:20s} {p:.0%}  [{lo:.0%}, {hi:.0%}]   ({rev}/{conf})")

# plot: per-condition accuracy with CI error bars
fig, ax = plt.subplots(figsize=(11, 5.5))
x = np.arange(len(models)); w = 0.2
for i, c in enumerate(CONDS):
    ys = [acc_ci[(m, c)][0] for m in models]
    lo = [acc_ci[(m, c)][0]-acc_ci[(m, c)][1] for m in models]
    hi = [acc_ci[(m, c)][2]-acc_ci[(m, c)][0] for m in models]
    ax.bar(x+(i-1.5)*w, ys, w, yerr=[lo, hi], capsize=3, label=c)
ax.set_xticks(x); ax.set_xticklabels(models, rotation=15, ha="right")
ax.set_ylim(0, 1.08); ax.set_ylabel("semantic-following accuracy")
ax.axhline(1/3, ls="--", color="gray", lw=1)
ax.set_title(f"Headline accuracy per condition, 95% Wilson CI "
             f"(3 bins x 3 themes x {len(RUNS)} runs @ T=0.7)")
ax.legend(fontsize=9)
plt.tight_layout(); plt.savefig("data/headline_ci.png", dpi=130)
print("\nSaved -> data/headline_ci.png")
