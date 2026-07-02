"""Multi-verbalization SFT data (fixes Exp 19's memorization).

Same solver-certified programs, each (program, condition) rendered in the TWO
NARRATIVE surfaces (v2 themes 0 and 1), with a framing-AGNOSTIC certified
chain-of-thought. Trained this way, the model should learn the semantics rather
than one phrasing.

Genuine held-out test (Exp 20), audit finding #4 -- the test framings are NOT
in training:
  * abstract 'generic' framing (verbalize_generic) -- never trained here;
  * narrative theme 2 (auditor) -- themes 0,1 trained, theme 2 held out;
and TRAIN sizes (depth 2,4 / ew 4,6) are disjoint from the TEST size (depth 8 /
ew 8). So transfer is measured across BOTH surface and size, not memorized.
"""
import json, os
from nafbench.instances import build_by_effwidth, BIN_SIGNATURE
from nafbench import solvers as S
from nafbench import verbalize_v2 as VA
from run_eval import parse_answer

SYSTEM = ("You are a careful reasoning test subject. Solve the problem using only "
          "your own reasoning. Reason step by step, then end with exactly one line "
          "'ANSWER: X' where X is A, B, or C.")
BINS = ["control", "even_one_sided", "odd", "even_both_sided"]
CYC = {"control": 2, "even_one_sided": 4, "odd": 3, "even_both_sided": 4}
CONDS = ["cred", "skept", "wfs", "closed_world"]
DEPTHS, WIDTHS = [2, 4], [4, 6]      # TRAIN sizes (held-out test uses depth 8 / ew 8)


def cot(bin_name, cond, gold):
    if bin_name == "control":
        return (f"There is no negative cycle; the query is grounded in the facts, "
                f"so it is definitely true.\nANSWER: {gold}")
    if cond == "wfs":
        return ("The atoms form a cycle through negation with no grounding in facts, "
                "so under well-founded semantics they are undefined; the query depends "
                "on them, hence undefined.\nANSWER: C")
    if cond == "closed_world":
        return ("Operationally (closed-world / SLDNF) the negative cycle does not "
                "terminate, so no definite yes/no is reached.\nANSWER: C")
    if cond == "cred":
        if bin_name == "odd":
            return ("An odd negation cycle has no stable model, so nothing holds in any "
                    "answer set (credulously false).\nANSWER: B")
        return ("An even negation cycle has two answer sets; the query holds in at least "
                "one of them, so credulously yes.\nANSWER: A")
    # skeptical
    if bin_name == "odd":
        return ("An odd negation cycle has no stable model, so the query holds vacuously "
                "in every answer set (skeptically true).\nANSWER: A")
    if bin_name == "even_both_sided":
        return ("Both answer sets of the even cycle make the query true, so it holds in "
                "every answer set (skeptically yes).\nANSWER: A")
    return ("The even cycle has two answer sets and the query fails in one of them, so "
            "not skeptically (no).\nANSWER: B")


# training framings: the TWO narrative surfaces only (v2 themes 0,1). The
# abstract 'generic' framing and narrative theme 2 are deliberately withheld so
# Exp 20 measures genuine cross-verbalization transfer (audit #4).
FRAMINGS = [("v2t0", lambda p, c: VA.build_prompt(p, c, theme=0)),
            ("v2t1", lambda p, c: VA.build_prompt(p, c, theme=1))]

os.makedirs("data/train", exist_ok=True)
rows = []
for b in BINS:
    for d in DEPTHS:
        for w in WIDTHS:
            prog = build_by_effwidth(d, w, b, cycle_len=CYC[b])
            cert = S.certify_full(prog, "q")
            for c in CONDS:
                gold = VA.gold_for(cert["labels"], c)
                target = cot(b, c, gold)
                assert parse_answer(target) == gold, (b, c, gold, target)
                for _, render in FRAMINGS:
                    rows.append({"messages": [
                        {"role": "system", "content": SYSTEM},
                        {"role": "user", "content": render(prog, c)},
                        {"role": "assistant", "content": target}]})

with open("data/train/sft_multi.jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
print(f"multi-verbalization SFT: {len(rows)} examples "
      f"({len(BINS)} bins x {len(DEPTHS)}x{len(WIDTHS)} sizes x {len(CONDS)} conds x {len(FRAMINGS)} framings)")
