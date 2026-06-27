"""Validate Agnieszka's v2 parametrization.

(1) For every (bin, depth, width), the certified four-tuple
    (credulous, skeptical, WFS, SLDNF) must equal the bin's predicted signature.
(2) Solver hardness (clingo conflicts, Prolog inferences) should grow with
    width and depth, confirming width/depth are real difficulty knobs.
"""
import sys
from nafbench.instances import build_instance, BIN_SIGNATURE
from nafbench import solvers as S

BINS = ["control", "even_one_sided", "odd", "even_both_sided"]


def main():
    print("=== (1) certified 4-tuple vs predicted bin signature ===")
    print(f"{'bin':16s} {'d':>2} {'w':>2}  cred skept wfs  sldnf   expected            ok")
    ok_all = True
    for b in BINS:
        for d in (0, 2, 4):
            for w in (0, 3, 6):
                prog = build_instance(d, w, b)
                r = S.certify_full(prog, "q")
                got = (r["labels"]["cred"], r["labels"]["skept"],
                       r["labels"]["wfs"], r["labels"]["sldnf"])
                ok = got == BIN_SIGNATURE[b]
                ok_all &= ok
                print(f"{b:16s} {d:>2} {w:>2}  {got[0]:>4} {got[1]:>5} {got[2]:>3} {got[3]:>6}"
                      f"   {str(BIN_SIGNATURE[b]):20s} {'PASS' if ok else '**FAIL**'}")
    print(f"\nAll signatures correct: {ok_all}")

    print("\n=== (2) solver hardness vs width (bin=control, depth=0) ===")
    print(f"{'width':>5}  clingo_conflicts  clingo_choices  prolog_inferences")
    for w in (0, 2, 4, 8, 16):
        prog = build_instance(0, w, "control")
        m = S.certify_full(prog, "q")["metrics"]
        print(f"{w:>5}  {str(m['clingo_conflicts']):>16}  {str(m['clingo_choices']):>14}"
              f"  {str(m['prolog_inferences']):>17}")

    print("\n=== (2b) solver hardness vs depth (bin=control, width=0) ===")
    for d in (0, 4, 8, 16):
        prog = build_instance(d, 0, "control")
        m = S.certify_full(prog, "q")["metrics"]
        print(f"depth {d:>3}  inferences={m['prolog_inferences']}  "
              f"conflicts={m['clingo_conflicts']}")

    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
