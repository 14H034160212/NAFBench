"""Self-verification mitigation set (verify-before-infer, no solver).

Takes the 12 WFS prompts and inserts an explicit verification scaffold, testing
whether structuring the reasoning ("name the semantics; assign each atom a
truth value under it; only then evaluate the query") improves accuracy without
delegating to a solver. This is the prompt-only analogue of the proposal's
Conflict-Aware-Fusion 'verification preamble'.
"""
import json

SCAFFOLD = (
    "Before answering, reason in three explicit, labelled steps:\n"
    "STEP 1 — State the exact semantics you must apply and its rule for "
    "'true' / 'false' / 'undefined'.\n"
    "STEP 2 — For EACH atom that appears, determine its truth value under THAT "
    "semantics. For any atom whose support runs through a cycle of negations, "
    "check whether it is grounded in facts; if it is not, it is 'undefined' "
    "(do NOT case-split into separate consistent worlds unless the semantics "
    "tells you to).\n"
    "STEP 3 — Evaluate the queried atom from the Step-2 values "
    "(undefined propagates: anything that depends on an undefined atom and is "
    "not otherwise grounded is itself undefined).\n"
    "Then give your final answer as a line 'ANSWER: X' where X is A, B, or C."
)

OLD_TAIL = ("Think step by step, then end your answer with a line of the form "
            "'ANSWER: X' where X is A, B, or C.")

items = []
for e in json.load(open("data/eval_set.json")):
    if not e["task_id"].endswith("::wfs"):
        continue
    prompt = e["prompt"].replace(OLD_TAIL, SCAFFOLD)
    # guard: the substitution must actually happen, else the self-verify prompt
    # is byte-identical to 'direct' and the condition reads as a null result.
    assert OLD_TAIL in e["prompt"], (
        f"OLD_TAIL not found in {e['task_id']}; verify-set scaffold not applied "
        f"(is this a v2-style set with a different tail?)")
    items.append({**{k: e[k] for k in ("task_id", "rec_id", "cond", "family",
                                       "divergent", "gold", "certified")},
                  "method": "self_verify", "prompt": prompt})

json.dump(items, open("data/verify_set.json", "w"), indent=1)
print(f"Self-verify set: {len(items)} WFS prompts")
print(items[0]["prompt"][:300], "...")
