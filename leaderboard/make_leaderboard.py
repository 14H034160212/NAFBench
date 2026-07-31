"""Build the NAF-Bench leaderboard data splits.

- dev (public, WITH gold): the released production set, for local debugging.
- test (hidden): FRESH certified programs generated with new seeds and deduped
  against the public set by canonical key, so they are not in any public
  release (contamination-resistant). Public prompts go to test_public.jsonl;
  the gold is kept in test_gold.json (server-side only, never released).

Same difficulty as the production set by default (depth 8, width 4). Increase
DEPTH/WIDTH/CYC below for a harder tier if frontier models saturate.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nafbench.instances import build_variant, canonical_key, BIN_SIGNATURE
from nafbench.solvers import stable_cred_skept, wfs_query
from nafbench import verbalize_generic as VG
from nafbench.verbalize_v2 import gold_for

DEPTH, WIDTH = 8, 4
CYC = {"control": 2, "even_one_sided": 4, "odd": 3, "even_both_sided": 4}
BINS = ["control", "even_one_sided", "odd", "even_both_sided"]
CONDS = ["none", "closed_world", "cred", "skept", "wfs"]
N_PER_CELL = 25          # hidden-test programs per bin
SEED_START = 100000      # high offset: disjoint from the public set's seeds
WMAP = {"true": "T", "false": "F", "undefined": "u"}
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def excluded_keys():
    """Canonical keys of every program already public (production set), so the
    hidden test cannot accidentally reuse one."""
    keys = set()
    prod = json.load(open(os.path.join(ROOT, "data/production_set.json")))
    seeds_by_bin = {}
    for it in prod:
        seeds_by_bin.setdefault(it["divergence_bin"], set()).add(it["variant_seed"])
    for b, seeds in seeds_by_bin.items():
        for s in seeds:
            prog = build_variant(DEPTH, WIDTH, b, CYC[b], s)
            keys.add(canonical_key(prog))
    return keys


def build_hidden():
    exclude = excluded_keys()
    test_items = []
    for b in BINS:
        exp = BIN_SIGNATURE[b]
        kept, seen, seed = [], set(exclude), SEED_START
        while len(kept) < N_PER_CELL and seed < SEED_START + 200000:
            prog = build_variant(DEPTH, WIDTH, b, CYC[b], seed); seed += 1
            cr, sk, nmods, conf, ch = stable_cred_skept(prog, "q")
            wl = WMAP[wfs_query(prog, "q")]
            sldnf = "loop" if b != "control" else "T"
            if (cr, sk, wl, sldnf) != tuple(exp):
                continue
            key = canonical_key(prog)
            if key in seen:
                continue
            seen.add(key)
            kept.append((prog, {"cred": cr, "skept": sk, "wfs": wl, "sldnf": sldnf}))
        assert len(kept) == N_PER_CELL, f"{b}: only {len(kept)}"
        for idx, (prog, labels) in enumerate(kept):
            for c in CONDS:
                test_items.append({
                    "task_id": f"naflb-{b}-i{idx}-{c}::{c}",
                    "rec_id": f"naflb-{b}-i{idx}",
                    "cond": c, "divergence_bin": b,
                    "gold": None if c == "none" else gold_for(labels, c),
                    "prompt": VG.build_prompt(prog, c),
                })
    return test_items


def main():
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)

    # dev split = public production set (with gold), for debugging
    prod = json.load(open(os.path.join(ROOT, "data/production_set.json")))
    with open(os.path.join(HERE, "data/dev.jsonl"), "w") as f:
        for it in prod:
            f.write(json.dumps({"id": it["task_id"], "cond": it["cond"],
                                "divergence_bin": it["divergence_bin"],
                                "gold": it["gold"], "prompt": it["prompt"]}) + "\n")

    # hidden test: public prompts (no gold) + private gold
    test = build_hidden()
    with open(os.path.join(HERE, "data/test_public.jsonl"), "w") as f:
        for it in test:
            f.write(json.dumps({"id": it["task_id"], "prompt": it["prompt"]}) + "\n")
    gold = {it["task_id"]: {"gold": it["gold"], "cond": it["cond"],
                            "divergence_bin": it["divergence_bin"],
                            "rec_id": it["rec_id"]} for it in test}
    json.dump(gold, open(os.path.join(HERE, "data/test_gold.json"), "w"), indent=1)

    nprog = len({it["rec_id"] for it in test})
    print(f"dev: {len(prod)} prompts (public, with gold)")
    print(f"test: {len(test)} prompts over {nprog} hidden programs "
          f"({N_PER_CELL}/bin); gold in data/test_gold.json (keep private)")


if __name__ == "__main__":
    main()
