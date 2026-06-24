"""The solver-certification layer.

Three independent negation semantics, all over the SAME ground program:

  1. Stable model semantics  -> clingo (Python API)        [answer-set]
  2. Well-founded semantics  -> alternating fixpoint (pure Python, 3-valued)
  3. SLDNF / Prolog NAF      -> SWI-Prolog subprocess      [operational]

Each returns a *truth value for a query atom* drawn from:
  "true", "false", "undefined", "brave"  (true in some but not all stable models)
plus the solver-specific outcome "loop" (SLDNF non-termination / timeout).

These are exactly the distinctions the proposal argues LLMs collapse.
"""
from __future__ import annotations

import subprocess
import tempfile
import os
from typing import Dict, List, Set, Tuple

from .program import Program, Rule

TRUE, FALSE, UNDEF, BRAVE, LOOP = "true", "false", "undefined", "brave", "loop"


# --------------------------------------------------------------------------
# 2. Well-founded semantics via the alternating fixpoint (Van Gelder et al.)
# --------------------------------------------------------------------------
def _least_model_definite(rules: List[Rule], facts_pos_only: bool = False) -> Set[str]:
    """Least model of a definite (negation-free) program by T_P iteration."""
    model: Set[str] = set()
    changed = True
    while changed:
        changed = False
        for r in rules:
            if r.head in model:
                continue
            if all(b in model for b in r.pos):
                model.add(r.head)
                changed = True
    return model


def _gl_reduct(prog: Program, S: Set[str]) -> List[Rule]:
    """Gelfond-Lifschitz reduct of `prog` w.r.t. atom set S.

    A rule is dropped if any of its `not c` literals has c in S; otherwise the
    negative body is erased, leaving a definite rule.
    """
    out: List[Rule] = []
    for r in prog.rules:
        if any(c in S for c in r.neg):
            continue
        out.append(Rule(head=r.head, pos=r.pos, neg=()))
    return out


def _gamma(prog: Program, S: Set[str]) -> Set[str]:
    """Anti-monotone operator: least model of the reduct w.r.t. S."""
    return _least_model_definite(_gl_reduct(prog, S))


def well_founded_model(prog: Program) -> Dict[str, str]:
    """Return {atom: TRUE/FALSE/UNDEF} for every atom in the Herbrand base.

    Underestimate W = lfp of Gamma^2 from below  -> the TRUE atoms.
    Overestimate     = Gamma(W)                  -> TRUE-or-UNDEF atoms.
    """
    atoms = prog.atoms()
    # least fixpoint of Gamma^2 starting from the empty set
    W: Set[str] = set()
    while True:
        nxt = _gamma(prog, _gamma(prog, W))
        if nxt == W:
            break
        W = nxt
    over = _gamma(prog, W)  # atoms that are true or undefined
    result: Dict[str, str] = {}
    for a in atoms:
        if a in W:
            result[a] = TRUE
        elif a in over:
            result[a] = UNDEF
        else:
            result[a] = FALSE
    return result


def wfs_query(prog: Program, query: str) -> str:
    return well_founded_model(prog).get(query, FALSE)


# --------------------------------------------------------------------------
# 1. Stable model semantics via clingo
# --------------------------------------------------------------------------
def stable_models(prog: Program) -> List[Set[str]]:
    import clingo

    ctl = clingo.Control()
    ctl.configuration.solve.models = 0  # enumerate ALL models
    ctl.add("base", [], prog.to_clingo())
    ctl.ground([("base", [])])
    models: List[Set[str]] = []
    with ctl.solve(yield_=True) as handle:
        for m in handle:
            models.append({str(s) for s in m.symbols(shown=True)})
    return models


def stable_query(prog: Program, query: str) -> Tuple[str, int]:
    """Return (label, n_models).

    label:  "true"  if query in every stable model (cautious entailment)
            "false" if query in no stable model
            "brave" if query in some but not all models (model-dependent)
            "undefined" if there is NO stable model at all (e.g. p :- not p)
    """
    models = stable_models(prog)
    n = len(models)
    if n == 0:
        return UNDEF, 0  # no stable model: query is not certifiable -> undefined
    contains = [query in m for m in models]
    if all(contains):
        return TRUE, n
    if not any(contains):
        return FALSE, n
    return BRAVE, n


# --------------------------------------------------------------------------
# 3. SLDNF / Prolog NAF via SWI-Prolog
# --------------------------------------------------------------------------
def prolog_query(prog: Program, query: str, timeout_s: float = 2.5) -> str:
    """Operational NAF as a real Prolog engine computes it.

    We use call_with_time_limit to detect non-termination (the classic SLDNF
    failure mode on negative cycles) and report it as LOOP.
    """
    program_text = prog.to_prolog()
    # library(time) / call_with_time_limit is unavailable in some SWI builds,
    # so we detect SLDNF non-termination with the OS-level subprocess timeout.
    goal = "( {q} -> R = true ; R = false ), write(R), nl, halt.".format(q=query)

    with tempfile.NamedTemporaryFile("w", suffix=".pl", delete=False) as f:
        f.write(program_text + "\n")
        path = f.name
    try:
        proc = subprocess.run(
            ["swipl", "-q", "-g", goal, "-t", "halt(1)", path],
            capture_output=True, text=True, timeout=timeout_s,
        )
        out = proc.stdout.strip().splitlines()
        if not out:
            return FALSE
        last = out[-1].strip()
        return {"true": TRUE, "false": FALSE}.get(last, FALSE)
    except subprocess.TimeoutExpired:
        return LOOP
    finally:
        os.unlink(path)


# --------------------------------------------------------------------------
# Combined certification
# --------------------------------------------------------------------------
def certify(prog: Program, query: str) -> Dict:
    stable_label, n_models = stable_query(prog, query)
    wfs_label = wfs_query(prog, query)
    sldnf_label = prolog_query(prog, query)
    labels = {
        "stable": stable_label,
        "wfs": wfs_label,
        "sldnf": sldnf_label,
    }
    # Semantics distance: how many DISTINCT verdicts the semantics produce.
    # We map SLDNF "loop" to "undefined" for distance purposes, since an
    # operational engine that fails to terminate is effectively "no answer",
    # which WFS would call undefined.
    norm = {
        "stable": stable_label,
        "wfs": wfs_label,
        "sldnf": UNDEF if sldnf_label == LOOP else sldnf_label,
    }
    distinct = set(norm.values())
    return {
        "labels": labels,
        "n_stable_models": n_models,
        "semantics_distance": len(distinct),
        "agree": len(distinct) == 1,
        "distinct_verdicts": sorted(distinct),
    }
