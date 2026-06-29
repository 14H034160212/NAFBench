"""Generic, faithful verbalization of an arbitrary ground normal program.

Renders rule-by-rule ("X is true if Y is true and Z is not true."), so it works
for any structure (e.g. the multi-cycle gadgets) and is transparent enough to
double-check labels against the program. Reuses the v2 semantics instructions
and gold mapping.
"""
from __future__ import annotations
from .program import Program
from .verbalize_v2 import SEMANTICS_INSTRUCTIONS, gold_for  # noqa: F401


def _nm(a: str) -> str:
    return f"proposition {a}"


def _render(prog: Program) -> str:
    lines = []
    for r in prog.rules:
        h = _nm(r.head)
        if not r.pos and not r.neg:
            lines.append(f"{h[0].upper()+h[1:]} is true.")
        else:
            conds = [f"{_nm(b)} is true" for b in r.pos] + \
                    [f"{_nm(c)} is not true" for c in r.neg]
            lines.append(f"{h[0].upper()+h[1:]} is true if " + " and ".join(conds) + ".")
    return " ".join(lines)


def build_prompt(prog: Program, semantics: str) -> str:
    q = prog.meta["query"]
    return (
        f"{SEMANTICS_INSTRUCTIONS[semantics]}\n\n"
        f"Rules:\n{_render(prog)}\n\n"
        f"Question: Is {_nm(q)} true?\n\n"
        f"Choose exactly one:\n"
        f"  A. Definitely yes\n"
        f"  B. Definitely no\n"
        f"  C. Cannot be determined\n\n"
        f"Think step by step, then end with a line 'ANSWER: X' where X is A, B, or C.")
