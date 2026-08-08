"""Instance families for hard_v3: difficulty that survives contact with a solver.

The v2 combinatorial axis turned out to be decided by propagation rather than
search -- in `disj`, qcore <- x_ia holds for ANY i, so credulous is settled by a
single witness and skeptical by a single counterexample, and the 2**n stable
models are never visited. Measured: 16x the models buys 1.15-1.37x reasoning
tokens on o4-mini, and clingo solves the whole production set with 0-1
conflicts.

The families here are built so that no local argument settles the query:

  cnf      - a random 3-SAT instance near the phase transition (m/n ~ 4.26)
             embedded as choice cycles plus one violation constraint per clause.
             Stable models are the satisfying assignments, and the query asks
             about one variable, so:
                 credulous q  <=> CNF & q_lit is satisfiable
                 skeptical q  <=> CNF & ~q_lit is unsatisfiable
             Both need search. This family also supplies genuine gold variety:
             all four (cred, skept) combinations occur.

  parity   - q is true iff an even number of the n cycles chose 'a', via a
             stratified parity accumulator. No prefix of the choices decides
             the query, so the single-witness shortcut is gone. Effort is
             linear in n for a reasoner that spots the DP -- weaker than cnf,
             but a strict improvement on flat.

  coupled  - the one v2 axis that already scaled (2x models -> 1.56x effort);
             re-exported from hard_instances.py and selected on measured
             conflicts rather than on n.

  easy_pad - propagation-decidable control: a low-ratio (satisfiable, conflict-
             free) CNF padded with gold-neutral filler to match the token
             length of a hard tier. Without these, an effort increase on the
             hard tiers cannot be attributed to search rather than to reading
             a longer prompt.

Constraints are written with the standard odd-loop idiom
`bad :- <clause violated>, not bad`, because nafbench.program.Program carries
normal rules only (no empty heads). One rule per clause, not four: a clause is
violated exactly when every one of its literals is false, so the rule body is
the conjunction of the literal complements. This keeps prompts ~4x shorter than
the sat_j-per-literal encoding, which matters because prompt length is the
confound this file is trying to control for.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nafbench.program import Rule, Program
from nafbench.instances import canonical_key
from nafbench.solvers import (stable_cred_skept, wfs_query, prolog_query_metrics,
                              _wfs_to_v2)
from leaderboard.hard_instances import build_multi_variant  # coupled core, unchanged

PHASE_RATIO = 4.26   # random 3-SAT satisfiability threshold
EASY_RATIO = 1.8     # well below threshold: solved by propagation, conflicts ~0

# What kind of difficulty each family creates. Measured during implementation:
# clingo conflicts and LLM effort are NOT the same axis. `coupled` solves with 0
# conflicts yet produced the steepest o4-mini effort curve in hard_v2 (1.56x),
# while `cnf` is the only family where solver search actually grows. So the
# conflict filter is applied per family, not globally -- a blanket
# "reject conflicts == 0" would throw away the axis that empirically works best
# on models.
HARDNESS_KIND = {"cnf": "search",       # solver search grows; conflicts meaningful
                 "parity": "bookkeeping",   # must track state through n gadgets
                 "coupled": "entanglement",  # shared atoms; no local assignment decides
                 "decided": "definite",      # acyclic; the only family with A/B on wfs/cw
                 "loopy": "divergence",      # WFS decides, SLDNF loops: TTTloop / FFFloop
                 "easy_pad": "control"}      # propagation-decidable, length-matched


# --------------------------------------------------------------- primitives

def _choice_cycles(n):
    """n independent even loops: v_i / w_i. 2**n assignments before constraints."""
    rules = []
    for i in range(n):
        rules += [Rule(f"v{i}", neg=(f"w{i}",)), Rule(f"w{i}", neg=(f"v{i}",))]
    return rules


def _lit_atom(var, sign):
    return f"v{var}" if sign else f"w{var}"


def _clause_constraint(clause):
    """`bad :- <every literal false>, not bad` -- kills models violating the clause."""
    violated = tuple(_lit_atom(v, not s) for v, s in clause)
    return Rule("bad", pos=violated, neg=("bad",))


def _random_3sat(n, m, rng):
    return [[(v, rng.random() < 0.5) for v in rng.sample(range(n), 3)] for _ in range(m)]


def _pad(rules, qbody, rng, want_width=True, want_depth=True):
    """Gold-neutral structural noise, mirroring hard_instances.build_multi_variant:
    always-true width block, optional guard, and a pass-through depth chain."""
    w = rng.choice([0, 2, 3, 4]) if want_width else 0
    if w:
        subs = [f"s{j}" for j in range(w)]
        rules += [Rule(s) for s in subs]
        rules.append(Rule("wide", pos=tuple(subs)))
        qbody.append("wide")
    if rng.random() < 0.5:
        rules.append(Rule("etrue"))
        qbody.append("etrue")
    d = rng.choice([0, 2, 4, 6]) if want_depth else 0
    core = qbody[0]
    if d == 0:
        rules.append(Rule("q", pos=tuple(qbody)))
    else:
        rules.append(Rule("q", pos=tuple(["t0"] + qbody[1:])))
        for i in range(d - 1):
            rules.append(Rule(f"t{i}", pos=(f"t{i+1}",)))
        rules.append(Rule(f"t{d-1}", pos=(core,)))
    return w, d


# ------------------------------------------------------------------ builders

def build_cnf_variant(n, seed, ratio=PHASE_RATIO, n_filler=0):
    """3-SAT embedding. The query asks about variable 0, so cred/skept are two
    genuinely different search problems over the same instance."""
    rng = random.Random(seed)
    m = int(round(ratio * n))
    clauses = _random_3sat(n, m, rng)
    rules = _choice_cycles(n)
    rules += [_clause_constraint(c) for c in clauses]
    qvar, qsign = rng.randrange(n), rng.random() < 0.5
    qbody = [_lit_atom(qvar, qsign)]
    w, d = _pad(rules, qbody, rng)
    for j in range(n_filler):                       # length padding for controls
        rules += [Rule(f"f{j}"), Rule(f"g{j}", pos=(f"f{j}",))]
    rng.shuffle(rules)
    prog = Program(rules)
    prog.meta = dict(family="cnf", n_vars=n, n_clauses=m, ratio=ratio,
                     query="q", query_var=qvar, query_sign=qsign,
                     depth=d, width=w, n_filler=n_filler, variant_seed=seed,
                     cnf=[[[v, s] for v, s in c] for c in clauses])
    return prog


def build_parity_variant(n, seed):
    """q true iff an even number of the n cycles chose 'a'. Stratified parity
    accumulator: e_{i+1} flips on 'a', holds on 'b'. Every cycle is load-bearing."""
    rng = random.Random(seed)
    rules = _choice_cycles(n)
    rules.append(Rule("e0"))                                    # zero a's is even
    for i in range(n):
        rules.append(Rule(f"e{i+1}", pos=(f"e{i}", f"w{i}")))    # 'b': parity holds
        rules.append(Rule(f"e{i+1}", pos=(f"v{i}",), neg=(f"e{i}",)))  # 'a': flips
    qbody = [f"e{n}"]
    w, d = _pad(rules, qbody, rng)
    rng.shuffle(rules)
    prog = Program(rules)
    prog.meta = dict(family="parity", n_cycles=n, query="q",
                     depth=d, width=w, variant_seed=seed)
    return prog


def build_coupled_variant(n, seed):
    """v2's interdependent core -- the axis that already scaled -- unchanged."""
    prog = build_multi_variant("interdependent", n, seed)
    prog.meta = dict(prog.meta, family="coupled")
    return prog


def build_easy_pad_variant(n, seed, n_filler):
    """Propagation-decidable length-matched control: under-constrained CNF."""
    prog = build_cnf_variant(n, seed, ratio=EASY_RATIO, n_filler=n_filler)
    prog.meta = dict(prog.meta, family="easy_pad")
    return prog


def build_decided_variant(depth, seed):
    """Stratified negation stack: q has a DEFINITE answer under every semantics.

    Every cyclic family above leaves q undefined, so wfs and sldnf would be C on
    every program and those two conditions would keep the constant answer key
    that this whole set exists to remove. A stack `a0.  a1 :- not a0. ...`
    is acyclic, so all four semantics agree on T or F -- and which one it is
    depends on the parity of the stack depth, giving gold A and B on the
    conditions the cyclic families can only ever answer C.

    Not trivial to answer (the model still has to chase the negation chain),
    but genuinely easier than the search families -- that is the price of a
    non-degenerate key, and the `family` field lets analysis separate them.
    """
    rng = random.Random(seed)
    rules = [Rule("a0")]
    for i in range(1, depth + 1):
        rules.append(Rule(f"a{i}", neg=(f"a{i-1}",)))
    qbody = [f"a{depth}"]
    w, d = _pad(rules, qbody, rng)
    rng.shuffle(rules)
    prog = Program(rules)
    prog.meta = dict(family="decided", stack_depth=depth, query="q",
                     depth=d, width=w, variant_seed=seed)
    return prog


def build_loopy_variant(depth, seed):
    """Unfounded self-loop: the classic case where WFS and SLDNF disagree.

    `p_d :- p_d` is unfounded, so the well-founded model makes it FALSE, while
    SLDNF loops forever and returns no answer. So q gets a definite label under
    all three model-theoretic semantics and `loop` under SLDNF -- signatures
    TTTloop / FFFloop, which no other family here produces.

    Two reasons this family earns its place: it is the divergence the benchmark
    exists to measure, and it decouples closed_world from wfs (C and A/B on the
    same program), which every cyclic family above forces to move together.
    """
    rng = random.Random(seed)
    rules = []
    for i in range(depth):
        rules.append(Rule(f"p{i}", pos=(f"p{i+1}",)))
    rules.append(Rule(f"p{depth}", pos=(f"p{depth}",)))     # unfounded self-loop
    positive = seed % 2 == 0
    # q :- p0        -> q false in WFS  (FFFloop)
    # q :- not p0    -> q true  in WFS  (TTTloop)
    qbody = ["p0"]
    if positive:
        rules_q = Rule("q", pos=("p0",))
    else:
        rules_q = Rule("q", neg=("p0",))
    # pad around the query rule by hand (the shared _pad assumes a positive core)
    w = rng.choice([0, 2, 3])
    extra = []
    if w:
        subs = [f"s{j}" for j in range(w)]
        rules += [Rule(s) for s in subs]
        rules.append(Rule("wide", pos=tuple(subs)))
        extra.append("wide")
    if positive:
        rules.append(Rule("q", pos=tuple(["p0"] + extra)))
    else:
        rules.append(Rule("q", pos=tuple(extra), neg=("p0",)))
    rng.shuffle(rules)
    prog = Program(rules)
    prog.meta = dict(family="loopy", loop_depth=depth, query="q",
                     polarity="pos" if positive else "neg", width=w,
                     variant_seed=seed)
    return prog


BUILDERS = {"cnf": build_cnf_variant, "parity": build_parity_variant,
            "coupled": build_coupled_variant, "easy_pad": build_easy_pad_variant,
            "decided": build_decided_variant, "loopy": build_loopy_variant}


# ----------------------------------------------------------------- sampling

def gen_certified(family, n, n_want, seed0=0, max_seeds=4000, accept=None, **kw):
    """Yield up to n_want distinct certified programs.

    Returns (prog, cert) where cert has the same shape as
    nafbench.solvers.certify_full -- labels for all four semantics plus metrics
    (clingo_conflicts, clingo_choices, prolog_inferences, n_stable_models).

    Certification is two-stage on purpose. clingo + the WFS fixpoint are
    milliseconds, but the SLDNF label shells out to SWI-Prolog and every
    even-loop program burns the full timeout, so the Prolog step runs only on
    candidates that already passed `accept`. Certifying eagerly (a plain
    certify_full call per seed) makes a full sweep minutes slower for nothing.

    `accept(prog, partial_cert) -> bool` is the difficulty/quota gate; the
    caller owns it so tiering can be defined by measured search rather than by
    n. At gate time cert["labels"]["sldnf"] is not yet known.
    """
    build = BUILDERS[family]
    kept, seen, seed = [], set(), seed0
    while len(kept) < n_want and seed < seed0 + max_seeds:
        prog = build(n, seed, **kw)
        seed += 1
        key = canonical_key(prog)
        if key in seen:
            continue
        try:
            cred, skept, n_models, conflicts, choices = stable_cred_skept(prog, "q")
            wfs = _wfs_to_v2(wfs_query(prog, "q"))
        except Exception:  # noqa - a pathological program should not kill the sweep
            continue
        cert = {"labels": {"cred": cred, "skept": skept, "wfs": wfs, "sldnf": None},
                "n_stable_models": n_models,
                "metrics": {"clingo_conflicts": conflicts, "clingo_choices": choices,
                            "prolog_inferences": None, "n_stable_models": n_models}}
        if accept is not None and not accept(prog, cert):
            continue
        sldnf, inferences = prolog_query_metrics(prog, "q")   # the expensive half
        cert["labels"]["sldnf"] = sldnf
        cert["metrics"]["prolog_inferences"] = inferences
        cert["n_distinct_labels"] = len(set(cert["labels"].values()))
        seen.add(key)
        kept.append((prog, cert))
    return kept


if __name__ == "__main__":
    import statistics as st
    print(f"{'family':9} {'n':>3} {'rules':>6} {'conflicts':>10} {'models':>7}  signatures")
    for fam, ns in [("cnf", (8, 14, 22)), ("parity", (4, 6, 8)), ("coupled", (3, 5))]:
        for n in ns:
            got = gen_certified(fam, n, 6, seed0=n * 977)
            if not got:
                print(f"{fam:9} {n:>3}  (none)")
                continue
            cf = [c["metrics"]["clingo_conflicts"] for _, c in got]
            mo = [c["n_stable_models"] for _, c in got]
            sigs = sorted({"".join(c["labels"][k] for k in ("cred", "skept")) for _, c in got})
            print(f"{fam:9} {n:>3} {st.median(len(p.rules) for p, _ in got):>6.0f} "
                  f"{st.median(cf):>10.0f} {st.median(mo):>7.0f}  {sigs}")
