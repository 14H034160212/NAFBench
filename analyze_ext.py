"""Extended-range analysis (depth/eff_width up to 32): do the structural
moderators grow with range, and does effective-width dominate depth once length
is controlled? Plus the fuller model panel (incl. GPT-5; Opus on a slice)."""
import json, glob
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

ev = {e["task_id"]: e for e in json.load(open("data/v3_ext.json"))}
models = {}
for f in glob.glob("data/ext_answers/*.json"):
    if f.endswith("raw.json"): continue
    d = json.load(open(f)); models[d["model"]] = d["answers"]
MM = sorted(models)
BINS = ["control", "even_one_sided", "odd", "even_both_sided"]
scored = [e for e in ev.values() if e["cond"] != "none"]

def ok(m, e): return models[m].get(e["task_id"]) == e["gold"]
def cover(m): return sum(1 for e in scored if e["task_id"] in models[m])

print("=== accuracy (excl. no-instruction); coverage in parens ===")
for m in MM:
    r = [ok(m, e) for e in scored if e["task_id"] in models[m]]
    print(f"  {m:20s} {np.mean(r):.0%}   (n={cover(m)})")

# regression on FULL-coverage non-saturated models
full = [m for m in MM if cover(m) >= len(scored) - 2]
nonsat = [m for m in full if np.mean([ok(m, e) for e in scored if e["task_id"] in models[m]]) < 0.92]
print(f"\nfull-coverage models: {full}\nnon-saturated: {nonsat}")

R = [(e["depth"], e["effective_width"], e["length"]["tokens"], e["divergence_bin"], ok(m, e))
     for m in (nonsat or full) for e in scored if e["task_id"] in models[m]]
dep = np.array([r[0] for r in R], float); ew = np.array([r[1] for r in R], float)
tok = np.array([r[2] for r in R], float); y = np.array([r[4] for r in R], float)
binm = np.array([[1.0 if r[3] == b else 0.0 for b in BINS[1:]] for r in R])
def z(x): return (x - x.mean()) / (x.std() + 1e-9)
print("\n=== standardized OLS (range up to 32) ===")
for label, cols, names in [
    ("no length", [z(dep), z(ew)], ["z(depth)", "z(eff_width)"]),
    ("+length",   [z(dep), z(ew), z(tok)], ["z(depth)", "z(eff_width)", "z(tokens)"]),
]:
    X = np.column_stack([np.ones(len(R))] + cols + [binm])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    nm = ["intercept"] + names + [f"bin={x}" for x in BINS[1:]]
    print(f"  [{label}] " + "  ".join(f"{n}={v:+.3f}" for n, v in zip(nm, b)))
    print(f"     -> {'EFF_WIDTH' if abs(b[2])>abs(b[1]) else 'DEPTH'} stronger "
          f"(|ew|={abs(b[2]):.3f} vs |d|={abs(b[1]):.3f})")

print("\n=== per-condition accuracy (full panel) ===")
for m in MM:
    cells = []
    for c in ["closed_world", "cred", "skept", "wfs"]:
        sub = [ok(m, e) for e in scored if e["cond"] == c and e["task_id"] in models[m]]
        cells.append(f"{c}:{np.mean(sub):.0%}" if sub else f"{c}:--")
    print(f"  {m:20s} " + "  ".join(cells))

# moderation vs depth and vs eff_width (full-coverage models)
fig, ax = plt.subplots(1, 2, figsize=(13, 5))
for m in full:
    for idx, A in [(0, ax[0]), (1, ax[1])]:
        key = "depth" if idx == 0 else "effective_width"
        xs = sorted({e[key] for e in scored})
        ys = [np.mean([ok(m, e) for e in scored if e[key] == v and e["task_id"] in models[m]]) for v in xs]
        A.plot(xs, ys, marker="o", label=m)
ax[0].set_title("Accuracy vs DEPTH (to 32)"); ax[0].set_xlabel("depth")
ax[1].set_title("Accuracy vs EFFECTIVE WIDTH (to 32)"); ax[1].set_xlabel("effective width")
for a in ax: a.set_ylim(0, 1.05); a.set_ylabel("semantic-following accuracy"); a.grid(alpha=.3); a.legend(fontsize=8)
plt.tight_layout(); plt.savefig("data/ext_moderation.png", dpi=130)
print("\nSaved -> data/ext_moderation.png")
