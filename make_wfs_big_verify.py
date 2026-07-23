"""Verify-before-answer mitigation on the LARGE diverse WFS set (>=30 programs).

Same verify scaffold as make_verify_set.py (the 12-item version), but applied to
the 44-program wfs_big set so Mitigation 3 is reported at reviewer-requested
sample size. Replaces the standard answer-instruction tail with the labelled
three-step verification scaffold; the logic/gold are untouched.
"""
import json

SCAFFOLD = (
    "Before answering, reason in three explicit, labelled steps:\n"
    "STEP 1 - State the exact semantics you must apply and its rule for "
    "'true' / 'false' / 'undefined'.\n"
    "STEP 2 - For EACH atom that appears, determine its truth value under THAT "
    "semantics. For any atom whose support runs through a cycle of negations, "
    "check whether it is grounded in facts; if it is not, it is 'undefined' "
    "(do NOT case-split into separate consistent worlds unless the semantics "
    "tells you to).\n"
    "STEP 3 - Evaluate the queried atom from the Step-2 values "
    "(undefined propagates: anything that depends on an undefined atom and is "
    "not otherwise grounded is itself undefined).\n"
    "Then give your final answer as a line 'ANSWER: X' where X is A, B, or C."
)

OLD_TAIL = ("Think step by step, then end your answer with a line of the form "
            "'ANSWER: X' where X is A, B, or C.")

items = []
for e in json.load(open("data/wfs_big.json")):
    assert OLD_TAIL in e["prompt"], f"OLD_TAIL not found in {e['task_id']}"
    items.append({**{k: e[k] for k in ("task_id", "rec_id", "cond", "family",
                                       "kind", "gold", "certified")},
                  "method": "self_verify",
                  "prompt": e["prompt"].replace(OLD_TAIL, SCAFFOLD)})

json.dump(items, open("data/wfs_big_verify.json", "w"), indent=1)
print(f"wfs_big self-verify set: {len(items)} WFS prompts")
