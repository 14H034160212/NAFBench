"""Controlled generator for ground normal logic programs (expanded + themed).

Difficulty axes realized:
  * rule_depth      - length of the positive derivation chain to the query
  * negation_depth  - number of `not` links stacked along that chain
  * cycle_len       - length of the negative cycle (0 = none)
  * cycle parity    - even cycles -> multiple stable models; odd -> none
  * mode            - how the query attaches to the cycle (reach/disj/conj)
  * stratified      - stratified vs non-stratified
  * theme           - surface-form domain (verbalization-load axis)

Families:
  chain_default  : stratified default-with-exception chain (Tweety-style)
  negation_stack : alternating `not` stack (parity flips the answer)
  cycle_gadget   : a length-k negative cycle, query attached by reach/disj/conj
                   (this single gadget subsumes the old cyclic / constrained
                    families and generalizes them to arbitrary cycle length)
"""
from __future__ import annotations

import random
from typing import List

from .program import Program, Rule
from . import themes as TH


def chain_default(depth: int, with_exception: bool, theme: dict) -> Program:
    rules: List[Rule] = []
    support = [f"p{i}" for i in range(1, depth + 1)]
    for i in range(len(support) - 1):
        rules.append(Rule(support[i], pos=(support[i + 1],)))
    rules.append(Rule(support[-1]))            # base fact
    rules.append(Rule("q", pos=(support[0],), neg=("e0",)))
    if with_exception:
        rules.append(Rule("e0"))
    prog = Program(rules)
    prog.meta = dict(family="chain_default", rule_depth=depth, negation_depth=1,
                     cycle_len=0, cycle="none", stratified=True, mode="default",
                     with_exception=with_exception, theme=theme["name"], query="q")
    return prog


def negation_stack(neg_depth: int, theme: dict) -> Program:
    rules: List[Rule] = []
    levels = [f"t{i}" for i in range(neg_depth + 1)]
    for i in range(neg_depth):
        rules.append(Rule(levels[i], neg=(levels[i + 1],)))
    rules.append(Rule(levels[-1]))             # deepest is a fact
    prog = Program(rules)
    prog.meta = dict(family="negation_stack", rule_depth=neg_depth,
                     negation_depth=neg_depth, cycle_len=0, cycle="none",
                     stratified=True, mode="stack", theme=theme["name"], query="t0")
    return prog


def cycle_gadget(k: int, mode: str, prefix_depth: int, theme: dict) -> Program:
    """Negative cycle a_0 -> a_1 -> ... -> a_{k-1} -> a_0 via `not`, plus a query.

    rules: a_i :- not a_{(i+1) mod k}      (k>=2)
    mode:
      reach : q :- a_0   (optionally through a positive chain of prefix_depth)
      disj  : q :- a_i   for every i
      conj  : q :- a_0, a_1, ..., a_{k-1}
    Even k -> alternating answer sets; odd k -> no stable model.
    """
    actors = [f"a{i}" for i in range(k)]
    rules = [Rule(actors[i], neg=(actors[(i + 1) % k],)) for i in range(k)]
    parity = "even" if k % 2 == 0 else "odd"

    if mode == "reach":
        chain = [f"c{j}" for j in range(prefix_depth)]
        nodes = ["q"] + chain
        for j in range(len(nodes) - 1):
            rules.append(Rule(nodes[j], pos=(nodes[j + 1],)))
        rules.append(Rule(nodes[-1], pos=(actors[0],)))
    elif mode == "disj":
        for a in actors:
            rules.append(Rule("q", pos=(a,)))
    elif mode == "conj":
        rules.append(Rule("q", pos=tuple(actors)))
    else:
        raise ValueError(mode)

    rd = (prefix_depth + 1) if mode == "reach" else 1
    prog = Program(rules)
    prog.meta = dict(family="cycle_gadget", cycle_len=k, cycle=parity, mode=mode,
                     rule_depth=rd, negation_depth=1, stratified=False,
                     prefix_depth=prefix_depth, theme=theme["name"], query="q",
                     n_actors=k)
    return prog


def generate_dataset(seed: int = 0) -> List[Program]:
    rng = random.Random(seed)
    progs: List[Program] = []

    # ---- stratified controls: default-with-exception, every theme & depth ----
    for theme in TH.DEFAULT_THEMES:
        for d in (1, 2, 3, 4, 5):
            for exc in (False, True):
                progs.append(chain_default(d, exc, theme))

    # ---- nested-negation stacks, every theme & depth ----
    for theme in TH.STACK_THEMES:
        for nd in (1, 2, 3, 4, 5, 6):
            progs.append(negation_stack(nd, theme))

    # ---- cycle gadgets: length x mode x prefix x theme ----
    for k in (2, 3, 4, 5):
        for mode in ("reach", "disj", "conj"):
            prefixes = (0, 1, 2) if mode == "reach" else (0,)
            for pfx in prefixes:
                # rotate through 2 themes per structural combo for surface variety
                for theme in rng.sample(TH.CYCLE_THEMES, 2):
                    progs.append(cycle_gadget(k, mode, pfx, theme))

    return progs
