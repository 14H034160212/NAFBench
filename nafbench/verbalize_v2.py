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

_REVIEWERS = ["reviewer 0", "reviewer 1", "reviewer 2", "reviewer 3",
              "reviewer 4", "reviewer 5", "reviewer 6"]


def _premises(prog: Program) -> str:
    m = prog.meta
    b, k, d, w = m["divergence_bin"], m["cycle_len"], m["depth"], m["width"]
    L = []

    # --- divergence core ---
    if b == "control":
        L.append("The escalation is WARRANTED unless it has been blocked.")
        # (no statement ever blocks it)
    else:
        revs = _REVIEWERS[:k]
        for i in range(k):
            L.append(f"{revs[i].capitalize()} signs off if and only if "
                     f"{revs[(i + 1) % k]} does NOT sign off.")
        if b == "even_both_sided":
            for r in revs:
                L.append(f"The escalation is WARRANTED if {r} signs off.")
        else:  # even_one_sided / odd: query enters through reviewer 0 only
            L.append(f"The escalation is WARRANTED if {revs[0]} signs off.")

    # --- width block (shared subgoals) ---
    if w <= 0:
        L.append("The audit is COMPLETE.")
    else:
        L.append("The audit is COMPLETE if checklist A passes and checklist B passes.")
        items = " and ".join(f"item {j + 1}" for j in range(w))
        L.append(f"Checklist A passes if {items} are all filed.")
        L.append(f"Checklist B passes if {items} are all filed.")
        L.append("Item j is filed if form j is signed (for each j).")
        L.append("Every form 1.." + str(w) + " is signed.")

    # --- depth chain ---
    if d <= 0:
        L.append("The case is ESCALATED if the escalation is warranted and the "
                 "audit is complete.")
    else:
        L.append("The case is ESCALATED if stage 0 is reached.")
        for j in range(d - 1):
            L.append(f"Stage {j} is reached if stage {j + 1} is reached.")
        L.append(f"Stage {d - 1} is reached if the escalation is warranted and the "
                 f"audit is complete.")
    return " ".join(L)


def build_prompt(prog: Program, semantics: str) -> str:
    instr = SEMANTICS_INSTRUCTIONS[semantics]
    return (
        f"{instr}\n\n"
        f"Rules:\n{_premises(prog)}\n\n"
        f"Question: Is the case ESCALATED?\n\n"
        f"Choose exactly one:\n"
        f"  A. Definitely yes\n"
        f"  B. Definitely no\n"
        f"  C. Cannot be determined\n\n"
        f"Think step by step, then end with a line 'ANSWER: X' where X is A, B, or C.")
