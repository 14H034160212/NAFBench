"""Generalization test (per A. Slusarz's memorization concern): does semantic-
following transfer across verbalizations?

Same certified programs, rendered in TWO different framings:
  A = narrative  (nafbench/verbalize_v2: reviewers / audit / escalation)
  B = abstract   (nafbench/verbalize_generic: 'proposition X is true if ...')

Framing B is deliberately unlike anything used for the few-shot exemplars or the
LoRA training data, so B measures transfer, not memorized phrasing. We also test
few-shot TRANSFER: a narrative exemplar (framing A) in front of an abstract
(framing B) question.
"""
import json
from nafbench.instances import build_by_effwidth
from nafbench import solvers as S
from nafbench import verbalize_v2 as VA
from nafbench import verbalize_generic as VB

BINS = ["even_one_sided", "odd", "even_both_sided"]
CYC = {"even_one_sided": 4, "odd": 3, "even_both_sided": 4}
CONDS = ["cred", "skept", "wfs"]

# narrative exemplars (framing A) used for the cross-framing few-shot transfer
EXEMPLAR = {
"cred": "Worked example. Rules: Guard 0 is on duty iff Guard 1 is not; Guard 1 is on "
        "duty iff Guard 0 is not; the gate is OPEN if Guard 0 is on duty. Question "
        "(credulous): Is the gate OPEN? Reasoning: two answer sets {Guard 0},{Guard 1}; "
        "in {Guard 0} the gate is OPEN, so at least one → yes. ANSWER: A",
"skept": "Worked example. Rules: Guard 0 is on duty iff Guard 1 is not; Guard 1 is on "
         "duty iff Guard 0 is not; the gate is OPEN if Guard 0 is on duty. Question "
         "(skeptical): Is the gate OPEN? Reasoning: in {Guard 1} the gate is not OPEN, so "
         "not every set → no. ANSWER: B",
"wfs": "Worked example. Rules: Guard 0 is on duty iff Guard 1 is not; Guard 1 is on duty "
       "iff Guard 0 is not; the gate is OPEN if Guard 0 is on duty. Question "
       "(well-founded): Is the gate OPEN? Reasoning: the guards are circular through "
       "negation with no grounding, so undefined. ANSWER: C",
}


def label_info(labels):
    vals = list(labels.values())
    distinct = sorted(set(vals))
    odd = [k for k, v in labels.items() if vals.count(v) == 1]
    return {"distinct_labels": distinct, "n_distinct": len(distinct),
            "odd_label": odd[0] if len(odd) == 1 else None}


items = []
for b in BINS:
    prog = build_by_effwidth(8, 8, b, cycle_len=CYC[b])
    cert = S.certify_full(prog, "q")
    li = label_info(cert["labels"])
    for c in CONDS:
        gold = VA.gold_for(cert["labels"], c)
        pA = VA.build_prompt(prog, c, theme=0)          # narrative
        pB = VB.build_prompt(prog, c)                   # abstract
        pBfs = EXEMPLAR[c] + "\n\nNow answer this one.\n\n" + pB
        for framing, prompt in [("A_narrative", pA), ("B_abstract", pB),
                                ("B_abstract_fewshotA", pBfs)]:
            items.append({
                "task_id": f"gen-{b}-{c}-{framing}::{c}", "rec_id": f"gen-{b}-{c}-{framing}",
                "cond": c, "divergence_bin": b, "framing": framing,
                "gold": gold, "labels": cert["labels"], **li,
                "program": prog.pretty(), "prompt": prompt,
            })

json.dump(items, open("data/generalization.json", "w"), indent=1)
print(f"generalization set: {len(items)} prompts "
      f"({len(BINS)} bins x {len(CONDS)} conds x 3 framings)")
print("label info example:", label_info(items[0]["labels"]))
