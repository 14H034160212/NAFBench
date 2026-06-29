"""Few-shot mitigation: does ONE worked example of the target semantics lift the
weak models? Exemplars use a different surface (guards/gate) than the targets
(reviewers/escalation), so there's no leakage."""
import json
from nafbench.instances import build_instance
from nafbench import solvers as S
from nafbench import verbalize_v2 as V2

EXEMPLAR = {
"cred":
"Worked example.\nRules: Guard 0 is on duty if and only if Guard 1 is not on duty. "
"Guard 1 is on duty if and only if Guard 0 is not on duty. The gate is OPEN if Guard 0 is on duty.\n"
"Question (credulous): Is the gate OPEN?\nReasoning: the two guards form an even cycle with two "
"answer sets, {Guard 0} and {Guard 1}. Credulous = holds in at least one. In {Guard 0}, Guard 0 is "
"on duty so the gate is OPEN. Hence yes.\nANSWER: A",
"skept":
"Worked example.\nRules: Guard 0 is on duty if and only if Guard 1 is not on duty. "
"Guard 1 is on duty if and only if Guard 0 is not on duty. The gate is OPEN if Guard 0 is on duty.\n"
"Question (skeptical): Is the gate OPEN?\nReasoning: two answer sets, {Guard 0} and {Guard 1}. "
"Skeptical = holds in every answer set. In {Guard 1}, Guard 0 is not on duty so the gate is not OPEN; "
"it fails in one set.\nANSWER: B",
"wfs":
"Worked example.\nRules: Guard 0 is on duty if and only if Guard 1 is not on duty. "
"Guard 1 is on duty if and only if Guard 0 is not on duty. The gate is OPEN if Guard 0 is on duty.\n"
"Question (well-founded): Is the gate OPEN?\nReasoning: the guards depend on each other only through "
"negation with no grounding in facts, so both are undefined in the well-founded model; the gate's "
"status is therefore undefined.\nANSWER: C",
}

BINS = ["even_one_sided", "odd", "even_both_sided"]
CYC = {"even_one_sided": 4, "odd": 3, "even_both_sided": 4}
CONDS = ["cred", "skept", "wfs"]

items = []
for b in BINS:
    prog = build_instance(8, 4, b, cycle_len=CYC[b])
    cert = S.certify_full(prog, "q")
    for c in CONDS:
        base = V2.build_prompt(prog, c, theme=0)
        gold = V2.gold_for(cert["labels"], c)
        for shot in ["zeroshot", "fewshot"]:
            prompt = base if shot == "zeroshot" else EXEMPLAR[c] + "\n\nNow answer this one.\n\n" + base
            items.append({"task_id": f"fs-{b}-{c}-{shot}::{c}", "rec_id": f"fs-{b}-{c}-{shot}",
                          "cond": c, "divergence_bin": b, "shot": shot,
                          "gold": gold, "prompt": prompt})

json.dump(items, open("data/fewshot.json", "w"), indent=1)
print(f"few-shot set: {len(items)} prompts ({len(BINS)} bins x {len(CONDS)} conds x zero/few)")
