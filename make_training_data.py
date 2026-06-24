"""Generate solver-certified training data for the mitigation arm.

Produces, from a TRAIN pool of programs disjoint (by exact prompt string) from
the evaluation sets:

  * data/train/sft.jsonl  — chat examples whose assistant message is a faithful,
    semantics-correct chain-of-thought ending in the certified answer.
  * data/train/dpo.jsonl  — (prompt, chosen, rejected) preference pairs where
    `rejected` is the *documented reversion* failure (classical negation / case-
    split / open-world) and `chosen` is the certified reasoning. These target
    exactly the errors Experiments 2–5 surfaced — the data analogue of
    Conflict-Aware-Fusion's SFT + DPO steps.

Every target is validated: parse_answer(chosen) == certified gold, and
parse_answer(rejected) != gold. No model or GPU needed to BUILD the data; a
training recipe (trl) is documented in the README.
"""
import json
import os
from nafbench import generator as G
from nafbench import solvers as S
from nafbench import verbalize as V
from run_eval import parse_answer

SYSTEM = ("You are a careful reasoning test subject. Solve the problem using "
          "only your own reasoning. Reason step by step, then end with exactly "
          "one line 'ANSWER: X' where X is A, B, or C.")


def correct_cot(prog, cond, cert):
    m = prog.meta
    gold = V.label_to_gold(cert["labels"][V.SEMANTICS_TO_SOLVER[cond]])
    fam = m["family"]
    if fam == "cycle_gadget":
        parity = m["cycle"]
        mode = m["mode"]
        if cond == "wfs":
            body = ("Under well-founded semantics the cycle atoms depend only on "
                    "each other through negation with no factual grounding, so each "
                    "is UNDEFINED. ")
            if mode == "conj":
                body += ("The query is their conjunction; undefined ∧ undefined = "
                         "undefined (I must NOT case-split into separate worlds). ")
            elif mode == "disj":
                body += ("The query is their disjunction; undefined ∨ undefined = "
                         "undefined (I must NOT case-split). ")
            else:
                body += "The query is derived from an undefined atom, so it is undefined. "
            return body + "Therefore the value is undefined.\nANSWER: C"
        if cond == "stable":
            if parity == "odd":
                return ("Under stable-model semantics an odd negation cycle has NO "
                        "answer set, so the query is not cautiously entailed.\nANSWER: C")
            if mode == "disj":
                return ("Under stable-model semantics the even cycle yields two "
                        "alternating answer sets; in EACH, some cycle atom is true, so "
                        "the disjunctive query holds in every answer set.\nANSWER: A")
            if mode == "conj":
                return ("Under stable-model semantics the even cycle yields two "
                        "alternating answer sets; in each, only alternating atoms are "
                        "true, so the conjunctive query holds in NO answer set.\nANSWER: B")
            return ("Under stable-model semantics the query tracks one cycle atom, "
                    "true in one answer set and false in the other.\nANSWER: C")
        # none / closed_world -> operational SLDNF on a negative cycle loops
        return ("Operationally (closed-world / SLDNF) the negative cycle makes the "
                "computation non-terminating, so no definite yes/no is reached.\nANSWER: C")
    if fam == "chain_default":
        flagged = m["with_exception"]
        chain = ("The subject is in the base category, which (through the chain) "
                 "places it in C1. ")
        if flagged:
            return (chain + "It HAS been flagged, so the 'unless flagged' exception "
                    "fires and it is not approved.\nANSWER: B")
        return (chain + "'flagged' cannot be derived from any rule, so by "
                "negation-as-failure it is false; the exception does not fire and the "
                "default approval holds.\nANSWER: A")
    if fam == "negation_stack":
        return (f"Propagate from the deepest level (a fact) upward; each level flips "
                f"the one below via 'if and only if ... does not'. The parity of the "
                f"depth fixes the top level.\nANSWER: {gold}")
    return f"ANSWER: {gold}"


def reversion_cot(prog, cond, cert):
    """The documented WRONG answer (reversion). Returns (text, letter) or None."""
    m = prog.meta
    if m["family"] != "cycle_gadget":
        return None
    mode, parity = m["mode"], m["cycle"]
    if cond == "wfs":
        if mode == "disj":
            return ("Exactly one of each adjacent pair holds, so at least one cycle "
                    "atom is true and the disjunction is definitely true.\nANSWER: A", "A")
        if mode == "conj":
            return ("The cycle atoms are mutually exclusive, so they can never all be "
                    "true; the conjunction is impossible.\nANSWER: B", "B")
        return None
    if cond == "stable" and parity == "even":
        # reversion = collapse to WFS-style 'undefined'
        return ("The truth of the cycle atoms is not pinned down, so I cannot "
                "determine the query.\nANSWER: C", "C")
    return None


def main():
    os.makedirs("data/train", exist_ok=True)
    # test prompts to hold out (exact-string disjointness)
    test_prompts = set()
    for fn in ("data/eval_set.json", "data/wfs_big.json", "data/ladder_set.json"):
        try:
            for e in json.load(open(fn)):
                test_prompts.add(e["prompt"])
        except FileNotFoundError:
            pass

    pool = G.generate_dataset(seed=1)  # different theme draws from the seed-0 eval
    conds = ["none", "closed_world", "stable", "wfs"]
    sft, dpo = [], []
    n_skip_leak = 0
    for prog in pool:
        q = prog.meta["query"]
        cert = S.certify(prog, q)
        for cond in conds:
            prompt = V.build_prompt(prog, cond)
            if prompt in test_prompts:
                n_skip_leak += 1
                continue
            gold = V.label_to_gold(cert["labels"][V.SEMANTICS_TO_SOLVER[cond]])
            chosen = correct_cot(prog, cond, cert)
            assert parse_answer(chosen) == gold, (prog.meta, cond, gold, chosen)
            sft.append({"messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": chosen}]})
            rev = reversion_cot(prog, cond, cert)
            if rev and rev[1] != gold:
                dpo.append({"prompt": prompt, "chosen": chosen, "rejected": rev[0]})

    with open("data/train/sft.jsonl", "w") as f:
        for r in sft:
            f.write(json.dumps(r) + "\n")
    with open("data/train/dpo.jsonl", "w") as f:
        for r in dpo:
            f.write(json.dumps(r) + "\n")
    print(f"SFT examples: {len(sft)}  | DPO preference pairs: {len(dpo)}  "
          f"| held-out-for-leakage: {n_skip_leak}")
    from collections import Counter
    print("DPO target failure modes:",
          dict(Counter(json.loads(json.dumps(d))["rejected"].splitlines()[-1] for d in dpo)))


if __name__ == "__main__":
    main()
