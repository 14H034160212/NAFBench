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

    prog = Program(rules)
    prog.meta = dict(family="v2", divergence_bin=bin_name, depth=depth, width=width,
                     cycle_len=cycle_len, query="q",
                     expected=BIN_SIGNATURE[bin_name])
    return prog
