"""Headline metrics with 95% CIs CLUSTERED BY PROGRAM.

Audit finding #3: themes x sampling-runs are replicates of one program per bin,
so prompt-level Wilson intervals pseudoreplicate. We instead bootstrap over
programs (nafbench.clusterstats) -- honestly wide with a handful of programs.
"""
import json, glob, os
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from nafbench.clusterstats import cluster_bootstrap_ci

RUNS = [d for d in ["data/hl_run1", "data/hl_run2", "data/hl_run3"] if os.path.isdir(d)]
ev = {e["task_id"]: e for e in json.load(open("data/headline.json"))}
# models present in run1
models = sorted({os.path.basename(f)[:-5] for f in glob.glob(f"{RUNS[0]}/*.json")
                 if not f.endswith("raw.json")})

def ans(modelfile, run, tid):
    p = f"{run}/{modelfile}.json"
    if not os.path.exists(p): return None
    return json.load(open(p))["answers"].get(tid)

CONDS = ["closed_world", "cred", "skept", "wfs"]
n_prog = len({e["rec_id"] for e in ev.values()})
print(f"=== headline accuracy +/- 95% CI, CLUSTERED BY PROGRAM "
      f"(n = {n_prog} programs; themes x {len(RUNS)} runs are replicates) ===")
acc_ci = {}
for m in models:
    print(f"\n  {m}")
    for c in CONDS:
        # program -> list of 0/1 outcomes across its themes and runs
        by_prog = {}
        for t, e in ev.items():
            if e["cond"] != c:
                continue
            for r in RUNS:
                a = ans(m, r, t)
                by_prog.setdefault(e["rec_id"], []).append(int(a == e["gold"]))
        p, lo, hi, k, n, npr = cluster_bootstrap_ci(by_prog)
        acc_ci[(m, c)] = (p, lo, hi)
        print(f"    {c:13s} {p:.0%}  [{lo:.0%}, {hi:.0%}]   ({k}/{n} over {npr} progs)")

print("\n=== default-semantics reversion +/- 95% CI (clustered by program) ===")
rev_ci = {}
for m in models:
    by_prog = {}
    for rid in {e["rec_id"] for e in ev.values()}:
        outcomes = []
        for r in RUNS:
            d = ans(m, r, f"{rid}::none")
            if d is None: continue
            for c in CONDS:
                g = ev[f"{rid}::{c}"]["gold"]
                if g is not None and g != d:
                    outcomes.append(int(ans(m, r, f"{rid}::{c}") == d))
        if outcomes:
            by_prog[rid] = outcomes
    p, lo, hi, rev, conf, npr = cluster_bootstrap_ci(by_prog)
    rev_ci[m] = (p, lo, hi)
    print(f"  {m:20s} {p:.0%}  [{lo:.0%}, {hi:.0%}]   ({rev}/{conf} over {npr} progs)")

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
ax.set_title(f"Headline accuracy per condition, 95% CI clustered by program "
             f"(n = {n_prog} programs; themes x {len(RUNS)} runs @ T=0.7)")
ax.legend(fontsize=9)
plt.tight_layout(); plt.savefig("data/headline_ci.png", dpi=130)
print("\nSaved -> data/headline_ci.png")
