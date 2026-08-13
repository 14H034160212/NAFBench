"""Trace-soundness scoring (v1) for NAF-Bench submissions.

Backward-compatible extension of the leaderboard: a submission line may carry an
optional `trace` (the model's reasoning). We reuse the paper's trace parser
(`analyze_traces`) to read what verdict the trace commits to for the QUERY atom
and, on odd cycles, whether it registers that the program has no stable model,
then check those against the certified labels we already store per instance.

This is v1: it audits the *query verdict* and the *odd-cycle / no-stable-model*
recognition — the two checks that need only fields we store (`labels`,
`meta.query`, `n_stable_models`). The fuller per-atom audit (the cycle-bridge
atom `cq`) needs the generator to emit per-atom certification and is a follow-up.

A trace is classified per prompt as:
  sound        -- states the query verdict, and it agrees with certification
  contradicted -- states a verdict that disagrees, or (odd-cycle skeptical) fails
                  to register that there is no stable model in a trace long enough
  unverifiable -- nothing checkable is stated (terse trace); not counted against
  no-derivation-- empty / no verdict at all
Only `sound` counts toward "reasoned soundly %".
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # repo root, for analyze_traces
import analyze_traces as at  # noqa: E402  (reuse normalise/verdict/entail_verdict/same/NO_MODELS)

# certified label token -> verdict token used by the trace parser
_LABEL = {"T": "true", "F": "false", "u": "undefined", "loop": "loop"}


def certified_q(labels, cond):
    """The query's certified verdict under `cond`, as a parser verdict token."""
    if cond == "closed_world":
        return _LABEL.get(labels.get("sldnf"), "loop")
    if cond == "wfs":
        return _LABEL.get(labels.get("wfs"), "undefined")
    return _LABEL.get(labels.get(cond), None)  # cred / skept -> true/false


def is_odd(item):
    """Odd cycle: no stable model, so skeptical is vacuously true."""
    return (item.get("n_stable_models") == 0
            and str(item.get("labels", {}).get("skept")).upper() == "T")


def soundness(trace, item):
    """Classify one trace against the stored certification for `item`.
    `item` needs: cond, labels, meta.query (query atom), n_stable_models."""
    if not trace or not str(trace).strip():
        return "no-derivation"
    cond = item["cond"]
    v_q = certified_q(item.get("labels", {}), cond)
    if v_q is None:
        return "unverifiable"
    n = at.normalise(trace)
    verbose = len(trace) > 250

    if cond in ("cred", "skept"):
        ent = at.entail_verdict(n, cond)          # 'true' / 'false' / None
        if cond == "skept" and is_odd(item) and verbose and not at.NO_MODELS.search(n):
            return "contradicted"                 # odd cycle admits no stable model, unregistered
        if ent is None:
            return "unverifiable" if verbose else "no-derivation"
        return "sound" if ent == v_q else "contradicted"

    # closed_world / wfs: one global assignment, audit the query atom's verdict
    said = at.verdict(n, item.get("meta", {}).get("query", "q"))[0]
    if said is None:
        return "unverifiable" if verbose else "no-derivation"
    return "sound" if at.same(said, v_q, cond) else "contradicted"


def trace_stats(submission, gold):
    """submission: id -> {prediction, trace}. gold: id -> item (must carry labels,
    cond, meta, n_stable_models). Returns None if no traces were submitted, else a
    dict with reasoned_soundly (% of traced+correct that are sound) and coverage."""
    from evaluate import normalize
    SPEC = ("closed_world", "cred", "skept", "wfs")
    traced = sound = correct_and_traced = correct_and_sound = 0
    for tid, item in gold.items():
        if item.get("cond") not in SPEC:
            continue
        sub = submission.get(tid)
        if not isinstance(sub, dict):
            continue
        tr = sub.get("trace")
        if not tr:
            continue
        traced += 1
        cls = soundness(tr, item)
        sound += cls == "sound"
        if item.get("gold") is not None and normalize(sub.get("prediction")) == str(item["gold"]).upper():
            correct_and_traced += 1
            correct_and_sound += cls == "sound"
    if traced == 0:
        return None

    def pct(a, b):
        return round(100.0 * a / b, 1) if b else 0.0
    return {
        "reasoned_soundly": pct(correct_and_sound, correct_and_traced),  # right for the right reason
        "sound_of_traced": pct(sound, traced),
        "trace_coverage": traced,
    }
