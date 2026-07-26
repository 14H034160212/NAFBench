"""Trace audit.

Per instance it rebuilds the exact program from its `variant_seed` and compute, with
nafbench.solvers, the certified per-atom verdict for

  cq  -- the atom that bridges the negation cycle into the positive chain, and
  q   -- the query,

then extract from the trace what the model *said* about each, plus whether it
registered the cycle at all, whether it recognised that an odd cycle admits no stable
model, and whether it enumerated more than one model where the semantics requires it.

The audit is run over correct and incorrect answers alike, so it separates
  - correct answer + sound derivation      (genuine)
  - correct answer + no/unsound derivation (right for the wrong reason)
  - wrong answer  + sound derivation       (scoring loss / self-override)
  - wrong answer  + unsound derivation     (and where it broke)

Usage:  ./.venv/bin/python analyze_traces.py [--cases] [--validate N]
"""
import argparse
import json
import re
from collections import Counter, defaultdict

from nafbench.answer import parse_answer_reasoning
from nafbench.instances import build_variant
from nafbench.solvers import stable_models, well_founded_model

SET = "data/production_set.json"
RUN = "data/production_answers/run1"
MODELS = ["claude-sonnet-5", "gpt-5.6-sol", "o4-mini",
          "qwen2.5-coder_32b", "deepseek-r1_32b", "llama3_8b"]
CONDS = ["closed_world", "cred", "skept", "wfs"]
CYC = {"control": 2, "even_one_sided": 4, "odd": 3, "even_both_sided": 4}
# certified verdict -> the answer letter the prompt asks for
LETTER = {"true": "A", "false": "B", "undefined": "C", "loop": "C"}

# ---------------------------------------------------------------- extraction

_LATEX = re.compile(r"\\[()\[\]]|\\text\{[^}]*\}|\\mathrm\{[^}]*\}|[`*$]|\\,|\\;|\\!")
_ARROW = re.compile(r"⇒|→|⟹|=>|->|\\Rightarrow|\\rightarrow|\\to\b|←|<-|:-|\\leftarrow")
_SPLIT = re.compile(r"[\n;]+|(?<=[.!])\s+")

# a clause that restates a rule, states a subgoal, or explores a hypothesis is not a
# verdict. "X is true if Y" is the verbalizer's own rule syntax, so `if` is decisive.
NOT_A_VERDICT = re.compile(
    r"\b(if|iff|suppose|assume|assuming|were|would|hypothes|guess|candidate|try|"
    r"attempt|imagine|need to prove|to prove|must show|in order to|requires that|"
    r"let us|let's|the rule|rule \d|whether|looking at|let me|i will|"
    r"need to (?:trace|determine|check|evaluate|see|establish)|"
    r"prov(?:ing|e)\b|deriving\b|establishing\b|showing\b|requires?\b|"
    r"first (?:tries|attempts)|reduces through|chain (?:from|for))\b|"
    r"\b(?:case|model|answer set|scenario|world|interpretation)\s+[A-Z0-9]\b", re.I)

# A verdict must be bound to the atom, not merely co-occur with it in the clause:
# "Since blocked is false, cq is true" states `false` of `blocked` and `true` of `cq`.
# So we read only the span from the atom up to the next atom mention.
VERDICT_PATS = [
    ("undefined", re.compile(
        r"^\W*(?:is|are|=|:|becomes?|comes out|remains?|stays?|be|were)?\s*"
        r"(?:now |also |therefore |thus |itself )*(?:left |assigned )?"
        r"(undefined|undetermined|indeterminate|neither true nor false|"
        r"cannot be determined|not determined)", re.I)),
    ("loop", re.compile(
        r"^\W*(?:is|are|=|:|becomes?|remains?|stays?|be)?\s*"
        r"(?:evaluation |resolution )?(?:does ?n[o']t terminate|non-?termination|"
        r"infinite (?:recursion|loop|regress)|loops? forever|flounders?|"
        r"diverges?|neither (?:definite )?success nor finite failure|"
        r"unresolvable|cannot be resolved|fails? to terminate|"
        r"fails? to (?:reach|produce|yield|give)(?: a| any)? definite|"
        r"neither finitely succeeds)", re.I)),
    ("false", re.compile(
        r"^\W*(?:is|are|=|:|becomes?|comes out|remains?|stays?|be|were)?\s*"
        r"(?:definitely |therefore |thus |also )*"
        r"(?:false\b|not derivable\b|not (?:be )?(?:derived|provable|proven|"
        r"supported|justified|established)\b|fails?\b|"
        r"does not hold\b|cannot be derived\b)", re.I)),
    ("true", re.compile(
        r"^\W*(?:is|are|=|:|becomes?|comes out|remains?|stays?|be|were)?\s*"
        r"(?:definitely |therefore |thus |also |indeed )*"
        r"(?:true\b|holds?\b|derivable\b|derived\b|succeeds?\b|"
        r"established\b|justified\b|supported\b)", re.I)),
]
# verdict stated BEFORE the atom: "deriving cq", "cq cannot be established"
PRE_PATS = [
    ("true", re.compile(r"\b(?:derives|derived|establishes|established|"
                        r"supports|supported|yields|gives|makes)\s*$", re.I)),
    ("false", re.compile(r"\b(?:cannot|can't|fail(?:s|ed)? to|never|does not)\s+"
                         r"(?:derive\w*|establish\w*|prove\w*)\s*$", re.I)),
]

# unanchored: any truth-value token anywhere in the window. Two distinct tokens mean
# a paired listing ("cq = true and undefined = undefined" reads off (t6,cq)), so the
# window cannot be attributed to one atom.
TOKENS = {
    "true": re.compile(r"\btrue\b|(?<!not )(?<!n't )\bholds?\b|\bderivable\b|"
                       r"\bsucceeds?\b", re.I),
    "false": re.compile(r"\bfalse\b|\bnot derivable\b|\bfails?\b|\bdoes not hold\b|"
                        r"\bnot hold\b|\bdefinitely no\b|\bnot true in every\b", re.I),
    "undefined": re.compile(r"\bundefined|\bundetermined|\bindeterminate|"
                            r"\bcannot be determined|neither true nor false", re.I),
    "loop": re.compile(r"does ?n[o']t terminate|non-?termination|"
                       r"infinite (recursion|loop)|\bflounders?|\bdiverges?|"
                       r"fails? to terminate|fails? to (?:reach|produce|yield|give)"
                       r"(?: a| any)? definite|neither finitely succeeds", re.I),
}

NO_MODELS = re.compile(
    r"\bno (stable model|stable models|answer set|answer sets)\b|"
    r"\b(zero|0) (stable models|answer sets)\b|"
    r"\bthere (?:is|are) no (?:such )?(?:stable model|answer set)", re.I)
MULTI_MODELS = re.compile(
    r"\b(two|2|both|multiple|several) (stable models|answer sets|models)\b|"
    r"\bmodel (a|b|1|2)\b|\banswer set (a|b|1|2)\b|"
    r"\b(first|second) (stable model|answer set|model)\b|"
    r"\bm\s?[12]\b|\b(solution|candidate|configuration) [ab12]\b|"
    r"\btwo (?:self-consistent |stable )*(?:configurations|candidates)\b|"
    r"\b(two|both) (stable )?(assignments|resolutions|branches|scenarios|solutions)\b|"
    r"\bin one answer set\b[^.]{0,60}\b(another|the other)\b|"
    r"\beither branch\b|\bregardless of which\b", re.I)
# models are often named by their atom set instead: "{x0,x2}: ... {x1,x3}: ..."
SET_NOTATION = re.compile(r"\{\s*x\s*_?\s*\d+(?:\s*,\s*x\s*_?\s*\d+)*\s*\}")
# under stable semantics the auditable claim is the ENTAILMENT verdict, not a
# model-relative atom value ("in Model B, q is false" is compatible with either gold).
QUANT = re.compile(
    r"at least one|in some|in every|in all|every answer set|all answer sets|"
    r"credulous|brave|skeptic|cautious|vacuous", re.I)
QUANT_NEG = re.compile(
    r"\bnot\b[^.]{0,40}\b(in every|in all|every answer set|all answer sets)\b|"
    r"\b(?:not|no longer)\b[^.]{0,20}\b(?:guaranteed|assured|ensured)\b|"
    r"\b(does not|doesn't|fails to) hold in (every|all)\b|"
    r"\bnot (?:true|derivable|entailed) in (?:every|all)\b|"
    r"\bno answer set\b[^.]{0,40}\b(contains|in which|where)\b|"
    r"\bthere are no answer sets\b|\bthe program is inconsistent\b|"
    r"\bthere (?:is|exists) an answer set (?:where|in which)[^.]{0,40}"
    r"(?:not|fails|absent|false)", re.I)
CYCLE_WORD = re.compile(
    r"\bcycl|\bloop\b|mutual|circular|self-referen|odd-length|even-length|"
    r"odd cycle|even cycle|depends on itself|around the cycle|interdependen|"
    r"infinite regress|never terminates|returns to|back to x", re.I)


def normalise(text):
    t = re.sub(r"<think>|</think>", "\n", text or "")
    t = _LATEX.sub(" ", t)
    # A rule written head-first with a left implication ("cq true <- x0", "t7 false :- b")
    # is a rule restatement, not a verdict: the arrow IS the verbalizer's "if". Rewriting
    # it to `if` hands it to the rule-restatement guard. Only left arrows immediately
    # preceded by a truth token are rewritten, so derivation steps that happen to use an
    # arrow ("t5 <- t6(true) and cq(undefined) -> t5 = undefined") are untouched.
    t = re.sub(r"\b(true|false|undefined)\s*(?:←|<-|:-|\\leftarrow)", r"\1 if ", t, flags=re.I)
    t = _ARROW.sub(" ; ", t)
    t = re.sub(r"[∧]", " and ", t)
    return re.sub(r"[ \t]+", " ", t)


def atom_re(atom):
    if re.fullmatch(r"[a-z]+\d+", atom):
        stem, num = re.match(r"([a-z]+)(\d+)", atom).groups()
        return re.compile(rf"(?<![A-Za-z0-9_]){stem}\s*_?\s*{num}(?![A-Za-z0-9_])")
    return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(atom)}(?![A-Za-z0-9_])")


# text that merely continues an atom list, so a trailing verdict still applies
# a window that denies a truth value must not be read as asserting it.
# `nor` continues a denial across a comma ("cq is undefined -- there's no rule
# guaranteeing cq false, nor is there founded support making cq true"), so it has to
# deny as strongly as `not` does.
NEGATED = re.compile(r"\bnot\b|\bneither\b|\bnor\b|n't\b|\bcannot\b|\bno rule\b|"
                     r"\bno founded\b|\bwithout\b|\bfails? to\b|\bdoes not\b", re.I)
# set/model notation: "{x0,x2}", "outside {x0,...,q}". An atom named INSIDE braces is
# being listed as a member (or an exclusion), never given a verdict.
BRACED = re.compile(r"\{[^{}]*\}")

LIST_GLUE = re.compile(r"[\s,;]*(?:and|the|then|also|finally|ultimately|subsequent|"
                       r"remaining|rest of|following|whole|entire|chain|so|thus|"
                       r"therefore|hence|down to|through|up to|,)*[\s,;]*", re.I)

ATOMISH = re.compile(r"(?<![A-Za-z0-9_])(?:x|t|s|p|g|f|q|cq|wide|btrue|etrue|blocked)"
                     r"\s*_?\s*\d*(?![A-Za-z0-9_])")


def verdict(norm_text, atom):
    """The last clause-bound verdict attributed to `atom` specifically.

    For each mention of the atom we read only the window up to the NEXT atom-like
    token, so a verdict about a neighbouring atom in the same clause is not stolen.
    """
    ar = atom_re(atom)
    found = (None, None)
    for clause in _SPLIT.split(norm_text):
        if NOT_A_VERDICT.search(clause) or "?" in clause:
            continue                     # a question is not a verdict either
        braces = [m.span() for m in BRACED.finditer(clause)]
        for m in ar.finditer(clause):
            if any(a <= m.start() < b for a, b in braces):
                continue                 # the atom is a set member, not a subject
            pos, end, walked = m.end(), len(clause), False
            while True:
                nxt = ATOMISH.search(clause, pos)
                if not nxt:
                    break
                gap = clause[pos:nxt.start()]
                if LIST_GLUE.fullmatch(gap):
                    pos, walked = nxt.end(), True   # inside a shared-verdict atom list
                    continue
                end = nxt.start()
                break
            window = clause[m.end():end][:150]
            head = clause[:m.start()].rsplit(",", 1)[-1].rsplit(";", 1)[-1]
            if NEGATED.search(head[-40:]):
                continue                     # the clause denies this atom's verdict
            present = {lab for lab, pat in TOKENS.items() if pat.search(window)}
            if len(present) > 1:
                continue                         # ambiguous paired listing -> skip
            hit = None
            for label, pat in VERDICT_PATS:
                if pat.search(window):
                    hit = label
                    break
            if (hit is None and walked and len(present) == 1
                    and not NEGATED.search(window)):
                # "making cq, t7, ... and ultimately q undefined": one verdict, shared
                # by the whole list, sitting at the end of the window
                hit = present.copy().pop()
            if hit is None:                      # try "deriving cq" / "cannot prove cq"
                before = clause[max(0, m.start() - 40):m.start()]
                for label, pat in PRE_PATS:
                    if pat.search(before):
                        hit = label
                        break
            if hit:
                found = (hit, clause.strip()[:200])
    return found


def entail_verdict(norm_text, cond):
    """Under cred/skept: the last clause that states an ENTAILMENT conclusion."""
    found = None
    for clause in _SPLIT.split(norm_text):
        if not QUANT.search(clause) or not atom_re("q").search(clause):
            continue
        if NOT_A_VERDICT.search(clause) or "?" in clause:
            continue
        if all(any(a <= m.start() < b for a, b in
                   [x.span() for x in BRACED.finditer(clause)])
               for m in atom_re("q").finditer(clause)):
            continue                     # q appears only inside set notation
        # strip "not <atom>" so a rule body does not read as a denial -- but keep the
        # words that ARE the denial of an entailment claim, or QUANT_NEG never sees them
        bare = re.sub(r"\bnot\s+(?:proposition\s+)?(?!true|false|derivable|"
                      r"undefined|hold|entailed|guaranteed|assured|ensured)"
                      r"[a-z]+\s*_?\s*\d*\b", " ", clause, flags=re.I)
        if re.search(r"\bvacuous", clause, re.I) or (
                cond == "skept" and NO_MODELS.search(clause)):
            # zero stable models: vacuously TRUE for the universal quantifier.
            # Checked first, because "there are no answer sets" reads as a negation.
            found = "true" if cond == "skept" else "false"
        elif QUANT_NEG.search(bare) or re.search(
                r"\bcannot (?:conclude|affirm|establish|assert)\b|"
                r"\bnot (?:skeptically|credulously)\b", clause, re.I):
            found = "false"
        elif TOKENS["false"].search(clause) and not TOKENS["true"].search(clause):
            found = "false"
        elif TOKENS["true"].search(clause) and not TOKENS["false"].search(clause):
            found = "true"
    return found


def audit_trace(text, inst):
    """Extract every feature the classification needs from one raw trace."""
    n = normalise(text)
    cyc_atoms = inst["cycle_atoms"]
    named = sum(1 for a in cyc_atoms if atom_re(a).search(n))
    if named >= 2 and re.search(r"x\s*_?\s*0\s*[-\u2013\u2014]+\s*x?\s*_?\s*\d",
                                n, re.I):
        named = len(cyc_atoms)            # "x0-x3" / "x0--x3" names the whole cycle
    f = {
        "chars": len(text or ""),
        "cycle_seen": named >= max(2, len(cyc_atoms) - 1) and bool(CYCLE_WORD.search(n)),
        "cycle_atoms_named": named,
        "no_models": bool(NO_MODELS.search(n)),
        "multi_models": bool(MULTI_MODELS.search(n)),
    }
    f["multi_models"] = f["multi_models"] or len(set(SET_NOTATION.findall(n))) >= 2
    f["cq_said"], f["cq_span"] = verdict(n, "cq")
    f["q_said"], f["q_span"] = verdict(n, "q")
    f["q_entail"] = {c: entail_verdict(n, c) for c in ("cred", "skept")}
    return f


# ---------------------------------------------------------------- ground truth

def certified(inst_e):
    """Per-atom certified verdicts for one program, under each condition."""
    b = inst_e["divergence_bin"]
    p = build_variant(inst_e["depth"], inst_e["width"], b, CYC[b], inst_e["variant_seed"])
    assert p.pretty() == inst_e["program"], inst_e["rec_id"]
    wf = well_founded_model(p)
    models = stable_models(p)
    cyc_atoms = sorted({r.head for r in p.rules if re.fullmatch(r"x\d+", r.head)})

    def sm(atom, quant):
        if not models:                      # zero stable models
            return "false" if quant == "cred" else "true"   # skept is vacuously true
        hit = [atom in M for M in models]
        return "true" if (any(hit) if quant == "cred" else all(hit)) else "false"

    out = {"cycle_atoms": cyc_atoms, "n_models": len(models), "bin": b,
           "cq": {}, "q": {}}
    for c in CONDS:
        for atom in ("cq", "q"):
            if c == "wfs":
                v = wf.get(atom, "false")
            elif c == "closed_world":
                # our shapes: control terminates true; every cycle-dependent atom loops
                v = "true" if b == "control" else "loop"
            else:
                v = sm(atom, "cred" if c == "cred" else "skept")
            out[atom][c] = v
    return out


# ---------------------------------------------------------------- classification

def same(said, certified, cond):
    """Verdict equality, allowing the terminological identity the prompt itself imposes.

    Under closed_world the answer options collapse SLDNF non-termination and "cannot be
    determined" onto the same choice C, and traces use the two interchangeably, so
    `loop` and `undefined` are one verdict there.
    """
    if said == certified:
        return True
    if cond == "closed_world" and {said, certified} <= {"loop", "undefined"}:
        return True
    return False


def classify(f, cert, cond, gold, answer):
    """Classify the DERIVATION (not the answer letter):

      sound        -- states the query verdict correctly, every stated checkpoint agrees
                      with certification, and the structural prerequisite is met
      unsound      -- a stated verdict contradicts certification, or a structural
                      prerequisite is demonstrably absent in a trace long enough to
                      have stated it
      unverifiable -- nothing contradicts certification but the query verdict is not
                      stated (typically a terse trace); NOT counted against a model
      no-derivation-- no truth value assigned to the query or the bridge atom at all

    Two audits, because the two semantics families expose different content:
      wfs / closed_world -- one global assignment, so per-atom verdicts are comparable
      cred / skept       -- atoms are model-relative, so per-atom verdicts are NOT
                            comparable to a global label; we audit the model structure
                            (an odd cycle admits none, an even cycle at least two) and
                            the quantifier applied to it
    """
    b = cert["bin"]
    v_cq, v_q = cert["cq"][cond], cert["q"][cond]
    said_cq, said_q = f["cq_said"], f["q_said"]
    verbose = f["chars"] > 250

    if said_q is None and said_cq is None:
        return "no-derivation", "no truth value assigned to the query or bridge atom"

    # ---------------- stable-model family: audit structure + quantifier
    if cond in ("cred", "skept"):
        ent = f["q_entail"][cond]
        if b == "odd":
            # everything turns on "this program has no stable model"
            if verbose and not f["no_models"]:
                return "unsound", "odd cycle not recognised as admitting no stable model"
        elif (b == "even_one_sided" and cond == "skept" and verbose
              and ent != v_q and not f["multi_models"]):
            # a universal quantifier needs more than the one model a witness gives
            return "unsound", "universal quantifier applied without enumerating models"
        # (credulous on an even bin needs only ONE witness model, so no gate here)
        if ent is not None and ent != v_q:
            return "unsound", f"q certified {v_q}, trace concludes {ent}"
        if ent == v_q:
            return "sound", ""
        return "unverifiable", "structure right, entailment verdict not stated"

    # ---------------- wfs / closed_world: one global assignment, audit per atom
    bridge_ok = said_cq is not None and same(said_cq, v_cq, cond)
    if b != "control" and verbose and not f["cycle_seen"] and not bridge_ok:
        return "unsound", "negation cycle never registered"
    if said_cq is not None and not same(said_cq, v_cq, cond):
        return "unsound", f"cq certified {v_cq}, trace says {said_cq}"
    if said_q is not None and not same(said_q, v_q, cond):
        if said_cq is not None and same(said_cq, v_cq, cond):
            return "unsound", f"cq correct ({v_cq}) but propagated to q as {said_q}"
        return "unsound", f"q certified {v_q}, trace says {said_q}"
    if said_q is not None:
        return "sound", ""
    return "unverifiable", "bridge atom correct, query verdict not stated"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", action="store_true", help="print the few case studies")
    ap.add_argument("--validate", type=int, default=0,
                    help="print N stratified traces with their extraction, for hand-check")
    args = ap.parse_args()

    ev = {e["task_id"]: e for e in json.load(open(SET))}
    progs = {}
    for e in ev.values():
        progs.setdefault(e["rec_id"], e)
    cert = {rid: certified(e) for rid, e in progs.items()}
    print(f"certified per-atom verdicts for {len(cert)} programs "
          f"(all reconstructed from variant_seed and checked against stored text)\n")

    rows = []
    for m in MODELS:
        raw = json.load(open(f"{RUN}/{m}.raw.json"))
        for t, e in ev.items():
            if e["cond"] not in CONDS:
                continue
            c = cert[e["rec_id"]]
            f = audit_trace(raw.get(t), c)
            ans = parse_answer_reasoning(raw.get(t) or "", query="q")
            snd, mech = classify(f, c, e["cond"], e["gold"], ans)
            rows.append(dict(model=m, tid=t, bin=e["divergence_bin"], cond=e["cond"],
                             gold=e["gold"], ans=ans, correct=(ans == e["gold"]),
                             sound=snd, mech=mech, **f))

    # ---------------------------------------------------------------- report
    W = 22
    KINDS = ["sound", "unverifiable", "unsound", "no-derivation"]

    def sub(m, pred=lambda x: True):
        return [x for x in rows if x["model"] == m and pred(x)]

    print("=" * 78)
    print("T1. Derivation audit x answer correctness (480 scored prompts per model)")
    print("    'contradicted' = a stated verdict disagrees with certification.")
    print("=" * 78)
    print(f"{'model':{W}s} {'ANSWER CORRECT':>30s} | {'ANSWER WRONG':>30s}")
    print(f"{'':{W}s} {'sound':>7s} {'unverif':>8s} {'contra':>7s} {'no-der':>6s} | "
          f"{'sound':>7s} {'unverif':>8s} {'contra':>7s} {'no-der':>6s}")
    for m in MODELS:
        c = Counter(x["sound"] for x in sub(m, lambda x: x["correct"]))
        w = Counter(x["sound"] for x in sub(m, lambda x: not x["correct"]))
        print(f"{m:{W}s} " + " ".join(f"{c[k]:>7d}" if i else f"{c[k]:>7d}"
                                     for i, k in enumerate(KINDS)) +
              " | " + " ".join(f"{w[k]:>7d}" for k in KINDS))

    print("\n" + "=" * 78)
    print("T2. Headline: among CORRECT answers, how often is a stated verdict wrong?")
    print("    (the 'right letter, broken derivation' rate; unverifiable excluded from")
    print("     the denominator, since a terse trace is not evidence either way)")
    print("=" * 78)
    print(f"{'model':{W}s} {'correct':>8s} {'auditable':>10s} {'sound':>7s} "
          f"{'contra':>7s} {'contra %':>9s}")
    for m in MODELS:
        r = sub(m, lambda x: x["correct"])
        aud = [x for x in r if x["sound"] in ("sound", "unsound")]
        bad = [x for x in aud if x["sound"] == "unsound"]
        if not aud:
            continue
        print(f"{m:{W}s} {len(r):8d} {len(aud):10d} {len(aud)-len(bad):7d} "
              f"{len(bad):7d} {100*len(bad)/len(aud):8.1f}%")
    # noise floor: the two models that answer 480/480 and whose derivations were
    # re-checked against clingo are sound by construction, so their contradiction
    # rate measures this audit's false-positive rate.
    ref = [x for x in rows if x["model"] in ("claude-sonnet-5", "gpt-5.6-sol")
           and x["correct"] and x["sound"] in ("sound", "unsound")]
    fp = sum(1 for x in ref if x["sound"] == "unsound")
    print(f"\n  extractor false-positive floor (Claude + GPT-5.6 Sol, both 480/480 "
          f"correct): {fp}/{len(ref)} = {100*fp/len(ref):.1f}%")
    print("  -> only rates well above that floor are signal.")

    print("\n" + "=" * 78)
    print("T3. Among INCORRECT answers, where the derivation breaks")
    print("=" * 78)
    for m in MODELS:
        r = sub(m, lambda x: not x["correct"])
        if not r:
            print(f"\n{m}: no incorrect answers")
            continue
        print(f"\n{m}  ({len(r)} incorrect)")
        for mech, n in Counter(x["mech"] or "(no contradiction found; letter wrong)"
                               for x in r).most_common(6):
            print(f"   {n:4d}  {mech}")

    print("\n" + "=" * 78)
    print("T4. Sound-derivation rate per condition (sound / auditable)")
    print("=" * 78)
    print(f"{'model':{W}s} " + " ".join(f"{c[:5]:>13s}" for c in CONDS))
    for m in MODELS:
        cells = []
        for c in CONDS:
            aud = sub(m, lambda x, c=c: x["cond"] == c and x["sound"] in ("sound", "unsound"))
            s_ = sum(1 for x in aud if x["sound"] == "sound")
            cells.append(f"{s_:3d}/{len(aud):3d} {100*s_/max(len(aud),1):3.0f}%")
        print(f"{m:{W}s} " + " ".join(f"{c:>13s}" for c in cells))
    # per-condition noise floor from the two provably-sound models, so the reader can
    # see where the audit is least reliable (SLDNF phrasing, model-relative prose).
    cells = []
    for c in CONDS:
        aud = [x for x in rows if x["model"] in ("claude-sonnet-5", "gpt-5.6-sol")
               and x["cond"] == c and x["sound"] in ("sound", "unsound")]
        bad = sum(1 for x in aud if x["sound"] == "unsound")
        cells.append(f"{100*bad/max(len(aud),1):3.0f}% fp")
    print(f"{'(audit noise floor)':{W}s} " + " ".join(f"{c:>13s}" for c in cells))

    print("\n" + "=" * 78)
    print("T5. Structural checkpoints on the divergent bins (360 prompts per model)")
    print("=" * 78)
    print(f"{'model':{W}s} {'cycle registered':>17s} {'odd: no stable model':>21s} "
          f"{'skept-even: >1 model':>21s}")
    for m in MODELS:
        r = sub(m, lambda x: x["bin"] != "control")
        cyc = sum(1 for x in r if x["cycle_seen"])
        odd = [x for x in r if x["bin"] == "odd" and x["cond"] in ("cred", "skept")]
        nm = sum(1 for x in odd if x["no_models"])
        esk = [x for x in r if x["bin"].startswith("even") and x["cond"] == "skept"]
        mm = sum(1 for x in esk if x["multi_models"])
        print(f"{m:{W}s} {cyc:8d}/{len(r):3d} {100*cyc/len(r):3.0f}% "
              f"{nm:12d}/{len(odd):3d} {100*nm/max(len(odd),1):3.0f}% "
              f"{mm:12d}/{len(esk):3d} {100*mm/max(len(esk),1):3.0f}%")

    print("\n" + "=" * 78)
    print("T7. The odd bin rewards the wrong procedure with the right letter")
    print("    Zero stable models => credulous false (B), skeptical vacuously true (A).")
    print("    A model that ignores the cycle and forward-chains also answers A, so")
    print("    odd+skept can be scored correct with no trace of the actual reason.")
    print("=" * 78)
    print(f"{'model':{W}s} {'odd+skept correct':>18s} {'of those, no-stable-model':>26s} "
          f"{'unearned':>9s}")
    for m in MODELS:
        r = [x for x in rows if x["model"] == m and x["bin"] == "odd"
             and x["cond"] == "skept" and x["correct"]]
        if not r:
            continue
        earned = sum(1 for x in r if x["no_models"])
        print(f"{m:{W}s} {len(r):18d} {earned:20d}      "
              f"{len(r)-earned:9d} ({100*(len(r)-earned)/len(r):3.0f}%)")
    print(f"\n  for contrast, odd+cred (gold B, which forward-chaining does NOT hit):")
    print(f"{'model':{W}s} {'odd+cred correct':>18s} {'of those, no-stable-model':>26s}")
    for m in MODELS:
        r = [x for x in rows if x["model"] == m and x["bin"] == "odd"
             and x["cond"] == "cred" and x["correct"]]
        if not r:
            continue
        print(f"{m:{W}s} {len(r):18d} {sum(1 for x in r if x['no_models']):20d}")

    print("\n" + "=" * 78)
    print("T6. Audit coverage (how much of each panel the audit can actually speak to)")
    print("=" * 78)
    print(f"{'model':{W}s} {'auditable':>10s} {'unverif':>8s} {'no-deriv':>9s} "
          f"{'median chars':>13s}")
    for m in MODELS:
        r = sub(m)
        d = Counter(x["sound"] for x in r)
        med = sorted(x["chars"] for x in r)[len(r) // 2]
        print(f"{m:{W}s} {100*(d['sound']+d['unsound'])/len(r):9.0f}% "
              f"{100*d['unverifiable']/len(r):7.0f}% {100*d['no-derivation']/len(r):8.0f}% "
              f"{med:13d}")

    json.dump(rows, open("data/trace_audit.json", "w"), indent=1)
    print("\nper-trace audit -> data/trace_audit.json")

    if args.validate:
        print("\n" + "=" * 78)
        print(f"HAND-CHECK SAMPLE ({args.validate} stratified traces)")
        print("=" * 78)
        import random
        random.seed(7)
        strata = defaultdict(list)
        for x in rows:
            strata[(x["model"], x["sound"])].append(x)
        picks = []
        for k in sorted(strata):
            picks += random.sample(strata[k], min(2, len(strata[k])))
        for x in random.sample(picks, min(args.validate, len(picks))):
            print(f"\n--- {x['tid']} | {x['model']} | gold={x['gold']} ans={x['ans']} "
                  f"| {x['sound']}: {x['mech']}")
            print(f"    cycle_seen={x['cycle_seen']} no_models={x['no_models']} "
                  f"multi_models={x['multi_models']}")
            print(f"    cq said {x['cq_said']!r} « {x['cq_span']} »")
            print(f"    q  said {x['q_said']!r} « {x['q_span']} »")

    if args.cases:
        print("\n" + "=" * 78)
        print("CASE STUDIES (three, one per mechanism the tables identify)")
        print("=" * 78)
        want = [
            ("qwen2.5-coder_32b", "prod-odd-i0-skept::skept",
             "T7: correct letter, wrong procedure -- forward-chains the odd cycle to "
             "'true' and lands on the letter the vacuous-truth convention requires"),
            ("o4-mini", "prod-even_one_sided-i7-wfs::wfs",
             "T3: cycle and bridge atom handled, then a two-valued collapse in "
             "propagation (undefined -> false)"),
            ("deepseek-r1_32b", "prod-even_one_sided-i20-wfs::wfs",
             "T1 wrong+sound: derivation reaches 'undefined' but the final letter is B"),
        ]
        for m, tid, why in want:
            raw = json.load(open(f"{RUN}/{m}.raw.json"))
            x = next(r for r in rows if r["model"] == m and r["tid"] == tid)
            print(f"\n### {m} | {tid}\n### {why}")
            print(f"### gold={x['gold']} answer={x['ans']} verdict={x['sound']}: {x['mech']}")
            print(f"### trace says cq={x['cq_said']} q={x['q_said']}")
            txt = raw.get(tid) or ""
            body = txt if len(txt) <= 900 else txt[:450] + "\n    […]\n" + txt[-450:]
            print("    " + body.replace("\n", "\n    "))


if __name__ == "__main__":
    main()
