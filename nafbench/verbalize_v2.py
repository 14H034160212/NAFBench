"""Faithful verbalization for the v2 G(depth, width, bin) instances.

Renders the incident-escalation theme directly from prog.meta (mirroring
nafbench/instances.build_instance), so every rule maps to exactly one sentence
and the four certified labels remain valid gold. Adds the five semantics
instructions, including the credulous/skeptical stable-model split.
"""
from __future__ import annotations
from .program import Program

# ---- map a certified v2 label (T/F/u/loop) to the uniform A/B/C gold ----
_COND_GOLD = {
    "cred":  {"T": "A", "F": "B"},
    "skept": {"T": "A", "F": "B"},
    "wfs":   {"T": "A", "F": "B", "u": "C"},
    "closed_world": {"T": "A", "F": "B", "loop": "C"},
    "none":  {"T": "A", "F": "B", "u": "C", "loop": "C"},
}
# which certified dimension each condition is scored against
_COND_DIM = {"cred": "cred", "skept": "skept", "wfs": "wfs",
             "closed_world": "sldnf", "none": "sldnf"}


def gold_for(labels: dict, cond: str) -> str:
    """labels = certify_full(...)['labels'] (keys cred/skept/wfs/sldnf)."""
    return _COND_GOLD[cond][labels[_COND_DIM[cond]]]


SEMANTICS_INSTRUCTIONS = {
    "none": "Answer using ordinary commonsense reasoning about the rules below.",
    "closed_world": (
        "Use the CLOSED-WORLD ASSUMPTION with negation-as-failure: a statement is "
        "FALSE exactly when it cannot be derived. Treat the rules operationally, as "
        "a Prolog engine would; if the reasoning cannot terminate with a definite "
        "yes/no, answer 'Cannot be determined'."),
    "cred": (
        "Use STABLE-MODEL (answer-set) semantics with CREDULOUS (brave) reasoning. "
        "Consider every self-consistent scenario that is exactly justified by the "
        "rules (an 'answer set'). Answer 'Definitely yes' if the queried statement "
        "holds in AT LEAST ONE such scenario, and 'Definitely no' if it holds in "
        "NONE."),
    "skept": (
        "Use STABLE-MODEL (answer-set) semantics with SKEPTICAL (cautious) "
        "reasoning. Answer 'Definitely yes' only if the queried statement holds in "
        "EVERY self-consistent scenario (answer set), and 'Definitely no' if there "
        "is even one scenario where it fails. If there are NO self-consistent "
        "scenarios at all, the statement counts as holding in every scenario "
        "(answer 'Definitely yes')."),
    "wfs": (
        "Use WELL-FOUNDED semantics (three-valued: true / false / undefined). A "
        "statement is 'true' only if it is ultimately grounded in facts, 'false' if "
        "it can never be supported, and 'undefined' if its support depends "
        "circularly on assumptions about itself. Answer 'Definitely yes' for true, "
        "'Definitely no' for false, 'Cannot be determined' for undefined."),
}

# surface themes (replicates) — same logical structure, different vocabulary;
# this doubles as the verbalization-load axis.
THEMES_V2 = [
    dict(actor="reviewer", verb="signs off", notverb="does not sign off",
         warranted="the escalation is WARRANTED",
         audit="the audit is COMPLETE", clA="checklist A passes", clB="checklist B passes",
         item="item", form="form", stage="stage", query="the case is ESCALATED",
         qword="Is the case ESCALATED?"),
    dict(actor="sensor", verb="is active", notverb="is not active",
         warranted="the alarm condition HOLDS",
         audit="the self-test PASSES", clA="diagnostic A passes", clB="diagnostic B passes",
         item="signal", form="channel", stage="relay", query="the ALARM is raised",
         qword="Is the ALARM raised?"),
    dict(actor="auditor", verb="approves", notverb="does not approve",
         warranted="the override is JUSTIFIED",
         audit="the paperwork is IN ORDER", clA="file A is clear", clB="file B is clear",
         item="document", form="record", stage="tier", query="the override is GRANTED",
         qword="Is the override GRANTED?"),
]
_ORD = ["0", "1", "2", "3", "4", "5", "6"]


def _cap(s: str) -> str:
    """Capitalize only the first character (preserve intentional CAPS / 'A','B')."""
    return s[:1].upper() + s[1:]


def _premises(prog: Program, theme: int = 0) -> str:
    m = prog.meta
    b, k, d, w = m["divergence_bin"], m["cycle_len"], m["depth"], m["width"]
    th = THEMES_V2[theme % len(THEMES_V2)]
    A, V = th["actor"], th["verb"]
    L = []

    # --- divergence core ---
    if b == "control":
        L.append(f"{_cap(th['warranted'])} unless it has been blocked.")
    else:
        revs = [f"{A} {_ORD[i]}" for i in range(k)]
        for i in range(k):
            L.append(f"{_cap(revs[i])} {V} if and only if "
                     f"{revs[(i + 1) % k]} {th['notverb']}.")
        if b == "even_both_sided":
            for r in revs:
                L.append(f"{_cap(th['warranted'])} if {r} {V}.")
        else:
            L.append(f"{_cap(th['warranted'])} if {revs[0]} {V}.")

    # --- width block (shared subgoals) ---
    if w <= 0:
        L.append(f"{_cap(th['audit'])}.")
    else:
        L.append(f"{_cap(th['audit'])} if {th['clA']} and {th['clB']}.")
        items = " and ".join(f"{th['item']} {j + 1}" for j in range(w))
        L.append(f"{_cap(th['clA'])} if {items} are all filed.")
        L.append(f"{_cap(th['clB'])} if {items} are all filed.")
        L.append(f"A {th['item']} is filed if its {th['form']} is signed.")
        L.append(f"Every {th['form']} 1..{w} is signed.")

    # --- depth chain ---
    warr = th["warranted"]
    aud = th["audit"]
    if d <= 0:
        L.append(f"{_cap(th['query'])} if {warr} and {aud}.")
    else:
        L.append(f"{_cap(th['query'])} if {th['stage']} 0 is reached.")
        for j in range(d - 1):
            L.append(f"{_cap(th['stage'])} {j} is reached if {th['stage']} {j + 1} is reached.")
        L.append(f"{_cap(th['stage'])} {d - 1} is reached if {warr} and {aud}.")
    return " ".join(L)


def build_prompt(prog: Program, semantics: str, theme: int = 0) -> str:
    instr = SEMANTICS_INSTRUCTIONS[semantics]
    return (
        f"{instr}\n\n"
        f"Rules:\n{_premises(prog, theme)}\n\n"
        f"Question: {THEMES_V2[theme % len(THEMES_V2)]['qword']}\n\n"
        f"Choose exactly one:\n"
        f"  A. Definitely yes\n"
        f"  B. Definitely no\n"
        f"  C. Cannot be determined\n\n"
        f"Think step by step, then end with a line 'ANSWER: X' where X is A, B, or C.")
