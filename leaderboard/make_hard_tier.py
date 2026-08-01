"""Build a certified DIFFICULTY LADDER for the leaderboard's hard tier.

Goal: find the difficulty at which frontier models stop scoring 100% joint.
Two difficulty axes, both solver-certified (gold stays exact):

  A) cycle length  -- longer negation cycles to trace (build_variant, cyc in
     {4,6,8,10}); stable-model count stays 2, so this stresses chain-tracing.
  B) number of independent cycles -- the combinatorial axis: k independent
     2-cycles give 2^k stable models, so skeptical/credulous entailment must
     reason over exponentially many models (build_multi_independent /
     build_interdependent). This is the axis most likely to break the frontier.

Each program is rendered under the three specified readings that diverge
(credulous / skeptical / WFS; SLDNF loops on all of these) plus the
no-instruction baseline. Output includes gold + a difficulty label so a single
frontier run yields an accuracy-vs-difficulty curve.

The output (gold + solver-recoverable prompts) is a candidate hidden set --
gitignored, regenerate locally.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nafbench.instances import (build_variant, build_multi_independent,
                                build_interdependent, canonical_key)
from nafbench.solvers import stable_cred_skept, wfs_query
from nafbench import verbalize_generic as VG
from nafbench.verbalize_v2 import gold_for

CONDS = ["none", "closed_world", "cred", "skept", "wfs"]
WMAP = {"true": "T", "false": "F", "undefined": "u"}
HERE = os.path.dirname(os.path.abspath(__file__))

DEPTH, WIDTH = 8, 4
N_VARIANTS = 8            # distinct programs per cycle-length rung per bin
CYCLE_LENS = [4, 6, 8, 10]
CYCLE_BINS = ["even_one_sided", "odd", "even_both_sided"]
MULTI_N = [2, 3, 4]      # independent cycles -> 2^n stable models
INTERDEP_N = [2, 3]


def certify(prog, bin_name):
    cr, sk, nmods, conf, ch = stable_cred_skept(prog, "q")
    wl = WMAP[wfs_query(prog, "q")]
    labels = {"cred": cr, "skept": sk, "wfs": wl, "sldnf": "loop"}
    return labels, nmods


def emit(items, prog, bin_name, axis, difficulty, idx, nmods):
    labels, _ = certify(prog, bin_name)
    for c in CONDS:
        items.append({
            "id": f"hard-{axis}-{difficulty}-{bin_name}-i{idx}-{c}::{c}",
            "rec_id": f"hard-{axis}-{difficulty}-{bin_name}-i{idx}",
            "axis": axis, "difficulty": difficulty, "divergence_bin": bin_name,
            "n_stable_models": nmods, "cond": c,
            "gold": None if c == "none" else gold_for(labels, c),
            "prompt": VG.build_prompt(prog, c),
        })


def main():
    items = []
    # Axis A: cycle length
    for cyc in CYCLE_LENS:
        for b in CYCLE_BINS:
            kept, seen, seed = 0, set(), 0
            while kept < N_VARIANTS and seed < 50000:
                prog = build_variant(DEPTH, WIDTH, b, cyc, seed); seed += 1
                labels, nmods = certify(prog, b)
                key = canonical_key(prog)
                if key in seen:
                    continue
                seen.add(key)
                emit(items, prog, b, "cyclen", cyc, kept, nmods)
                kept += 1
    # Axis B: number of independent / interdependent cycles (combinatorial)
    for n in MULTI_N:
        prog = build_multi_independent(n)
        _, nmods = certify(prog, "even_one_sided")
        emit(items, prog, "multi", "multi", "indep_n%d" % n, 0, nmods)
    for n in INTERDEP_N:
        prog = build_interdependent(n)
        _, nmods = certify(prog, "even_one_sided")
        emit(items, prog, "multi", "multi", "interdep_n%d" % n, 0, nmods)

    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    out = os.path.join(HERE, "data/hard_ladder.jsonl")
    with open(out, "w") as f:
        for it in items:
            f.write(json.dumps(it) + "\n")
    nprog = len({it["rec_id"] for it in items})
    from collections import Counter
    diff = Counter((it["axis"], it["difficulty"]) for it in items if it["cond"] == "none")
    print(f"hard ladder: {len(items)} prompts over {nprog} programs -> {out}")
    for (axis, d), n in sorted(diff.items()):
        print(f"  {axis:7} {d:12} : {n} programs")


if __name__ == "__main__":
    main()
