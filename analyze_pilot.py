"""Analyze the pilot to make the design decisions in A. Slusarz's note."""
import json, glob
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

ev = {e["task_id"]: e for e in json.load(open("data/pilot.json"))}
models = {}
for f in glob.glob("data/pilot_answers/*.json"):
    if f.endswith("raw.json"): continue
    d = json.load(open(f)); models[d["model"]] = d["answers"]
MM = sorted(models)

def correct(m, e):
    return models[m].get(e["task_id"]) == e["gold"]

scored = [e for e in ev.values() if e["cond"] != "none"]   # none has no gold

print("=== overall accuracy (excl. no-instruction) ===")
for m in MM:
    r = [correct(m, e) for e in scored if e["task_id"] in models[m]]
    print(f"  {m:20s} {np.mean(r):.0%}")

# (1) cycle-length shortcut: accuracy by cycle length, per bin (cyclic bins)
print("\n=== (1) cycle-length shortcut (accuracy by cycle_len; higher@small => shortcut) ===")
for b in ["even_one_sided", "odd"]:
    print(f"  {b}:")
    for m in MM:
        accs = {}
        for cyc in sorted({e["cycle_len"] for e in scored if e["divergence_bin"] == b}):
            sub = [correct(m, e) for e in scored if e["divergence_bin"] == b and e["cycle_len"] == cyc and e["task_id"] in models[m]]
            accs[cyc] = np.mean(sub)
        print(f"    {m:18s} " + "  ".join(f"cyc{c}:{a:.0%}" for c, a in accs.items()))

# (2) easy vs hard boundary
print("\n=== (2) boundary: easy (depth=2, eff_width=min) vs hard (depth=16, eff_width=16) ===")
def corner(m, depth, hard):
    sub = []
    for e in scored:
        if e["task_id"] not in models[m]: continue
        is_min = e["effective_width"] == (0 if e["divergence_bin"] == "control" else e["cycle_len"])
        if e["depth"] == depth and ((hard and e["effective_width"] == 16) or (not hard and is_min)):
            sub.append(correct(m, e))
    return np.mean(sub) if sub else float("nan")
for m in MM:
    print(f"  {m:20s} easy {corner(m,2,False):.0%}   hard {corner(m,16,True):.0%}")

# (3) condition screening
print("\n=== (3) per-condition accuracy (which are worth keeping?) ===")
for m in MM:
    cells = []
    for c in ["closed_world", "cred", "skept", "wfs"]:
        sub = [correct(m, e) for e in scored if e["cond"] == c and e["task_id"] in models[m]]
        cells.append(f"{c}:{np.mean(sub):.0%}")
    print(f"  {m:20s} " + "  ".join(cells))
print("  default ('none') -> which semantics does it match?")
for m in MM:
    match = {"cred": 0, "skept": 0, "wfs": 0, "closed_world": 0, "n": 0}
    for e in ev.values():
        if e["cond"] != "none" or e["task_id"] not in models[m]: continue
        a = models[m][e["task_id"]]; rid = e["rec_id"]; match["n"] += 1
        for c in ["cred", "skept", "wfs", "closed_world"]:
            g = ev.get(f"{rid}::{c}", {}).get("gold")
            if g is not None and a == g: match[c] += 1
    n = max(match["n"], 1)
    print(f"    {m:18s} " + "  ".join(f"{c}:{match[c]/n:.0%}" for c in ["cred","skept","wfs","closed_world"]))

# (4) length confound
print("\n=== (4) length confound ===")
allc, allt, alld, allw = [], [], [], []
for m in MM:
    for e in scored:
        if e["task_id"] not in models[m]: continue
        allc.append(correct(m, e)); allt.append(e["length"]["tokens"])
        alld.append(e["depth"]); allw.append(e["effective_width"])
allc, allt, alld, allw = map(lambda x: np.array(x, float), (allc, allt, alld, allw))
print(f"  corr(correct, tokens)      = {np.corrcoef(allt, allc)[0,1]:+.3f}")
print(f"  corr(tokens, depth)        = {np.corrcoef(allt, alld)[0,1]:+.3f}")
print(f"  corr(tokens, eff_width)    = {np.corrcoef(allt, allw)[0,1]:+.3f}")
# partial: correct ~ z(tokens) + z(depth) + z(effwidth)
def z(x): return (x-x.mean())/(x.std()+1e-9)
X = np.column_stack([np.ones(len(allc)), z(allt), z(alld), z(allw)])
beta,*_ = np.linalg.lstsq(X, allc, rcond=None)
print(f"  OLS correct ~ tokens+depth+effwidth: b_tokens={beta[1]:+.3f} "
      f"b_depth={beta[2]:+.3f} b_effwidth={beta[3]:+.3f}")
print("  (effwidth now folds in cycle length, per the note)")
