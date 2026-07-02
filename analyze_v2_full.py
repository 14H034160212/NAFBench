"""Full v2 grid analysis: regression of correctness on depth + width + bin,
balanced accuracy (gold is imbalanced), per-(bin,condition) following, and
theme-replicate error bars on the width/depth moderation curves.
"""
import json, glob
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

ev = {e["task_id"]: e for e in json.load(open("data/v2_full.json"))}
models = {}
for f in glob.glob("data/v2_full_answers/*.json"):
    if f.endswith("raw.json"): continue
    d = json.load(open(f)); models[d["model"]] = d["answers"]

BINS = ["control", "even_one_sided", "odd", "even_both_sided"]
CONDS = ["cred", "skept", "wfs"]
DEPTHS = sorted({e["depth"] for e in ev.values()})
WIDTHS = sorted({e["width"] for e in ev.values()})

def recs(model):
    a = models[model]
    return [(e["depth"], e["width"], e["divergence_bin"], e["cond"], e["theme"],
             1 if a.get(t) == e["gold"] else 0) for t, e in ev.items() if t in a]

def balanced_acc(model):
    """Mean over (bin,cond) groups of group accuracy — neutralizes gold imbalance."""
    a = models[model]; groups = {}
    for t, e in ev.items():
        if t not in a: continue
        groups.setdefault((e["divergence_bin"], e["cond"]), []).append(a[t] == e["gold"])
    return np.mean([np.mean(v) for v in groups.values()])

N_TOTAL = len(ev)
print(f"=== overall / balanced accuracy ({N_TOTAL} prompts; coverage n reported) ===")
for m in sorted(models):
    r = np.array([x[-1] for x in recs(m)], float)
    print(f"  {m:20s} raw {r.mean():.0%}   balanced {balanced_acc(m):.0%}   (n={len(r)}/{N_TOTAL})")

print("\n=== per (bin, condition) accuracy — does the model FOLLOW that semantics? ===")
hdr = "  ".join(f"{b[:5]}/{c[:2]}" for b in BINS for c in CONDS)
print(f"{'model':20s} " + hdr)
for m in sorted(models):
    a = models[m]; cells = []
    for b in BINS:
        for c in CONDS:
            ts = [t for t, e in ev.items() if e["divergence_bin"] == b and e["cond"] == c and t in a]
            acc = np.mean([a[t] == ev[t]["gold"] for t in ts]) if ts else float("nan")
            cells.append(f"{acc:4.0%}")
    print(f"{m:20s} " + "    ".join(cells))

# regression on non-saturated models: correct ~ z(depth)+z(width)+bin dummies
nonsat = [m for m in models if np.mean([x[-1] for x in recs(m)]) < 0.92]
print(f"\n=== pooled OLS on non-saturated models {nonsat} ===")
R = [x for m in nonsat for x in recs(m)]
dep = np.array([r[0] for r in R], float); wid = np.array([r[1] for r in R], float)
y = np.array([r[5] for r in R], float)
def z(x): return (x - x.mean()) / (x.std() + 1e-9)
binmat = np.array([[1.0 if r[2] == b else 0.0 for b in BINS[1:]] for r in R])  # control = ref
X = np.column_stack([np.ones(len(R)), z(dep), z(wid), binmat])
beta, *_ = np.linalg.lstsq(X, y, rcond=None)
names = ["intercept", "z(depth)", "z(width)"] + [f"bin={b}" for b in BINS[1:]]
for n, b in zip(names, beta):
    print(f"  {n:18s} {b:+.3f}")
print(f"  -> stronger structural moderator: "
      f"{'WIDTH' if abs(beta[2]) > abs(beta[1]) else 'DEPTH'} "
      f"(|b_width|={abs(beta[2]):.3f} vs |b_depth|={abs(beta[1]):.3f})")

# ---- moderation curves with theme-replicate error bars (non-saturated) ----
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
for m in nonsat:
    R = recs(m)
    def curve(idx):
        xs = DEPTHS if idx == 0 else WIDTHS
        means, errs = [], []
        for v in xs:
            per_theme = []
            for th in (0, 1, 2):
                vals = [r[5] for r in R if r[idx] == v and r[4] == th]
                if vals: per_theme.append(np.mean(vals))
            means.append(np.mean(per_theme)); errs.append(np.std(per_theme))
        return xs, means, errs
    xs, mu, er = curve(0); axes[0].errorbar(xs, mu, yerr=er, marker="o", capsize=3, label=m)
    xs, mu, er = curve(1); axes[1].errorbar(xs, mu, yerr=er, marker="s", capsize=3, label=m)
axes[0].set_title("Accuracy vs DEPTH (error bars = theme replicates)"); axes[0].set_xlabel("depth")
axes[1].set_title("Accuracy vs WIDTH (error bars = theme replicates)"); axes[1].set_xlabel("width")
for ax in axes:
    ax.set_ylim(0, 1.05); ax.set_ylabel("semantic-following accuracy"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
plt.tight_layout(); plt.savefig("data/v2_full_moderation.png", dpi=130)
print("\nSaved -> data/v2_full_moderation.png")
