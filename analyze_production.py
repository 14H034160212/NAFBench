"""Aggregate the production run: per-model, per-condition accuracy with 95% CIs
CLUSTERED BY PROGRAM (nafbench.clusterstats), plus default-semantics reversion.
Reads every data/production_answers/run*/<model>.json repeat."""
import json, glob, os
from collections import defaultdict
from nafbench.clusterstats import cluster_bootstrap_ci

ev = {e["task_id"]: e for e in json.load(open("data/production_set.json"))}
RUNS = sorted(glob.glob("data/production_answers/run*"))
CONDS = ["closed_world", "cred", "skept", "wfs"]
models = sorted({os.path.basename(f)[:-5] for r in RUNS
                 for f in glob.glob(f"{r}/*.json") if not f.endswith("raw.json")})


def ans(model, run, tid):
    p = f"{run}/{model}.json"
    if not os.path.exists(p):
        return None
    return json.load(open(p))["answers"].get(tid)


print(f"=== production: {len(ev)} base prompts, {len(RUNS)} repeats, "
      f"{len(models)} models; 95% CI clustered by program ===")
for m in models:
    print(f"\n  {m}")
    for c in CONDS:
        by_prog = defaultdict(list)
        for t, e in ev.items():
            if e["cond"] != c or e["gold"] is None:
                continue
            for r in RUNS:
                a = ans(m, r, t)
                if a is not None:
                    by_prog[e["rec_id"]].append(int(a == e["gold"]))
        p, lo, hi, k, n, npr = cluster_bootstrap_ci(by_prog)
        print(f"    {c:13s} {p:.0%} [{lo:.0%},{hi:.0%}]  ({k}/{n} over {npr} programs)")

print("\n=== default-semantics reversion (clustered by program) ===")
# reversion: for each program, when told a semantics whose gold differs from the
# model's no-instruction ('none') answer, does it keep that default answer anyway?
none_items = [e for e in ev.values() if e["cond"] == "none"]
for m in models:
    by_prog = defaultdict(list)
    for e0 in none_items:
        rid = e0["rec_id"]                       # e.g. 'prod-control'
        for r in RUNS:
            d = ans(m, r, e0["task_id"])         # the no-instruction answer
            if d is None:
                continue
            for c in CONDS:
                ge = ev.get(f"{rid}-{c}::{c}")
                if ge and ge["gold"] is not None and ge["gold"] != d:
                    keep = ans(m, r, ge["task_id"])
                    if keep is not None:
                        by_prog[rid].append(int(keep == d))
    p, lo, hi, k, n, npr = cluster_bootstrap_ci(by_prog)
    if n:
        print(f"  {m:20s} {p:.0%} [{lo:.0%},{hi:.0%}]  ({k}/{n} over {npr} programs)")
