"""Rule-reordering robustness set (meeting 2026-07-08, collaborators).

Reordering the rule sentences does NOT change the program's semantics, so the
certified gold is invariant. This set therefore isolates whether an LLM's answer
is sensitive to the ORDER in which the rules are presented -- a robustness /
confound axis alongside verbalization. We also record solver hardness so we can
check whether order changes operational difficulty.

For each (bin, condition) we emit K rule orderings at a fixed (depth, width):
  asis (as-written), reversed, and 3 seeded random permutations.
rec_id groups the K orderings of one (bin, condition) so accuracy VARIANCE across
orderings is the metric of interest.
"""
import json
import random
from nafbench.instances import build_instance
from nafbench import solvers as S
from nafbench import verbalize_v2 as V2

BINS = ["control", "even_one_sided", "odd", "even_both_sided"]
CYC = {"control": 2, "even_one_sided": 4, "odd": 3, "even_both_sided": 4}
CONDS = ["cred", "skept", "wfs", "closed_world"]
DEPTH, WIDTH, THEME = 2, 4, 0
N_RANDOM = 3

items = []
for b in BINS:
    prog = build_instance(DEPTH, WIDTH, b, cycle_len=CYC[b])
    cert = S.certify_full(prog, "q")
    n = V2.n_rule_lines(prog, THEME)
    # build the K orderings (deterministic)
    orders = [("asis", list(range(n))), ("reversed", list(range(n))[::-1])]
    for r in range(N_RANDOM):
        rng = random.Random(1000 * BINS.index(b) + r)  # reproducible per (bin, r)
        perm = list(range(n)); rng.shuffle(perm)
        orders.append((f"rand{r + 1}", perm))
    for c in CONDS:
        gold = V2.gold_for(cert["labels"], c)
        for oid, order in orders:
            prompt = V2.build_prompt(prog, c, theme=THEME, order=order)
            items.append({
                "task_id": f"reorder-{b}-{c}-{oid}::{c}",
                "rec_id": f"reorder-{b}-{c}",          # groups the K orderings
                "cond": c, "divergence_bin": b, "order_id": oid, "order": order,
                "depth": DEPTH, "width": WIDTH, "cycle_len": CYC[b],
                "n_rule_lines": n, "gold": gold,
                "labels": cert["labels"], "n_stable_models": cert["n_stable_models"],
                "metrics": cert["metrics"], "program": prog.pretty(),
                "prompt": prompt,
            })

json.dump(items, open("data/reorder_set.json", "w"), indent=1)
n_inst = len({e["rec_id"] for e in items})
print(f"reorder set: {len(items)} prompts "
      f"({len(BINS)} bins x {len(CONDS)} conds x {2 + N_RANDOM} orderings) "
      f"over {n_inst} (bin,cond) groups")
# sanity: gold must be constant within each rec_id (order does not change logic)
from collections import defaultdict
g = defaultdict(set)
for e in items:
    g[e["rec_id"]].add(e["gold"])
bad = [k for k, v in g.items() if len(v) > 1]
print("groups with order-dependent gold (must be empty):", bad or "none")
