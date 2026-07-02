"""Validate the semantics on textbook examples AND the v2 bin signatures.

Pytest-collectable (test_* functions) and also runnable as a script. If these
pass, the solver-certification layer the whole benchmark rests on is sound.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nafbench.program import Program, Rule
from nafbench import solvers as S
from nafbench.instances import build_by_effwidth, BIN_SIGNATURE

# --- v1 certify() canonical cases: (name, program, query, expected labels) ----
CANON = [
    ("Tweety (penguin)",
     Program([Rule("bird_tweety"), Rule("penguin_tweety"),
              Rule("abnormal_tweety", pos=("penguin_tweety",)),
              Rule("flies_tweety", pos=("bird_tweety",), neg=("abnormal_tweety",))]),
     "flies_tweety", {"stable": "false", "wfs": "false", "sldnf": "false"}),
    ("Tweety (no penguin)",
     Program([Rule("bird_tweety"),
              Rule("abnormal_tweety", pos=("penguin_tweety",)),
              Rule("flies_tweety", pos=("bird_tweety",), neg=("abnormal_tweety",))]),
     "flies_tweety", {"stable": "true", "wfs": "true", "sldnf": "true"}),
    ("Odd loop p:-not p",
     Program([Rule("p", neg=("p",))]),
     "p", {"stable": "undefined", "wfs": "undefined", "sldnf": "loop"}),
    ("Even loop a:-not b;b:-not a",
     Program([Rule("a", neg=("b",)), Rule("b", neg=("a",))]),
     "a", {"stable": "brave", "wfs": "undefined", "sldnf": "loop"}),
    ("p:-not q (q absent)",
     Program([Rule("p", neg=("q",))]),
     "p", {"stable": "true", "wfs": "true", "sldnf": "true"}),
    ("c via even loop",
     Program([Rule("a", neg=("b",)), Rule("b", neg=("a",)),
              Rule("c", pos=("a",)), Rule("c", pos=("b",))]),
     "c", {"stable": "true", "wfs": "undefined", "sldnf": "loop"}),
]

BINS_CYC = [("control", 2), ("even_one_sided", 4), ("odd", 3), ("even_both_sided", 4)]


def test_canonical_labels():
    for name, prog, query, expect in CANON:
        got = S.certify(prog, query)["labels"]
        assert got == expect, f"{name}: {got} != {expect}"


def test_bin_signatures():
    """certify_full's cred/skept/wfs/sldnf must equal each bin's declared
    signature (audit: the v2 layer had no asserted tests)."""
    for b, cyc in BINS_CYC:
        prog = build_by_effwidth(2, 4, b, cycle_len=cyc)
        cert = S.certify_full(prog, "q")
        got = tuple(cert["labels"][k] for k in ("cred", "skept", "wfs", "sldnf"))
        assert got == tuple(BIN_SIGNATURE[b]), f"{b}: {got} != {BIN_SIGNATURE[b]}"


def test_credulous_skeptical_zero_model():
    """Odd cycle has NO stable model: credulous=F (nothing holds), skeptical=T
    (vacuously holds in every model). n_stable_models must be 0."""
    prog = build_by_effwidth(2, 4, "odd", cycle_len=3)
    cert = S.certify_full(prog, "q")
    assert cert["n_stable_models"] == 0
    assert cert["labels"]["cred"] == "F"
    assert cert["labels"]["skept"] == "T"


def test_even_cycle_two_models():
    """Even one-sided cycle has 2 stable models: credulous=T, skeptical=F."""
    prog = build_by_effwidth(2, 4, "even_one_sided", cycle_len=4)
    cert = S.certify_full(prog, "q")
    assert cert["n_stable_models"] == 2
    assert cert["labels"]["cred"] == "T"
    assert cert["labels"]["skept"] == "F"


def main():
    tests = [test_canonical_labels, test_bin_signatures,
             test_credulous_skeptical_zero_model, test_even_cycle_two_models]
    ok = 0
    for t in tests:
        try:
            t(); ok += 1; print(f"[PASS] {t.__name__}")
        except AssertionError as e:
            print(f"[**FAIL**] {t.__name__}: {e}")
    print(f"\n{ok}/{len(tests)} test functions passed.")
    sys.exit(0 if ok == len(tests) else 1)


if __name__ == "__main__":
    main()
