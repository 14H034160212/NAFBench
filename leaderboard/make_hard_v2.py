"""Harder tier (v2): push the combinatorial axis.

Beyond hard_ladder (v1), this set stresses the two quantifiers that reasoning
over exponentially many stable models exposes:

  - independent  (disjunctive q): q true if ANY of n cycles picks its 'a'.
    q is false in only 1 of 2**n models -> SKEPTICAL must find that one world.
  - conjunctive  q: q true only if ALL n cycles pick 'a' (1 of 2**n models) ->
    CREDULOUS must find that one world.
  - interdependent: coupled cycles (share atoms) -> entangled reasoning.

n is swept up to 6 (2**6 = 64 stable models). A short cycle-length ladder is
kept as a control (world count stays 2, so if the frontier holds there but drops
on the combinatorial axis, the axis -- not mere length -- is what matters).
All certified to (T, F, u, loop): credulous/skeptical/WFS gold = A/B/C.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from nafbench.instances import build_variant, canonical_key
from nafbench.solvers import stable_cred_skept, wfs_query
from nafbench import verbalize_generic as VG
from nafbench.verbalize_v2 import gold_for
from leaderboard.hard_instances import gen_multi_variants

CONDS = ["none", "closed_world", "cred", "skept", "wfs"]
WMAP = {"true": "T", "false": "F", "undefined": "u"}
N_VARIANTS = 8

# combinatorial axis: (subtype, tag, n-levels)
COMBO = [
    ("independent",    "disj",    [2, 3, 4, 5, 6]),   # skeptical-hard
    ("conjunctive",    "conj",    [2, 3, 4, 5, 6]),   # credulous-hard
    ("interdependent", "coupled", [2, 3, 4, 5]),      # entangled
]
# control axis: cycle length (world count stays 2)
CYCLEN = [4, 8]
CYCLEN_BINS = ["even_one_sided", "odd"]


def emit(items, prog, labels, axis, difficulty, idx, nmods):
    for c in CONDS:
        items.append({
            "id": f"hv2-{axis}-{difficulty}-i{idx}-{c}::{c}",
            "rec_id": f"hv2-{axis}-{difficulty}-i{idx}",
            "axis": axis, "difficulty": difficulty, "n_stable_models": nmods,
            "divergence_bin": "even_one_sided", "cond": c,
            "gold": None if c == "none" else gold_for(labels, c),
            "prompt": VG.build_prompt(prog, c),
        })


def main():
    items = []
    for sub, tag, levels in COMBO:
        for n in levels:
            for idx, (prog, labels, nmods) in enumerate(
                    gen_multi_variants(sub, n, N_VARIANTS, seed0=n * 1000)):
                emit(items, prog, labels, "combo", f"{tag}_n{n}", idx, nmods)
    # cycle-length control
    for cyc in CYCLEN:
        for b in CYCLEN_BINS:
            kept, seen, seed = 0, set(), 0
            while kept < N_VARIANTS and seed < 50000:
                prog = build_variant(8, 4, b, cyc, seed); seed += 1
                cr, sk, nmods, conf, ch = stable_cred_skept(prog, "q")
                wl = WMAP[wfs_query(prog, "q")]
                key = canonical_key(prog)
                if key in seen:
                    continue
                seen.add(key)
                labels = {"cred": cr, "skept": sk, "wfs": wl, "sldnf": "loop"}
                emit(items, prog, labels, "cyclen", f"{b}_k{cyc}", kept, nmods)
                kept += 1

    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    out = os.path.join(HERE, "data/hard_v2.jsonl")
    with open(out, "w") as f:
        for it in items:
            f.write(json.dumps(it) + "\n")
    from collections import Counter
    nprog = len({it["rec_id"] for it in items})
    print(f"hard v2: {len(items)} prompts over {nprog} programs -> {out}")
    lvl = {}
    for it in items:
        if it["cond"] == "none":
            lvl.setdefault((it["axis"], it["difficulty"]), [0, it["n_stable_models"]])
            lvl[(it["axis"], it["difficulty"])][0] += 1
    for (axis, d), (n, nm) in sorted(lvl.items()):
        print(f"  {axis:7} {d:16} : {n} programs   (stable models = {nm})")


if __name__ == "__main__":
    main()
