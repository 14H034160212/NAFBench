"""Analyze the v2 grid: semantic-following accuracy vs depth and width.

Tests Agnieszka's hypothesis that WIDTH (simultaneous tracking) is a stronger
moderator of model failure than DEPTH (linear chaining), via:
  - marginal accuracy curves vs depth and vs width (per model),
  - a standardized OLS of per-item correctness ~ depth + width (pooled), so the
    larger |coefficient| identifies the stronger moderator,
  - correlation of correctness with solver hardness (Prolog inferences).
"""
import json, glob
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

ev = {e["task_id"]: e for e in json.load(open("data/v2_eval.json"))}
models = {}
for f in glob.glob("data/v2_answers/*.json"):
    if f.endswith("raw.json"): continue
    d = json.load(open(f)); models[d["model"]] = d["answers"]

DEPTHS = sorted({e["depth"] for e in ev.values()})
WIDTHS = sorted({e["width"] for e in ev.values()})

def rows(model):
    a = models[model]
    out = []
    for t, e in ev.items():
        if t not in a: continue
        out.append((e["depth"], e["width"], e["metrics"]["prolog_inferences"] or 0,
                    1 if a[t] == e["gold"] else 0))
    return np.array(out, float)

print("=== semantic-following accuracy (75 prompts: 25 cred/A, 25 skept/B, 25 wfs/C) ===")
for m in sorted(models):
    r = rows(m)
    print(f"  {m:20s} overall {r[:,3].mean():.0%}  (n={len(r)})")

print("\n=== marginal accuracy vs DEPTH (avg over width) ===")
for m in sorted(models):
    r = rows(m)
    line = "  ".join(f"d{int(d)}:{r[r[:,0]==d,3].mean():.0%}" for d in DEPTHS)
    print(f"  {m:20s} {line}")
print("\n=== marginal accuracy vs WIDTH (avg over depth) ===")
for m in sorted(models):
    r = rows(m)
    line = "  ".join(f"w{int(w)}:{r[r[:,1]==w,3].mean():.0%}" for w in WIDTHS)
    print(f"  {m:20s} {line}")

# pooled standardized OLS: correct ~ z(depth) + z(width)
allr = np.vstack([rows(m) for m in models])
def z(x): return (x - x.mean()) / (x.std() + 1e-9)
X = np.column_stack([np.ones(len(allr)), z(allr[:,0]), z(allr[:,1])])
y = allr[:,3]
beta, *_ = np.linalg.lstsq(X, y, rcond=None)
print(f"\n=== pooled OLS  correct ~ b0 + b_depth*z(depth) + b_width*z(width) ===")
print(f"  b_depth = {beta[1]:+.3f}   b_width = {beta[2]:+.3f}   "
      f"(more negative = stronger degradation)")
print(f"  => stronger moderator: {'WIDTH' if abs(beta[2])>abs(beta[1]) else 'DEPTH'}")
# correlation with solver hardness
cc = np.corrcoef(allr[:,2], allr[:,3])[0,1]
print(f"  corr(correct, prolog_inferences) = {cc:+.3f}")

# ---- plots: marginal curves + per-model heatmaps ----
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
for m in sorted(models):
    r = rows(m)
    axes[0].plot(DEPTHS, [r[r[:,0]==d,3].mean() for d in DEPTHS], marker="o", label=m)
    axes[1].plot(WIDTHS, [r[r[:,1]==w,3].mean() for w in WIDTHS], marker="s", label=m)
axes[0].set_title("Accuracy vs DEPTH (avg over width)"); axes[0].set_xlabel("depth")
axes[1].set_title("Accuracy vs WIDTH (avg over depth)"); axes[1].set_xlabel("width")
for ax in axes:
    ax.set_ylim(0,1.05); ax.set_ylabel("semantic-following accuracy"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
plt.tight_layout(); plt.savefig("data/v2_moderation.png", dpi=130)
print("\nSaved -> data/v2_moderation.png")
