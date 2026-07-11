"""Production headline set — option (b): 30 DISTINCT programs per cell.

Per A. Słusarz (2026-07): fixed (depth, width), one verbalization, 30 distinct
programs per cell. A "cell" is a divergence bin at the fixed size; the 30
instances are structurally distinct, gold-preserving variants (nafbench.instances
.build_variant: variable aggregators / support distribution / cq&wide attach
points / cycle guards / rule order), deduplicated by an isomorphism-insensitive
canonical key. Rendered with the faithful rule-level verbalizer (verbalize_generic)
so the structural differences actually appear in the natural-language prompt.

Settings (agreed): depth = 8, width = 4, cycle even = 4 / odd = 3.
"""
import json
from nafbench.instances import build_variant, canonical_key, BIN_SIGNATURE
from nafbench.solvers import stable_cred_skept, wfs_query
from nafbench import verbalize_generic as VG
from nafbench.verbalize_v2 import gold_for
from nafbench import metrics as MET

DEPTH, WIDTH = 8, 4
CYC = {"control": 2, "even_one_sided": 4, "odd": 3, "even_both_sided": 4}
BINS = ["control", "even_one_sided", "odd", "even_both_sided"]
CONDS = ["none", "closed_world", "cred", "skept", "wfs"]
N_PER_CELL = 30
WMAP = {"true": "T", "false": "F", "undefined": "u"}

items = []
for b in BINS:
    exp = BIN_SIGNATURE[b]                        # (cred, skept, wfs, sldnf)
    kept, seen_keys, seed = [], set(), 0
    while len(kept) < N_PER_CELL and seed < 100000:
        prog = build_variant(DEPTH, WIDTH, b, CYC[b], seed); seed += 1
        cr, sk, nmods, conf, ch = stable_cred_skept(prog, "q")
        wl = WMAP[wfs_query(prog, "q")]
        # SLDNF label is deterministic for these shapes (cyclic -> loop; control
        # terminates true, which the bin signature encodes as "T").
        sldnf = "loop" if b != "control" else "T"
        if (cr, sk, wl, sldnf) != tuple(exp):     # gold must be invariant
            continue
        key = canonical_key(prog)
        if key in seen_keys:                      # drop isomorphic duplicates
            continue
        seen_keys.add(key)
        labels = {"cred": cr, "skept": sk, "wfs": wl, "sldnf": sldnf}
        kept.append((prog, labels, nmods, conf, ch))
    assert len(kept) == N_PER_CELL, f"{b}: only {len(kept)} distinct variants"
    for idx, (prog, labels, nmods, conf, ch) in enumerate(kept):
        for c in CONDS:
            prompt = VG.build_prompt(prog, c)
            items.append({
                "task_id": f"prod-{b}-i{idx}-{c}::{c}",
                "rec_id": f"prod-{b}-i{idx}",         # one distinct program = one cluster
                "cond": c, "divergence_bin": b, "instance": idx,
                "depth": DEPTH, "width": WIDTH, "cycle_len": CYC[b],
                "gold": None if c == "none" else gold_for(labels, c),
                "labels": labels, "n_stable_models": nmods,
                "metrics": {"clingo_conflicts": conf, "clingo_choices": ch},
                "variant_seed": prog.meta["variant_seed"],
                "program": prog.pretty(), "length": MET.length_metrics(prompt),
                "prompt": prompt,
            })

json.dump(items, open("data/production_set.json", "w"), indent=1)
n_prog = len({e["rec_id"] for e in items})
print(f"production set (option b): {len(items)} prompts = {len(BINS)} bins x "
      f"{N_PER_CELL} distinct programs x {len(CONDS)} conds  ({n_prog} programs total)")
print(f"depth {DEPTH} / width {WIDTH}, cycle even={CYC['even_one_sided']}/odd={CYC['odd']}, "
      f"faithful generic verbalization")
print("token range:", min(e['length']['tokens'] for e in items), "..",
      max(e['length']['tokens'] for e in items))
