"""Full v3 analysis: does effective_width (cycle folded in) dominate depth,
controlling for instance length? Plus per-condition / default behaviour."""
import json, glob
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

ev = {e["task_id"]: e for e in json.load(open("data/v3_full.json"))}
models = {}
for f in glob.glob("data/v3_answers/*.json"):
    if f.endswith("raw.json"): continue
    d = json.load(open(f)); models[d["model"]] = d["answers"]
MM = sorted(models)
BINS = ["control", "even_one_sided", "odd", "even_both_sided"]
scored = [e for e in ev.values() if e["cond"] != "none"]

def ok(m, e): return models[m].get(e["task_id"]) == e["gold"]
def bal(m):
    g = {}
    for e in scored:
        if e["task_id"] in models[m]:
            g.setdefault((e["divergence_bin"], e["cond"]), []).append(ok(m, e))
    return np.mean([np.mean(v) for v in g.values()])

print(f"=== accuracy (excl. no-instruction); coverage n of {len(scored)} scored ===")
for m in MM:
    r = [ok(m, e) for e in scored if e["task_id"] in models[m]]
    print(f"  {m:20s} raw {np.mean(r):.0%}   balanced {bal(m):.0%}   (n={len(r)}/{len(scored)})")

def design(ms):
    rows = []
    for m in ms:
        for e in scored:
            if e["task_id"] in models[m]:
                rows.append((e["depth"], e["effective_width"], e["length"]["tokens"],
                             e["divergence_bin"], ok(m, e)))
    return rows

def z(x): return (x - x.mean()) / (x.std() + 1e-9)
nonsat = [m for m in MM if np.mean([ok(m, e) for e in scored if e["task_id"] in models[m]]) < 0.92]
R = design(nonsat or MM)
dep = np.array([r[0] for r in R], float); ew = np.array([r[1] for r in R], float)
tok = np.array([r[2] for r in R], float); y = np.array([r[4] for r in R], float)
binm = np.array([[1.0 if r[3] == b else 0.0 for b in BINS[1:]] for r in R])

print(f"\n=== standardized OLS on non-saturated models {nonsat} ===")
for label, cols, names in [
    ("without length", [z(dep), z(ew)], ["z(depth)", "z(eff_width)"]),
    ("controlling for length", [z(dep), z(ew), z(tok)], ["z(depth)", "z(eff_width)", "z(tokens)"]),
]:
    X = np.column_stack([np.ones(len(R))] + cols + [binm])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    alln = ["intercept"] + names + [f"bin={b}" for b in BINS[1:]]
    print(f"  [{label}]")
    for n, b in zip(alln, beta):
        print(f"     {n:16s} {b:+.3f}")
    bd, bw = beta[1], beta[2]
    print(f"     -> stronger: {'EFF_WIDTH' if abs(bw) > abs(bd) else 'DEPTH'} "
          f"(|eff_width|={abs(bw):.3f} vs |depth|={abs(bd):.3f})")

print("\n=== per-condition accuracy ===")
for m in MM:
    cells = [f"{c}:{np.mean([ok(m,e) for e in scored if e['cond']==c and e['task_id'] in models[m]]):.0%}"
             for c in ["closed_world", "cred", "skept", "wfs"]]
    print(f"  {m:20s} " + "  ".join(cells))

# moderation plot (eff_width vs depth) with theme error bars, non-saturated
fig, ax = plt.subplots(1, 2, figsize=(13, 5))
for m in (nonsat or MM):
    for idx, A in [(0, ax[0]), (1, ax[1])]:
        key = "depth" if idx == 0 else "effective_width"
        xs = sorted({e[key] for e in scored})
        mu, er = [], []
        for v in xs:
            per = []
            for th in {e["theme"] for e in scored}:
                vals = [ok(m, e) for e in scored if e[key] == v and e["theme"] == th and e["task_id"] in models[m]]
                if vals: per.append(np.mean(vals))
            mu.append(np.mean(per)); er.append(np.std(per))
        A.errorbar(xs, mu, yerr=er, marker="o", capsize=3, label=m)
ax[0].set_title("Accuracy vs DEPTH"); ax[0].set_xlabel("depth")
ax[1].set_title("Accuracy vs EFFECTIVE WIDTH (cycle folded in)"); ax[1].set_xlabel("effective width")
for a in ax: a.set_ylim(0, 1.05); a.set_ylabel("semantic-following accuracy"); a.grid(alpha=.3); a.legend(fontsize=8)
plt.tight_layout(); plt.savefig("data/v3_moderation.png", dpi=130)
print("\nSaved -> data/v3_moderation.png")
