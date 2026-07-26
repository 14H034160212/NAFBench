"""Which semantics does a model apply when the prompt names none of them?

The scored production conditions (`closed_world`, `cred`, `skept`, `wfs`) each name a
semantics in the preamble, so they measure whether a model can *follow* an instruction.
The fifth condition, `none`, names nothing: "Answer using ordinary commonsense reasoning
about the rules below." Its 120 items therefore carry no gold, and the interesting
question is not accuracy but *identification* -- which of the four readings, if any, the
model's untutored answers behave like.

We score every `none` answer against the letter each candidate reading requires, over the
four divergence bins that separate them:

                      cred  skept  wfs   closed_world   stable-consensus
  control              A      A     A         A               A
  even_one_sided       A      B     C         C               C
  odd                  B      A     C         C               C
  even_both_sided      A      A     C         C               A

`stable-consensus` is the fifth candidate: answer definitely when credulous and skeptical
entailment agree, "cannot be determined" when they diverge. It is not one of the four
textbook readings, and `even_both_sided` is the only bin that separates it from WFS.

Two baselines are printed alongside the models. A model that always answers A scores
90/120 against the credulous reading with no reasoning at all, so a raw agreement figure
identifies nothing on its own -- only a margin over both baselines does.

Every bin signature is recomputed here from the program text (clingo + the WFS fixpoint)
and asserted against the stored labels, so the table does not trust the dataset metadata.

Usage:  ./.venv/bin/python analyze_default_reading.py [--json data/default_reading.json]
"""
import argparse
import json
from collections import Counter

from analyze_traces import CYC, MODELS, RUN, SET, audit_trace, certified
from nafbench.answer import parse_answer_reasoning
from nafbench.instances import BIN_SIGNATURE, build_variant
from nafbench.solvers import stable_cred_skept, wfs_query

BINS = ["control", "even_one_sided", "odd", "even_both_sided"]
LETTER = {"T": "A", "F": "B", "u": "C", "loop": "C"}

# a candidate reading maps a bin signature (cred, skept, wfs, sldnf) to a letter
READINGS = {
    "cred":         lambda cr, sk, wf, sl: LETTER[cr],
    "skept":        lambda cr, sk, wf, sl: LETTER[sk],
    "wfs":          lambda cr, sk, wf, sl: LETTER[wf],
    "closed_world": lambda cr, sk, wf, sl: LETTER[sl],
    "consensus":    lambda cr, sk, wf, sl: LETTER[cr] if cr == sk else "C",
}
ORDER = ["cred", "skept", "wfs", "closed_world", "consensus"]


def signature(e):
    """Recompute (cred, skept, wfs, sldnf) for one item, checked against stored labels."""
    b = e["divergence_bin"]
    p = build_variant(e["depth"], e["width"], b, CYC[b], e["variant_seed"])
    assert p.pretty() == e["program"], e["rec_id"]
    cr, sk, _, _, _ = stable_cred_skept(p, "q")
    wf = {"true": "T", "false": "F", "undefined": "u"}[wfs_query(p, "q")]
    # SLDNF is analytic for these shapes: the control programs are acyclic and terminate
    # true, every divergent bin reaches the query through the negation cycle and loops.
    sl = "T" if b == "control" else "loop"
    sig = (cr, sk, wf, sl)
    assert sig == tuple(BIN_SIGNATURE[b]), (e["rec_id"], sig, BIN_SIGNATURE[b])
    assert sig == (e["labels"]["cred"], e["labels"]["skept"],
                   e["labels"]["wfs"], e["labels"]["sldnf"]), e["rec_id"]
    return sig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="data/default_reading.json")
    args = ap.parse_args()

    ev = [e for e in json.load(open(SET)) if e["cond"] == "none"]
    progs, sigs, cert = {}, {}, {}
    for e in ev:
        if e["rec_id"] not in progs:
            progs[e["rec_id"]] = e
            sigs[e["rec_id"]] = signature(e)
            cert[e["rec_id"]] = certified(e)
    print(f"{len(ev)} untutored (`none`) prompts over {len(progs)} programs; every bin "
          f"signature recomputed and matched against the stored labels\n")

    rows = []
    for m in MODELS:
        raw = json.load(open(f"{RUN}/{m}.raw.json"))
        for e in ev:
            sig = sigs[e["rec_id"]]
            txt = raw.get(e["task_id"]) or ""
            f = audit_trace(txt, cert[e["rec_id"]])
            rows.append(dict(
                model=m, tid=e["task_id"], bin=e["divergence_bin"],
                letter=parse_answer_reasoning(txt, query="q"), chars=len(txt),
                cycle_seen=f["cycle_seen"], no_models=f["no_models"],
                multi_models=f["multi_models"],
                required={k: READINGS[k](*sig) for k in ORDER}))

    def sub(m):
        return [r for r in rows if r["model"] == m]

    W = 20
    print("=" * 78)
    print("D1. Untutored answers per divergence bin (30 programs per bin, no gold)")
    print("    A = definitely yes, B = definitely no, C = cannot be determined")
    print("=" * 78)
    print(f"{'model':{W}s} " + " ".join(f"{b[:14]:>15s}" for b in BINS)
          + f" {'cycle seen':>11s}")
    for m in MODELS:
        cells = []
        for b in BINS:
            c = Counter(r["letter"] or "-" for r in sub(m) if r["bin"] == b)
            cells.append(" ".join(f"{k}{c[k]}" for k in ("A", "B", "C", "-") if c[k]))
        div = [r for r in sub(m) if r["bin"] != "control"]
        seen = sum(1 for r in div if r["cycle_seen"])
        print(f"{m:{W}s} " + " ".join(f"{c:>15s}" for c in cells)
              + f" {seen:4d}/{len(div):3d}")
    print("\n  required letter per reading:")
    for k in ORDER:
        need = {b: READINGS[k](*BIN_SIGNATURE[b]) for b in BINS}
        print(f"{k:>20s}  " + " ".join(f"{need[b]:>15s}" for b in BINS))

    print("\n" + "=" * 78)
    print("D2. Agreement of the untutored answers with each candidate reading (of 120)")
    print("=" * 78)
    print(f"{'model':{W}s} " + " ".join(f"{k[:12]:>13s}" for k in ORDER)
          + f" {'parsed':>7s}")

    best = {}
    for m in MODELS:
        r = sub(m)
        got = Counter()
        for x in r:
            for k in ORDER:
                if x["letter"] == x["required"][k]:
                    got[k] += 1
        parsed = sum(1 for x in r if x["letter"])
        top = max(ORDER, key=lambda k: got[k])
        best[m] = (top, got[top])
        cells = [f"{got[k]:3d} {100*got[k]/len(r):3.0f}%" +
                 ("*" if k == top else " ") for k in ORDER]
        print(f"{m:{W}s} " + " ".join(f"{c:>13s}" for c in cells)
              + f" {parsed:4d}/{len(r):3d}")
    for base in ("A", "B", "C"):
        got = Counter()
        for x in rows[:len(ev)]:
            for k in ORDER:
                if base == x["required"][k]:
                    got[k] += 1
        cells = [f"{got[k]:3d} {100*got[k]/len(ev):3.0f}% " for k in ORDER]
        print(f"{'(always ' + base + ')':{W}s} " + " ".join(f"{c:>13s}" for c in cells))
    print("\n  * = best fit.  A reading is only identified if the fit beats every")
    print("    constant-answer baseline; otherwise the agreement is answer bias.")

    print("\n" + "=" * 78)
    print("D3. Margin of the best-fitting reading over the best constant baseline")
    print("=" * 78)
    base_best = {}
    for base in ("A", "B", "C"):
        for k in ORDER:
            n = sum(1 for x in rows[:len(ev)] if base == x["required"][k])
            base_best[k] = max(base_best.get(k, 0), n)
    for m in MODELS:
        top, n = best[m]
        print(f"{m:{W}s} {top:>13s} {n:4d}/120   baseline {base_best[top]:3d}/120   "
              f"margin {n - base_best[top]:+4d}")

    # per-bin structural evidence for the C answers: on the divergent bins a "cannot be
    # determined" is only earned if the trace registers the cycle it turns on.
    print("\n" + "=" * 78)
    print("D4. Are the untutored 'cannot be determined' answers earned?")
    print("    (divergent bins only; 90 prompts per model)")
    print("=" * 78)
    print(f"{'model':{W}s} {'answered C':>11s} {'of those, cycle seen':>21s}")
    for m in MODELS:
        div = [r for r in sub(m) if r["bin"] != "control"]
        c = [r for r in div if r["letter"] == "C"]
        seen = sum(1 for r in c if r["cycle_seen"])
        pct = f"{100*seen/len(c):3.0f}%" if c else "  -"
        print(f"{m:{W}s} {len(c):8d}/{len(div):3d} {seen:15d}/{len(c):3d} {pct}")

    out = [{k: v for k, v in r.items()} for r in rows]
    json.dump(out, open(args.json, "w"), indent=1)
    print(f"\nper-item records -> {args.json}")


if __name__ == "__main__":
    main()
