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


# Revised prompts from a collaborator (2026-07): matched level of detail across the
# four semantics; each gives a self-contained operational definition so we test
# whether a model can FOLLOW the specified semantics, not whether it already
# knows it. Kept verbatim (straight quotes for codebase consistency).
SEMANTICS_INSTRUCTIONS = {
    "none": "Answer using ordinary commonsense reasoning about the rules below.",
    "closed_world": (
        "Use the CLOSED-WORLD ASSUMPTION with NEGATION-AS-FAILURE, interpreted "
        "operationally as in Prolog-style reasoning. A positive goal is 'true' if "
        "it can be derived by a terminating proof from the rules. A positive goal "
        "is 'false' if every attempted proof of it finitely fails. The "
        "default-negated goal not G is 'true' if the goal G finitely fails, and "
        "'false' if G succeeds. If evaluating the goal does not terminate, gets "
        "stuck because of negation (flounders), or otherwise cannot produce a "
        "definite success or finite failure, answer 'Cannot be determined.' Answer "
        "'Definitely yes' for true, 'Definitely no' for 'false', and 'Cannot be "
        "determined' when no definite operational result is obtained."),
    "cred": (
        "Use STABLE-MODEL, also called ANSWER-SET, semantics with CREDULOUS, also "
        "called BRAVE, reasoning. An answer set is a self-consistent set of atoms "
        "that is closed under the program rules and contains exactly the atoms "
        "justified by those rules under the assumptions made in that same set. "
        "Equivalently, after evaluating each default-negated condition not A "
        "relative to a candidate set, the candidate must be exactly the minimal set "
        "of atoms derivable from the remaining rules. For the queried statement: "
        "Answer 'Definitely yes' if the statement holds in AT LEAST ONE answer set. "
        "Answer 'Definitely no' if the statement holds in no answer sets. If the "
        "program has no answer sets, answer 'Definitely no.'"),
    "skept": (
        "Use STABLE-MODEL, also called ANSWER-SET, semantics with SKEPTICAL, also "
        "called CAUTIOUS, reasoning. Consider all answer sets of the program. Each "
        "answer set is a self-consistent scenario that is closed under the rules "
        "and contains exactly the atoms justified by those rules under its own "
        "assumptions about default negation. Equivalently, after evaluating each "
        "default-negated condition not A relative to a candidate set, the candidate "
        "must be exactly the minimal set of atoms derivable from the remaining "
        "rules. For the queried statement: Answer 'Definitely yes' only if the "
        "statement holds in EVERY answer set. Answer 'Definitely no' if there is at "
        "least one answer set in which the statement does not hold. If the program "
        "has no answer sets, then the statement vacuously holds in every answer "
        "set; answer 'Definitely yes.'"),
    "wfs": (
        "Use WELL-FOUNDED semantics, with three truth values: 'true', 'false', and "
        "'undefined'. A statement is 'true' if it has founded support: that is, it "
        "follows from rules whose positive conditions are 'true' and whose "
        "default-negated conditions are 'false', with the justification ultimately "
        "grounded rather than relying only on unsupported circular reasoning. A "
        "statement is 'false' if all possible rules that could derive it are "
        "defeated, inapplicable, or depend only on unfounded circular support. A "
        "statement is 'undefined' if it is neither founded true nor founded false, "
        "typically because its truth depends on an unresolved cycle through default "
        "negation or on other undefined statements. Answer 'Definitely yes' if the "
        "statement is 'true'. Answer 'Definitely no' if the statement is 'false'. "
        "Answer 'Cannot be determined' if the statement is 'undefined'. For a "
        "default-negated query not G, evaluate it using the well-founded truth "
        "value of G: not G is 'true' when G is 'false', 'false' when G is 'true', "
        "and 'undefined' when G is 'undefined'."),
}

# surface themes (replicates) — same logical structure, different vocabulary;
# this doubles as the verbalization-load axis.
THEMES_V2 = [
    dict(actor="reviewer", verb="signs off", notverb="does not sign off",
         warranted="the escalation is WARRANTED",
         audit="the audit is COMPLETE", clA="checklist 1 passes", clB="checklist 2 passes",
         item="item", form="form", stage="stage", query="the case is ESCALATED",
         qword="Is the case ESCALATED?"),
    dict(actor="sensor", verb="is active", notverb="is not active",
         warranted="the alarm condition HOLDS",
         audit="the self-test PASSES", clA="diagnostic 1 passes", clB="diagnostic 2 passes",
         item="signal", form="channel", stage="relay", query="the ALARM is raised",
         qword="Is the ALARM raised?"),
    dict(actor="auditor", verb="approves", notverb="does not approve",
         warranted="the override is JUSTIFIED",
         audit="the paperwork is IN ORDER", clA="file 1 is clear", clB="file 2 is clear",
         item="document", form="record", stage="tier", query="the override is GRANTED",
         qword="Is the override GRANTED?"),
]
_ORD = ["0", "1", "2", "3", "4", "5", "6"]


def _cap(s: str) -> str:
    """Capitalize only the first character (preserve intentional CAPS)."""
    return s[:1].upper() + s[1:]


def _premise_lines(prog: Program, theme: int = 0):
    """Return the rule sentences as a LIST (so callers can reorder them)."""
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
    return L


def _premises(prog: Program, theme: int = 0, order=None) -> str:
    """Rule sentences joined into a block. `order` (a permutation of indices over
    the rule lines) reorders them WITHOUT changing the logic -- the gold labels
    are invariant, so this isolates whether rule ORDER affects the model."""
    L = _premise_lines(prog, theme)
    if order is not None:
        assert sorted(order) == list(range(len(L))), \
            f"order must be a permutation of 0..{len(L) - 1}"
        L = [L[i] for i in order]
    return " ".join(L)


def n_rule_lines(prog: Program, theme: int = 0) -> int:
    """How many reorderable rule sentences this instance has."""
    return len(_premise_lines(prog, theme))


def _assemble(instr, rules, qword):
    return (
        f"{instr}\n\n"
        f"Rules:\n{rules}\n\n"
        f"Question: {qword}\n\n"
        f"Choose exactly one:\n"
        f"  A. Definitely yes\n"
        f"  B. Definitely no\n"
        f"  C. Cannot be determined\n\n"
        f"Think step by step, then end with a line 'ANSWER: X' where X is A, B, or C.")


def build_prompt(prog: Program, semantics: str, theme: int = 0,
                 pad_to_tokens: int = None, order=None) -> str:
    instr = SEMANTICS_INSTRUCTIONS[semantics]
    qword = THEMES_V2[theme % len(THEMES_V2)]["qword"]
    rules = _premises(prog, theme, order=order)
    if pad_to_tokens:
        # add inert, query-irrelevant filler until the WHOLE prompt reaches the
        # target token count -> length-match an easy instance to a hard one,
        # separating structure from sheer length (a collaborator's confound concern).
        from . import metrics as MET
        if MET.length_metrics("probe")["tokens"] is None:
            raise RuntimeError("pad_to_tokens requires tiktoken (pip install "
                               "tiktoken); token counting is unavailable.")
        extra, i = [], 0
        while MET.length_metrics(_assemble(instr, rules, qword))["tokens"] < pad_to_tokens:
            extra.append(f"For reference, archived note {i} concerns an unrelated "
                         f"matter and does not bear on the question.")
            rules = (_premises(prog, theme, order=order) +
                     "\nBackground (not part of the rules, irrelevant to the question): "
                     + " ".join(extra))
            i += 1
    return _assemble(instr, rules, qword)
