"""Validate the three semantics on textbook examples with KNOWN answers.

If these pass, the solver-certification layer is sound and the whole benchmark
rests on solid ground.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nafbench.program import Program, Rule
from nafbench import solvers as S


def show(name, prog, query, expect):
    res = S.certify(prog, query)
    ok = all(res["labels"][k] in expect.get(k, [res["labels"][k]]) for k in expect) \
        if isinstance(next(iter(expect.values())), list) else (res["labels"] == expect)
    # simpler: compare dict equality where expect gives exact labels
    ok = res["labels"] == expect
    flag = "PASS" if ok else "**FAIL**"
    print(f"[{flag}] {name}: query {query} -> {res['labels']} "
          f"(dist={res['semantics_distance']}, #stable={res['n_stable_models']})")
    return ok


def main():
    results = []

    # 1. Tweety: all semantics agree that tweety does NOT fly.
    p = Program([
        Rule("bird_tweety"),
        Rule("penguin_tweety"),
        Rule("abnormal_tweety", pos=("penguin_tweety",)),
        Rule("flies_tweety", pos=("bird_tweety",), neg=("abnormal_tweety",)),
    ])
    results.append(show("Tweety (penguin)", p, "flies_tweety",
                        {"stable": "false", "wfs": "false", "sldnf": "false"}))

    # 1b. Tweety without penguin fact: all agree it DOES fly.
    p = Program([
        Rule("bird_tweety"),
        Rule("abnormal_tweety", pos=("penguin_tweety",)),
        Rule("flies_tweety", pos=("bird_tweety",), neg=("abnormal_tweety",)),
    ])
    results.append(show("Tweety (no penguin)", p, "flies_tweety",
                        {"stable": "true", "wfs": "true", "sldnf": "true"}))

    # 2. Odd negative loop p :- not p.
    #    stable: none -> undefined ; WFS: undefined ; SLDNF: loop
    p = Program([Rule("p", neg=("p",))])
    results.append(show("Odd loop  p:-not p", p, "p",
                        {"stable": "undefined", "wfs": "undefined", "sldnf": "loop"}))

    # 3. Even negative loop a:-not b. b:-not a.
    #    stable: 2 models {a},{b} -> brave ; WFS: undefined ; SLDNF: loop
    p = Program([Rule("a", neg=("b",)), Rule("b", neg=("a",))])
    results.append(show("Even loop a:-not b;b:-not a", p, "a",
                        {"stable": "brave", "wfs": "undefined", "sldnf": "loop"}))

    # 4. Stratified default: p :- not q.  (q has no rule -> q false)
    #    all agree p true.
    p = Program([Rule("p", neg=("q",))])
    results.append(show("p:-not q (q absent)", p, "p",
                        {"stable": "true", "wfs": "true", "sldnf": "true"}))

    # 5. Constraint-like: a:-not b. b:-not a. c:-a. c:-b.
    #    c is true in both stable models -> stable true; WFS undef; SLDNF loop
    p = Program([Rule("a", neg=("b",)), Rule("b", neg=("a",)),
                 Rule("c", pos=("a",)), Rule("c", pos=("b",))])
    results.append(show("c via even loop", p, "c",
                        {"stable": "true", "wfs": "undefined", "sldnf": "loop"}))

    print(f"\n{sum(results)}/{len(results)} canonical cases passed.")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
