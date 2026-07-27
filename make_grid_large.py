"""Larger-sample depth x width grid (a collaborator's 'larger sample' request).

Extends the single-program-per-cell v2 grid (make_v2_eval) to N distinct,
gold-preserving programs per (depth, width) cell, so the marginal accuracies in
the size sweep get real program-clustered CIs. Bin fixed to even_one_sided
(as in the original grid); conds span A/B/C. Fast certification path
(stable_cred_skept + wfs_query; SLDNF is 'loop' for these cyclic shapes),
mirroring make_production.
"""
import json
from nafbench.instances import build_variant, canonical_key, BIN_SIGNATURE
from nafbench.solvers import stable_cred_skept, wfs_query
from nafbench import verbalize_generic as VG
from nafbench.verbalize_v2 import gold_for
from nafbench import metrics as MET

BIN = "even_one_sided"
CYC = 4
DEPTHS = [0, 2, 4, 6, 8]
WIDTHS = [0, 2, 4, 6, 8]
CONDS = ["cred", "skept", "wfs"]
N_PER_CELL = 3
WMAP = {"true": "T", "false": "F", "undefined": "u"}
exp = BIN_SIGNATURE[BIN]

items = []
for d in DEPTHS:
    for w in WIDTHS:
        kept, seen, seed = [], set(), 0
        while len(kept) < N_PER_CELL and seed < 400:
            prog = build_variant(d, w, BIN, CYC, seed); seed += 1
            cr, sk, nmods, conf, ch = stable_cred_skept(prog, "q")
            wl = WMAP[wfs_query(prog, "q")]
            if (cr, sk, wl, "loop") != tuple(exp):
                continue
            key = canonical_key(prog)
            if key in seen:
                continue
            seen.add(key)
            kept.append((prog, {"cred": cr, "skept": sk, "wfs": wl, "sldnf": "loop"},
                         nmods, conf, ch))
        for idx, (prog, labels, nmods, conf, ch) in enumerate(kept):
            for c in CONDS:
                prompt = VG.build_prompt(prog, c)
                items.append({
                    "task_id": f"grid-{BIN}-d{d}-w{w}-i{idx}-{c}::{c}",
                    "rec_id": f"grid-{BIN}-d{d}-w{w}-i{idx}",
                    "cond": c, "divergence_bin": BIN, "instance": idx,
                    "depth": d, "width": w, "cycle_len": CYC,
                    "gold": gold_for(labels, c), "labels": labels,
                    "n_stable_models": nmods,
                    "metrics": {"clingo_conflicts": conf, "clingo_choices": ch},
                    "variant_seed": prog.meta["variant_seed"],
                    "program": prog.pretty(), "length": MET.length_metrics(prompt),
                    "prompt": prompt,
                })
        print(f"  d={d} w={w}: {len(kept)} variants")

json.dump(items, open("data/grid_large_set.json", "w"), indent=1)
nprog = len({e["rec_id"] for e in items})
print(f"grid_large: {len(items)} prompts over {nprog} distinct programs "
      f"({len(DEPTHS)}x{len(WIDTHS)} cells, up to {N_PER_CELL}/cell, {len(CONDS)} conds)")
