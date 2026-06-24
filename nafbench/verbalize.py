"""Faithful, theme-driven natural-language verbalization + semantics instructions.

The verbalization is ISOMORPHIC to the certified program (every rule/fact
appears exactly once, nothing added or hidden), so solver labels stay valid.
Themes vary only the surface vocabulary, realizing the verbalization-load axis.

Uniform 3-way answer scheme:
    A = "Definitely yes"        (query certainly holds)
    B = "Definitely no"         (query certainly does not hold)
    C = "Cannot be determined"  (undefined / scenario-dependent / no model)
"""
from __future__ import annotations

from typing import Dict
from .program import Program
from . import themes as TH

_LABEL_TO_GOLD = {"true": "A", "false": "B", "brave": "C", "undefined": "C", "loop": "C"}


def label_to_gold(label: str) -> str:
    return _LABEL_TO_GOLD[label]


SEMANTICS_INSTRUCTIONS = {
    "none": "Answer using ordinary commonsense reasoning about the rules below.",
    "closed_world": (
        "Use the CLOSED-WORLD ASSUMPTION with negation-as-failure: a statement "
        "is taken to be FALSE exactly when it cannot be derived from the rules. "
        "Treat the rules operationally, the way a Prolog engine would. If the "
        "reasoning cannot terminate with a definite yes/no, answer 'Cannot be "
        "determined'."),
    "stable": (
        "Use STABLE-MODEL (answer-set) semantics. Consider every self-consistent "
        "way of assigning truth values that is exactly justified by the rules "
        "(each such assignment is an 'answer set'). Answer 'Definitely yes' only "
        "if the queried statement holds in EVERY answer set; 'Definitely no' if "
        "it holds in NO answer set; and 'Cannot be determined' if it holds in "
        "some answer sets but not others, OR if there is no answer set at all."),
    "wfs": (
        "Use WELL-FOUNDED semantics, which is three-valued (true, false, or "
        "undefined). A statement is 'true' only if it is well-founded (ultimately "
        "grounded in facts), 'false' if it can never be supported, and 'undefined' "
        "if its support depends circularly on assumptions about itself. Answer "
        "'Definitely yes' for true, 'Definitely no' for false, and 'Cannot be "
        "determined' for undefined."),
}

SEMANTICS_TO_SOLVER = {"none": "sldnf", "closed_world": "sldnf",
                       "stable": "stable", "wfs": "wfs"}


def _theme(themes, name):
    for t in themes:
        if t["name"] == name:
            return t
    return themes[0]


def _chain_default(prog: Program):
    m = prog.meta
    th = _theme(TH.DEFAULT_THEMES, m["theme"])
    d = m["rule_depth"]
    cats = [th["cat"].format(k=i) for i in range(1, d + 1)]
    lines = []
    for i in range(d - 1, 0, -1):
        lines.append(f"Every item in {cats[i]} is automatically also in {cats[i-1]}.")
    lines.append(f"{th['subj'].capitalize()} is in {cats[-1]}.")
    lines.append(f"An item in {cats[0]} is {th['prop']} unless it has been "
                 f"{th['exc']}.")
    if m["with_exception"]:
        lines.append(f"{th['subj'].capitalize()} has been {th['exc']}.")
    return " ".join(lines), th["q"]


def _negation_stack(prog: Program):
    m = prog.meta
    th = _theme(TH.STACK_THEMES, m["theme"])
    nd = m["negation_depth"]
    units = [th["unit"].format(i=i) for i in range(nd + 1)]
    lines = [f"{units[i].capitalize()} {th['verb']} if and only if "
             f"{units[i+1]} does NOT {th['verb'].lower()}." for i in range(nd)]
    lines.append(f"{units[nd].capitalize()} definitely {th['verb'].lower()}.")
    return " ".join(lines), th["q"]


def _cycle_gadget(prog: Program):
    m = prog.meta
    th = _theme(TH.CYCLE_THEMES, m["theme"])
    k = m["cycle_len"]
    mode = m["mode"]
    actors = th["actors"][:k]
    verb = th["verb"]
    # the mutual-exclusion cycle
    lines = [f"{actors[i]} {verb} if and only if {actors[(i+1) % k]} does NOT."
             for i in range(k)]

    if mode == "reach":
        pfx = m["prefix_depth"]
        if pfx == 0:
            lines.append(f"{th['trigger'].capitalize()} if {actors[0]} {verb}.")
        else:
            steps = [f"step S{j}" for j in range(pfx)]
            prev = f"{actors[0]} {verb}"
            for s in steps:
                lines.append(f"{s.capitalize()} occurs if {prev.lower()}.")
                prev = f"{s} occurs"
            lines.append(f"{th['trigger'].capitalize()} if {prev.lower()}.")
        return " ".join(lines), th["q_trigger"]

    if mode == "disj":
        for a in actors:
            lines.append(f"{th['trigger'].capitalize()} if {a} {verb}.")
        return " ".join(lines), th["q_trigger"]

    if mode == "conj":
        conj = " and ".join(f"{a} {verb}" for a in actors)
        lines.append(f"{th['conj_event'].capitalize()} only if {conj}.")
        return " ".join(lines), th["q_conj"]

    raise ValueError(mode)


_RENDERERS = {
    "chain_default": _chain_default,
    "negation_stack": _negation_stack,
    "cycle_gadget": _cycle_gadget,
}


def verbalize(prog: Program) -> Dict[str, str]:
    premises, query = _RENDERERS[prog.meta["family"]](prog)
    return {"premises": premises, "query": query}


def build_prompt(prog: Program, semantics: str) -> str:
    v = verbalize(prog)
    instr = SEMANTICS_INSTRUCTIONS[semantics]
    return (
        f"{instr}\n\n"
        f"Rules:\n{v['premises']}\n\n"
        f"Question: {v['query']}\n\n"
        f"Choose exactly one:\n"
        f"  A. Definitely yes\n"
        f"  B. Definitely no\n"
        f"  C. Cannot be determined\n\n"
        f"Think step by step, then end your answer with a line of the form "
        f"'ANSWER: X' where X is A, B, or C.")
