"""G(depth, width, divergence_bin) — Agnieszka's complexity parametrization.

A v2 generator that decouples three knobs:

  * divergence_bin : which (cred, skept, WFS, SLDNF) signature the query carries,
    determined by the presence/parity of a negative cycle:
        control          (T, T, T, T)     no cycle, all four agree
        even_one_sided   (T, F, u, loop)  even cycle, q :- x        (all four differ)
        odd              (F, T, u, loop)  odd cycle (no stable model; skept vacuous T)
        even_both_sided  (T, T, u, loop)  even cycle, q :- x ; q :- y (three differ)
  * depth : length of the positive rule chain from the divergence core to the query
    (a linear "apply k rules in sequence" load).
  * width : a shared-subgoal block that two parents both depend on, so `width`
    atoms must be kept in memory simultaneously:
        wide :- pa, pb.   pa :- s1..sw.   pb :- s1..sw.   si :- fi.   fi.
    `wide` is certified TRUE, so it scales the instance WITHOUT changing the
    divergence signature; it only adds simultaneous-tracking load.

The depth chain and width block are definite and true, so the query's four
certified labels equal the bin signature for every (depth, width). cycle_len is
a parameter too (fixed per bin by default; even bins use 2, odd uses 3).
"""
from __future__ import annotations
from typing import List
from .program import Program, Rule

# (credulous, skeptical, WFS, SLDNF)
BIN_SIGNATURE = {
    "control":         ("T", "T", "T", "T"),
    "even_one_sided":  ("T", "F", "u", "loop"),
    "odd":             ("F", "T", "u", "loop"),
    "even_both_sided": ("T", "T", "u", "loop"),
}


def _neg_cycle(k: int) -> List[Rule]:
    """x_i :- not x_{(i+1) mod k}  for i in 0..k-1  (a length-k cycle through `not`)."""
    return [Rule(f"x{i}", neg=(f"x{(i + 1) % k}",)) for i in range(k)]


def _bin_core(bin_name: str, cycle_len: int):
    """Return (rules, core_query_atom) whose query carries the bin signature."""
    if bin_name == "control":
        # stratified default: `blocked` has no rule -> false -> cq true (all agree)
        return [Rule("cq", neg=("blocked",))], "cq"
    if bin_name == "even_one_sided":
        return _neg_cycle(cycle_len) + [Rule("cq", pos=("x0",))], "cq"
    if bin_name == "odd":
        return _neg_cycle(cycle_len) + [Rule("cq", pos=("x0",))], "cq"
    if bin_name == "even_both_sided":
        # q reachable from EVERY cycle atom -> true in every stable model
        return _neg_cycle(cycle_len) + [Rule("cq", pos=(f"x{i}",)) for i in range(cycle_len)], "cq"
    raise ValueError(bin_name)


def _width_block(width: int):
    """Return (rules, wide_atom). `wide` is true but forces tracking `width` shared subgoals."""
    if width <= 0:
        return [Rule("wide")], "wide"
    rules = [Rule("wide", pos=("pa", "pb"))]
    shared = tuple(f"s{i}" for i in range(width))
    rules.append(Rule("pa", pos=shared))
    rules.append(Rule("pb", pos=shared))            # pa and pb share all `width` subgoals
    for i in range(width):
        rules.append(Rule(f"s{i}", pos=(f"f{i}",)))
        rules.append(Rule(f"f{i}"))                 # independent facts
    return rules, "wide"


def build_instance(depth: int, width: int, bin_name: str, cycle_len: int = None) -> Program:
    if cycle_len is None:
        cycle_len = 3 if bin_name == "odd" else 2
    core_rules, cq = _bin_core(bin_name, cycle_len)
    wide_rules, wide = _width_block(width)
    rules: List[Rule] = list(core_rules) + list(wide_rules)

    # positive chain of length `depth` from (width AND cq) up to the query q.
    # `wide` is listed before `cq` so width is evaluated before the cycle
    # (A. Slusarz).
    if depth <= 0:
        rules.append(Rule("q", pos=(wide, cq)))
    else:
        chain = [f"t{j}" for j in range(depth)]
        rules.append(Rule("q", pos=(chain[0],)))
        for j in range(depth - 1):
            rules.append(Rule(chain[j], pos=(chain[j + 1],)))
        rules.append(Rule(chain[-1], pos=(wide, cq)))   # deepest step needs width + core

    # Effective width (per A. Slusarz): a negative cycle cannot be resolved, so
    # its length contributes to the atoms that must be held in working memory at
    # once. control has no cycle -> contributes 0.
    cyc_contrib = 0 if bin_name == "control" else cycle_len
    prog = Program(rules)
    prog.meta = dict(family="v2", divergence_bin=bin_name, depth=depth,
                     width=width,                       # shared-subgoal knob
                     cycle_len=cycle_len,
                     effective_width=width + cyc_contrib,  # subgoals + cycle length
                     query="q", expected=BIN_SIGNATURE[bin_name])
    return prog


def build_multi_independent(n_cycles: int) -> Program:
    """n independent even 2-cycles; q reachable from the first atom of each
    (q :- x_i0).  (A. Slusarz's 'independent' multi-cycle example, n=2.)
    Signature stays (T, F, u, loop) but n_stable_models = 2**n_cycles."""
    rules: List[Rule] = []
    firsts = []
    for i in range(n_cycles):
        a, b = f"x{i}a", f"x{i}b"
        rules += [Rule(a, neg=(b,)), Rule(b, neg=(a,))]
        firsts.append(a)
    for a in firsts:
        rules.append(Rule("q", pos=(a,)))
    prog = Program(rules)
    prog.meta = dict(family="multicycle", subtype="independent", n_cycles=n_cycles,
                     cycle_len=2, depth=0, width=0, query="q")
    return prog


def build_interdependent(n_cycles: int) -> Program:
    """n coupled 2-cycles in a chain (A. Slusarz's 'interdependent' example, n=2):
       h_i :- not a_i.
       a_i :- not h_i, not h_{i+1}      (last: a_n :- not h_n)
       q   :- h_1
    n=2 reproduces x:-not y / y:-not x,not z / z:-not w / w:-not z / q:-x."""
    rules: List[Rule] = []
    for i in range(n_cycles):
        h, a = f"h{i}", f"a{i}"
        rules.append(Rule(h, neg=(a,)))
        if i < n_cycles - 1:
            rules.append(Rule(a, neg=(h, f"h{i + 1}")))
        else:
            rules.append(Rule(a, neg=(h,)))
    rules.append(Rule("q", pos=("h0",)))
    prog = Program(rules)
    prog.meta = dict(family="multicycle", subtype="interdependent", n_cycles=n_cycles,
                     cycle_len=2, depth=0, width=0, query="q")
    return prog


def build_variant(depth: int, width: int, bin_name: str, cycle_len: int, seed: int) -> Program:
    """A structurally DISTINCT instance at the SAME (bin, depth, width, cycle_len),
    for "30 distinct programs per cell" (A. Słusarz's option (b)). All variation
    is gold-preserving -- every returned program still certifies to the bin
    signature -- so only incidental structure differs. Axes (seeded):

      (i)   `wide` and `cq` are required at (possibly different) chain steps t_i;
      (ii)  a variable number of aggregator predicates p_i over the SAME shared
            subgoals s_j, each s_j given >= 2 parents;
      (iii) each subgoal s_j is supported by a variable number of facts, with the
            TOTAL number of support facts held fixed;
      (iv)  cycle rules may carry an extra always-true literal (x_i :- not x_{i+1}, e);
      (v)   the final rule list is shuffled (order is semantics-irrelevant).

    `wide` is always listed before `cq` in a shared body (per A. Słusarz).
    """
    import random as _random
    rng = _random.Random(seed)
    rules: List[Rule] = []

    # --- divergence core (+ axis iv: optional true literal on cycle rules) ---
    if bin_name == "control":
        cq = "cq"
        rules.append(Rule("cq", neg=("blocked",)))
    else:
        k = cycle_len
        extra = rng.random() < 0.5           # axis (iv)
        if extra:
            rules.append(Rule("etrue"))       # an always-true guard atom
        for i in range(k):
            pos = ("etrue",) if extra else ()
            rules.append(Rule(f"x{i}", pos=pos, neg=(f"x{(i + 1) % k}",)))
        cq = "cq"
        if bin_name == "even_both_sided":
            for i in range(k):
                rules.append(Rule("cq", pos=(f"x{i}",)))
        else:
            rules.append(Rule("cq", pos=("x0",)))

    # --- width block: axis (ii) aggregators + axis (iii) support distribution ---
    subgoals = [f"s{j}" for j in range(width)] if width > 0 else []
    if not subgoals:
        rules.append(Rule("wide"))
    else:
        n_agg = rng.randint(2, max(2, min(4, width)))     # (ii) number of p_i
        # assign each subgoal to a random subset of aggregators, each s_j >= 2 parents
        parents = {j: set() for j in range(width)}
        for j in range(width):
            m = rng.randint(2, n_agg)
            for a in rng.sample(range(n_agg), m):
                parents[j].add(a)
        agg_members = {a: [f"s{j}" for j in range(width) if a in parents[j]]
                       for a in range(n_agg)}
        # ensure no empty aggregator (give it one subgoal if empty)
        for a in range(n_agg):
            if not agg_members[a]:
                agg_members[a].append(f"s{rng.randrange(width)}")
        aggs = [f"p{a}" for a in range(n_agg)]
        for a in range(n_agg):
            rules.append(Rule(aggs[a], pos=tuple(agg_members[a])))
        rules.append(Rule("wide", pos=tuple(aggs)))
        # (iii) distribute a fixed TOTAL of support facts among subgoals, each >= 1
        total = 2 * width                                  # fixed budget
        counts = [1] * width
        for _ in range(total - width):
            counts[rng.randrange(width)] += 1
        for j in range(width):
            supports = [f"g{j}_{c}" for c in range(counts[j])]
            for g in supports:
                rules.append(Rule(g))                      # a fact
            rules.append(Rule(f"s{j}", pos=tuple(supports)))

    # --- depth chain: axis (i) attach cq / wide at chosen steps ---
    wide = "wide"
    if depth <= 0:
        rules.append(Rule("q", pos=(wide, cq)))
    else:
        chain = [f"t{j}" for j in range(depth)]
        cq_at = rng.randrange(depth)
        wide_at = rng.randrange(depth)
        rules.append(Rule("btrue"))                        # grounding base fact
        rules.append(Rule("q", pos=(chain[0],)))
        for j in range(depth):
            body = []
            if j < depth - 1:
                body.append(chain[j + 1])
            else:
                body.append("btrue")                        # deepest step grounds out
            if j == wide_at:
                body.append(wide)
            if j == cq_at:
                body.append(cq)
            # keep `wide` before `cq` if both present
            rules.append(Rule(chain[j], pos=tuple(body)))

    # --- axis (v): shuffle rule order (semantics-irrelevant) ---
    rng.shuffle(rules)

    cyc_contrib = 0 if bin_name == "control" else cycle_len
    prog = Program(rules)
    prog.meta = dict(family="v2var", divergence_bin=bin_name, depth=depth,
                     width=width, cycle_len=cycle_len,
                     effective_width=width + cyc_contrib,
                     query="q", expected=BIN_SIGNATURE[bin_name], variant_seed=seed)
    return prog


def canonical_key(prog: Program) -> str:
    """Isomorphism-insensitive key: rename atoms to a canonical order-independent
    scheme and return a sorted-rule signature, so structurally-identical programs
    (incl. mere reorderings / atom renamings) collapse to the same key."""
    # canonical atom names by (is-fact, out-degree, sorted neighbour roles) is
    # hard in general; we use a pragmatic key: multiset of rules with atoms
    # replaced by structural roles derived from name prefixes (x/s/p/g/t/cq/wide/
    # q/etrue/btrue/blocked), which is stable under our generator's renamings and
    # under reordering (rules are sorted).
    def role(a):
        for pre in ("blocked", "etrue", "btrue", "wide", "cq", "q",
                    "x", "s", "p", "g", "t"):
            if a == pre or a.startswith(pre):
                return pre
        return a
    sig = []
    for r in prog.rules:
        pos = tuple(sorted(role(b) for b in r.pos))
        neg = tuple(sorted(role(c) for c in r.neg))
        sig.append((role(r.head), pos, neg))
    return repr(sorted(sig))


def build_by_effwidth(depth: int, eff_width: int, bin_name: str, cycle_len: int = None):
    """Build an instance at a TARGET effective width (= shared subgoals + cycle len).

    The minimum effective width is the cycle length (0 for control), since the
    cycle itself already occupies that many working-memory slots.
    """
    if cycle_len is None:
        cycle_len = 3 if bin_name == "odd" else 2
    cyc_contrib = 0 if bin_name == "control" else cycle_len
    subgoals = eff_width - cyc_contrib
    if subgoals < 0:
        raise ValueError(f"eff_width {eff_width} < min {cyc_contrib} for {bin_name} "
                         f"(cycle_len={cycle_len})")
    return build_instance(depth, subgoals, bin_name, cycle_len)
