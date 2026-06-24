"""Core data structures for ground normal logic programs.

A *normal logic program* here is propositional (ground). Each rule has the form

    head :- b1, ..., bm, not c1, ..., not cn.

We keep things ground on purpose: the difficulty axes in the proposal
(negation depth, cycle parity, stratification) are all about the *propositional
dependency graph*, and grounding removes any ambiguity about how the three
solvers (clingo / well-founded / SWI-Prolog) interpret variables. A first-order
program with a finite Herbrand base would ground to exactly this representation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Set, Tuple, Dict


@dataclass(frozen=True)
class Rule:
    head: str
    pos: Tuple[str, ...] = ()      # positive body atoms
    neg: Tuple[str, ...] = ()      # atoms appearing under `not`

    def is_fact(self) -> bool:
        return not self.pos and not self.neg


@dataclass
class Program:
    rules: List[Rule] = field(default_factory=list)
    # metadata populated by the generator (difficulty axes etc.)
    meta: Dict = field(default_factory=dict)

    def atoms(self) -> Set[str]:
        out: Set[str] = set()
        for r in self.rules:
            out.add(r.head)
            out.update(r.pos)
            out.update(r.neg)
        return out

    # ---- serialization to each solver's concrete syntax ----------------

    def to_clingo(self) -> str:
        lines = []
        for r in self.rules:
            if r.is_fact():
                lines.append(f"{r.head}.")
                continue
            body = list(r.pos) + [f"not {a}" for a in r.neg]
            lines.append(f"{r.head} :- {', '.join(body)}.")
        return "\n".join(lines)

    def to_prolog(self) -> str:
        # SWI-Prolog: `not` is written `\+`. We also `:- dynamic` every atom so
        # that querying an atom that never appears as a head fails cleanly
        # (closed-world) instead of raising an existence error.
        lines = []
        for a in sorted(self.atoms()):
            lines.append(f":- dynamic {a}/0.")
        for r in self.rules:
            if r.is_fact():
                lines.append(f"{r.head}.")
                continue
            body = list(r.pos) + [f"\\+ {a}" for a in r.neg]
            lines.append(f"{r.head} :- {', '.join(body)}.")
        return "\n".join(lines)

    def pretty(self) -> str:
        lines = []
        for r in self.rules:
            if r.is_fact():
                lines.append(f"{r.head}.")
            else:
                body = list(r.pos) + [f"not {a}" for a in r.neg]
                lines.append(f"{r.head} :- {', '.join(body)}.")
        return "\n".join(lines)
