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

    # positive chain of length `depth` from (cq AND wide) up to the query q
    if depth <= 0:
        rules.append(Rule("q", pos=(cq, wide)))
    else:
        chain = [f"t{j}" for j in range(depth)]
        rules.append(Rule("q", pos=(chain[0],)))
        for j in range(depth - 1):
            rules.append(Rule(chain[j], pos=(chain[j + 1],)))
        rules.append(Rule(chain[-1], pos=(cq, wide)))   # deepest step needs core + width

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
