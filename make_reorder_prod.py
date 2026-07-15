"""Production-scale rule-reordering robustness set.

Unlike the pilot (one canonical program per bin), this uses MANY distinct
gold-preserving programs (via build_variant) and renders EACH in K rule orders,
so order-sensitivity is measured over a proper program population. Gold is
invariant across orderings (reordering does not change the logic), so any change
in the model's answer across the K orders is pure order-sensitivity.

N distinct programs per bin x 4 conditions x K orderings, rendered rule-by-rule
(verbalize_generic). rec_id = (program, condition); the metric is the fraction of
(program, condition) groups whose answer is NOT constant across the K orders.
"""
import json, random
from nafbench.instances import build_variant, canonical_key, BIN_SIGNATURE
from nafbench.solvers import stable_cred_skept, wfs_query
from nafbench.program import Program
from nafbench import verbalize_generic as VG
from nafbench.verbalize_v2 import gold_for
from nafbench import metrics as MET

DEPTH, WIDTH = 8, 4
CYC = {"control": 2, "even_one_sided": 4, "odd": 3, "even_both_sided": 4}
BINS = ["control", "even_one_sided", "odd", "even_both_sided"]
CONDS = ["closed_world", "cred", "skept", "wfs"]
N_PER_BIN = 10          # distinct programs per bin
K_ORDERS = 4            # identity + reversed + 2 seeded shuffles
WMAP = {"true": "T", "false": "F", "undefined": "u"}

items = []
for b in BINS:
    exp = BIN_SIGNATURE[b]
    kept, seen, seed = [], set(), 0
    while len(kept) < N_PER_BIN and seed < 100000:
        prog = build_variant(DEPTH, WIDTH, b, CYC[b], seed); seed += 1
        cr, sk, nm, cf, ch = stable_cred_skept(prog, "q")
        wl = WMAP[wfs_query(prog, "q")]
        sldnf = "loop" if b != "control" else "T"
        if (cr, sk, wl, sldnf) != tuple(exp):
            continue
        key = canonical_key(prog)
        if key in seen:
            continue
        seen.add(key)
        kept.append((prog, {"cred": cr, "skept": sk, "wfs": wl, "sldnf": sldnf}))
    assert len(kept) == N_PER_BIN, f"{b}: only {len(kept)}"
    for idx, (prog, labels) in enumerate(kept):
        base = list(prog.rules)
        n = len(base)
        orders = [("asis", list(range(n))), ("reversed", list(range(n))[::-1])]
        for r in range(K_ORDERS - 2):
            rng = random.Random(97 * idx + 7 * r + BINS.index(b))
            perm = list(range(n)); rng.shuffle(perm)
            orders.append((f"rand{r + 1}", perm))
        for c in CONDS:
            gold = gold_for(labels, c)
            for oid, perm in orders:
                po = Program([base[i] for i in perm]); po.meta = dict(prog.meta)
                prompt = VG.build_prompt(po, c)
                items.append({
                    "task_id": f"reop-{b}-i{idx}-{c}-{oid}::{c}",
                    "rec_id": f"reop-{b}-i{idx}-{c}",     # groups the K orderings
                    "cond": c, "divergence_bin": b, "instance": idx, "order_id": oid,
                    "gold": gold, "labels": labels,
                    "length": MET.length_metrics(prompt), "prompt": prompt,
                })

json.dump(items, open("data/reorder_prod_set.json", "w"), indent=1)
ngroups = len({e["rec_id"] for e in items})
print(f"production reorder set: {len(items)} prompts = {len(BINS)} bins x "
      f"{N_PER_BIN} programs x {len(CONDS)} conds x {K_ORDERS} orders "
      f"({ngroups} (program,cond) groups)")
# gold invariant within each group
from collections import defaultdict
g = defaultdict(set)
for e in items:
    if e["gold"]:
        g[e["rec_id"]].add(e["gold"])
print("groups with order-dependent gold (must be empty):", [k for k, v in g.items() if len(v) > 1] or "none")
