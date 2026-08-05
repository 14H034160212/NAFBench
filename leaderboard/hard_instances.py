"""Structurally-varied multi-cycle instances for the hard tier.

`build_multi_independent(n)` / `build_interdependent(n)` in the core package are
single canonical programs, so a combinatorial-difficulty level (fixed n_cycles,
hence fixed 2**n stable models) had only one program. This adds gold-preserving
STRUCTURAL variety around the multi-cycle core -- a variable-depth query chain, a
width block of always-true shared subgoals, and an optional guard literal -- so
each level yields many distinct programs (distinct canonical keys) at the *same*
combinatorial difficulty. Every variant still certifies to (T, F, u, loop), i.e.
credulous/skeptical/WFS gold = A/B/C.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nafbench.program import Rule, Program
from nafbench.instances import canonical_key
from nafbench.solvers import stable_cred_skept, wfs_query

WMAP = {"true": "T", "false": "F", "undefined": "u"}


def _core(subtype, n):
    """Multi-cycle core producing atom `qcore` with signature (T, F, u, loop)."""
    rules, firsts = [], []
    if subtype in ("independent", "conjunctive"):
        for i in range(n):
            a, b = f"x{i}a", f"x{i}b"
            rules += [Rule(a, neg=(b,)), Rule(b, neg=(a,))]
            firsts.append(a)
        if subtype == "independent":          # q true if ANY cycle picks 'a' (skeptical-hard)
            for a in firsts:
                rules.append(Rule("qcore", pos=(a,)))
        else:                                  # conjunctive: q true only if ALL pick 'a' (credulous-hard)
            rules.append(Rule("qcore", pos=tuple(firsts)))
    else:  # interdependent (coupled chain of 2-cycles)
        for i in range(n):
            h, a = f"h{i}", f"a{i}"
            rules.append(Rule(h, neg=(a,)))
            rules.append(Rule(a, neg=(h,) if i == n - 1 else (h, f"h{i+1}")))
        rules.append(Rule("qcore", pos=("h0",)))
    return rules


def build_multi_variant(subtype, n_cycles, seed):
    """A structurally distinct, gold-preserving multi-cycle program. `subtype` is
    'independent' or 'interdependent'; n_cycles sets the combinatorial difficulty."""
    rng = random.Random(seed)
    rules = _core(subtype, n_cycles)

    # width: w always-true shared subgoals -> a `wide` aggregator (gold-neutral)
    w = rng.choice([0, 2, 3, 4])
    qbody = ["qcore"]
    if w:
        subs = [f"s{j}" for j in range(w)]
        rules += [Rule(s) for s in subs]          # facts (always true)
        rules.append(Rule("wide", pos=tuple(subs)))
        qbody.append("wide")
    # optional always-true guard literal
    if rng.random() < 0.5:
        rules.append(Rule("etrue"))
        qbody.append("etrue")

    # depth: put the query d steps above the core through an always-passing chain
    d = rng.choice([0, 2, 4, 6])
    if d == 0:
        rules.append(Rule("q", pos=tuple(qbody)))
    else:
        head_body = ["t0"] + qbody[1:]            # keep wide/etrue on the top rule
        rules.append(Rule("q", pos=tuple(head_body)))
        for i in range(d - 1):
            rules.append(Rule(f"t{i}", pos=(f"t{i+1}",)))
        rules.append(Rule(f"t{d-1}", pos=("qcore",)))

    rng.shuffle(rules)
    prog = Program(rules)
    prog.meta = dict(family="multicycle", subtype=subtype, n_cycles=n_cycles,
                     cycle_len=2, depth=d, width=w, query="q", variant_seed=seed)
    return prog


def gen_multi_variants(subtype, n_cycles, n_want, seed0=0):
    """Return up to n_want distinct, certified (T,F,u,loop) programs."""
    kept, seen, seed = [], set(), seed0
    while len(kept) < n_want and seed < seed0 + 100000:
        prog = build_multi_variant(subtype, n_cycles, seed); seed += 1
        cr, sk, nmods, conf, ch = stable_cred_skept(prog, "q")
        wl = WMAP[wfs_query(prog, "q")]
        if (cr, sk, wl, "loop") != ("T", "F", "u", "loop"):
            continue
        key = canonical_key(prog)
        if key in seen:
            continue
        seen.add(key)
        kept.append((prog, {"cred": cr, "skept": sk, "wfs": wl, "sldnf": "loop"}, nmods))
    return kept


if __name__ == "__main__":
    for sub in ("independent", "interdependent"):
        for n in (2, 3, 4):
            v = gen_multi_variants(sub, n, 12)
            nmods = v[0][2] if v else "?"
            print(f"{sub:14} n={n}: {len(v)} distinct certified variants "
                  f"(stable models = {nmods})")
