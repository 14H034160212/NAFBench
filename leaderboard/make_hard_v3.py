"""hard_v3: difficulty validated against a solver, and an answer key that is
not guessable from the condition name.

Two things went wrong in hard_v2, both found by running it:

1. Every one of its 144 programs certifies to (cred=T, skept=F, wfs=u,
   sldnf=loop), because hard_instances.gen_multi_variants rejects anything
   else. Gold is therefore a function of the condition name alone
   (cw=C, cred=A, skept=B, wfs=C) and a model that never reads a program
   scores 100% JOINT. o4-mini scored 83.3% -- below the constant-guesser
   baseline.
2. The combinatorial axis is decided by propagation, not search: 16x the
   stable models bought 1.15-1.37x reasoning tokens, and clingo solves the
   whole set with 0-1 conflicts.

This set fixes (1) by mixing certified signatures across families, and
addresses (2) by adding a family whose queries are real search problems --
while keeping the families that stress other capabilities.

A finding from building it, which changed the design: **clingo conflicts and
LLM effort are not the same axis.** `coupled` solves with 0 conflicts yet
produced the steepest o4-mini effort curve in v2 (1.56x), and `parity` is
likewise conflict-free while forcing state to be tracked through n gadgets.
So the conflict filter is applied per family (see HARDNESS_KIND in
hard_instances_v3.py) rather than globally; a blanket "reject conflicts == 0"
would have discarded the axis that empirically works best on models.

Families, and what each is for:
  cnf       search        3-SAT near the phase transition; conflicts grow with n
  parity    bookkeeping   q iff an even number of cycles chose 'a'
  coupled   entanglement  v2's interdependent core, the axis that already scaled
  decided   key variety   stratified stack; the only family that can answer
                          A/B on closed_world and wfs (all cyclic families give C)
  easy_pad  control       propagation-decidable, length-matched to the cnf tiers

Usage:  python leaderboard/make_hard_v3.py [--out PATH] [--variants N]
"""
import argparse
import json
import os
import sys
import zlib
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from nafbench import verbalize_generic as VG  # noqa
from nafbench.verbalize_v2 import gold_for  # noqa
from leaderboard.hard_instances_v3 import gen_certified, HARDNESS_KIND  # noqa

CONDS = ["none", "closed_world", "cred", "skept", "wfs"]
SPEC = ["closed_world", "cred", "skept", "wfs"]

# (family, tier-tag, size-param, n_variants-multiplier). Sizes chosen from the
# measured curves in hard_instances_v3.__main__: cnf conflicts run ~4/5/10 at
# n=8/14/22, parity/coupled stay at 0 by design, decided alternates T/F on the
# parity of the stack depth.
TIERS = [
    ("cnf",      "cnf_n8",       8,  1.5),
    ("cnf",      "cnf_n14",     14,  1.5),
    ("cnf",      "cnf_n22",     22,  1.5),
    ("parity",   "parity_n4",    4,  0.25),
    ("parity",   "parity_n6",    6,  0.25),
    ("parity",   "parity_n8",    8,  0.25),
    ("coupled",  "coupled_n3",   3,  0.25),
    ("coupled",  "coupled_n5",   5,  0.25),
    ("decided",  "decided_d1",   1,  0.6),
    ("decided",  "decided_d2",   2,  0.6),
    ("decided",  "decided_d3",   3,  0.6),
    ("decided",  "decided_d4",   4,  0.6),
    ("decided",  "decided_d5",   5,  0.6),
    ("decided",  "decided_d6",   6,  0.6),
    ("loopy",    "loopy_d1",     1,  0.6),
    ("loopy",    "loopy_d2",     2,  0.6),
    ("loopy",    "loopy_d3",     3,  0.6),
    ("loopy",    "loopy_d4",     4,  0.6),
    ("easy_pad", "control_n8",   8,  0.25),
    ("easy_pad", "control_n14", 14,  0.25),
    ("easy_pad", "control_n22", 22,  0.25),
]
# filler rules that pad a control to roughly the token length of its cnf twin
CONTROL_FILLER = {8: 9, 14: 16, 22: 25}

# `parity`, `coupled` and `easy_pad` can only ever certify to TFuloop: in a
# cyclic program where q is achievable but not forced, credulous is T and
# skeptical is F, and everything cyclic is undefined under WFS. That is also
# the single signature all of hard_v2 had. So those axes are kept deliberately
# thin and the cnf quota below is biased AWAY from TF -- otherwise the modal
# answer vector (C, A, B, C) matches a large share of the set and the
# label-prior baseline stays high. ~20% is the structural floor for this family
# mix; getting lower would mean dropping the fixed-signature axes entirely.
CNF_SIG_QUOTA = {"TT": 0.34, "FT": 0.28, "FF": 0.28, "TF": 0.10}


def signature(cert):
    la = cert["labels"]
    return "".join(la[k] if la[k] else "?" for k in ("cred", "skept", "wfs", "sldnf"))


def make_accept(family, quota):
    """Gate run before the expensive Prolog step.

    For `cnf` it also balances the (cred, skept) signature so the search family
    does not collapse onto one answer pattern the way v2 did; the other
    families have a fixed signature by construction, so they pass through.
    """
    def accept(prog, cert):
        conflicts = cert["metrics"]["clingo_conflicts"] or 0
        if family == "cnf":
            # the search family must actually need search
            if conflicts == 0:
                return False
            key = cert["labels"]["cred"] + cert["labels"]["skept"]
            if quota[key] <= 0:
                return False
            quota[key] -= 1
        elif family == "easy_pad":
            # a control is only a control if it is propagation-decidable; a low
            # clause ratio makes that likely but does not guarantee it at larger n
            if conflicts != 0:
                return False
        return True
    return accept


def build(n_variants, seed_offset=0, id_prefix="hv3"):
    items, programs = [], []
    for family, tier, size, mult in TIERS:
        want = max(2, int(round(n_variants * mult)))
        kw = {}
        if family == "easy_pad":
            kw["n_filler"] = CONTROL_FILLER.get(size, 10)
        # cnf: spread the four (cred, skept) outcomes as evenly as the instance
        # distribution allows; generous per-bucket cap, the sweep ends on `want`
        quota = Counter({k: max(1, int(round(want * share)))
                         for k, share in CNF_SIG_QUOTA.items()}) if family == "cnf" \
            else Counter()
        # crc32, not hash(): Python randomizes string hashes per process, so
        # hash(tier) would silently produce a different benchmark on every run
        got = gen_certified(family, size, want,
                            seed0=(zlib.crc32(tier.encode()) + seed_offset) % 100000,
                            max_seeds=6000, accept=make_accept(family, quota), **kw)
        print(f"  {tier:14} {family:9} want={want:3} got={len(got):3} "
              f"sigs={sorted(Counter(signature(c) for _, c in got).items())}", flush=True)
        for idx, (prog, cert) in enumerate(got):
            programs.append((tier, family, prog, cert))
            emit(items, prog, cert, family, tier, idx, id_prefix)
    return items, programs


def emit(items, prog, cert, family, tier, idx, id_prefix="hv3"):
    labels = cert["labels"]
    sig = signature(cert)
    for c in CONDS:
        items.append({
            "id": f"{id_prefix}-{tier}-i{idx}-{c}::{c}",
            "rec_id": f"{id_prefix}-{tier}-i{idx}",
            "axis": family,
            "difficulty": tier,
            "hardness_kind": HARDNESS_KIND[family],
            "n_stable_models": cert["n_stable_models"],
            # a real grouping key now, not the hardcoded constant v2 used
            "divergence_bin": f"sig_{sig}",
            "signature": sig,
            "cond": c,
            "gold": None if c == "none" else gold_for(labels, c),
            "labels": labels,
            "metrics": cert["metrics"],
            "meta": {k: v for k, v in prog.meta.items() if k != "cnf"},
            "prompt": VG.build_prompt(prog, c),
        })


def label_prior_baseline(items):
    """What a model scores by answering the best constant per condition, never
    reading a program. This is the number that was 100% on hard_v2."""
    best = {}
    for c in SPEC:
        golds = Counter(it["gold"] for it in items if it["cond"] == c)
        best[c] = golds.most_common(1)[0][0] if golds else None
    by_prog = defaultdict(dict)
    for it in items:
        if it["cond"] in SPEC:
            by_prog[it["rec_id"]][it["cond"]] = (it["gold"] == best[it["cond"]])
    joint = sum(1 for d in by_prog.values() if all(d.get(c) for c in SPEC))
    per_prompt = sum(1 for it in items if it["cond"] in SPEC and it["gold"] == best[it["cond"]])
    n_spec = sum(1 for it in items if it["cond"] in SPEC)
    return best, 100.0 * joint / max(1, len(by_prog)), 100.0 * per_prompt / max(1, n_spec)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "data/hard_v3.jsonl"))
    ap.add_argument("--variants", type=int, default=8,
                    help="base variants per tier (scaled by each tier's multiplier)")
    ap.add_argument("--seed-offset", type=int, default=0,
                    help="offset added to each tier's seed -> disjoint instances "
                         "(use a nonzero value to generate a fresh hidden test set)")
    ap.add_argument("--id-prefix", default="hv3",
                    help="id/rec_id prefix (use e.g. 'hv3hid' for the hidden set)")
    args = ap.parse_args()

    print("generating (clingo + WFS per candidate; SWI-Prolog only on accepted):",
          flush=True)
    items, programs = build(args.variants, seed_offset=args.seed_offset,
                            id_prefix=args.id_prefix)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        for it in items:
            f.write(json.dumps(it) + "\n")

    nprog = len({it["rec_id"] for it in items})
    print(f"\nhard v3: {len(items)} prompts over {nprog} programs -> {args.out}")

    print("\ngold distribution per condition (v2 was one constant per column):")
    for c in SPEC:
        print(f"  {c:13} {sorted(Counter(it['gold'] for it in items if it['cond']==c).items())}")

    sigs = Counter(it["signature"] for it in items if it["cond"] == "none")
    print(f"\ndistinct certified signatures: {len(sigs)}  (v2 had 1)")
    for s, k in sigs.most_common():
        print(f"  {s}  x{k}")

    best, joint, per_prompt = label_prior_baseline(items)
    print(f"\nlabel-prior baseline (answer {best} always, never read a program):")
    print(f"  JOINT {joint:.1f}%   per-prompt {per_prompt:.1f}%     [hard_v2: 100.0% / 100.0%]")


if __name__ == "__main__":
    main()
