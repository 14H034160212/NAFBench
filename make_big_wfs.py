"""A larger, all-WFS evaluation set for tighter confidence intervals.

Divergent probes: even cycles k in {2,4,6} x {disjunction, conjunction} x 4
themes (WFS gold = undefined / C). Controls: default-with-exception and
negation-stack at several depths/themes (WFS gold = true/false). All under the
WFS condition, so 'always-C' is bounded by the divergent fraction.
"""
import json
from nafbench import generator as G
from nafbench import solvers as S
from nafbench import verbalize as V
from nafbench import themes as TH

items = []


def add(prog, tag, kind):
    q = prog.meta["query"]
    cert = S.certify(prog, q)
    gold = V.label_to_gold(cert["labels"]["wfs"])
    items.append({"task_id": f"{tag}::wfs", "rec_id": tag, "cond": "wfs",
                  "family": prog.meta["family"], "kind": kind,
                  "gold": gold, "certified": cert["labels"],
                  "prompt": V.build_prompt(prog, "wfs")})


# divergent: even cycles, disjunction + conjunction
for k in (2, 4, 6):
    for mode in ("disj", "conj"):
        for th in TH.CYCLE_THEMES:
            p = G.cycle_gadget(k, mode, 0, th)
            add(p, f"cyc{k}-{mode}-{th['name']}", "divergent")

# controls: default-with-exception (gold A/B) and negation stacks (gold A/B)
for th in TH.DEFAULT_THEMES[:2]:
    for d in (1, 2, 3):
        for exc in (False, True):
            add(G.chain_default(d, exc, th), f"def-{th['name']}-{d}-{int(exc)}", "control")
for th in TH.STACK_THEMES:
    for nd in (1, 2, 3, 4):
        add(G.negation_stack(nd, th), f"stk-{th['name']}-{nd}", "control")

json.dump(items, open("data/wfs_big.json", "w"), indent=1)
from collections import Counter
print(f"Big WFS set: {len(items)} prompts")
print("kind:", dict(Counter(e['kind'] for e in items)))
print("gold:", dict(Counter(e['gold'] for e in items)))
