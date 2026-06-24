"""Build difficulty-axis 'ladder' eval sets (clean single-axis sweeps).

Two controlled axes from the proposal:
  * negation depth : alternating `not` stack, depth 1..8 (condition: none)
                     -> can the model track deeply nested negation?
  * rule depth     : default-with-exception chain, depth 1..6 (condition:
                     closed_world) -> does deep chaining degrade CWA application?

Both families are stratified (all semantics agree), so the gold is unambiguous
and the only thing varying is the depth.
"""
import json
from nafbench import generator as G
from nafbench import solvers as S
from nafbench import verbalize as V
from nafbench import themes as TH

items = []


def add(prog, cond, axis, axis_value, tag):
    q = prog.meta["query"]
    cert = S.certify(prog, q)
    gold = V.label_to_gold(cert["labels"][V.SEMANTICS_TO_SOLVER[cond]])
    items.append({
        "task_id": f"{tag}::{cond}",
        "rec_id": tag, "cond": cond,
        "axis": axis, "axis_value": axis_value,
        "family": prog.meta["family"], "theme": prog.meta["theme"],
        "gold": gold, "certified": cert["labels"],
        "prompt": V.build_prompt(prog, cond),
    })


# negation-depth ladder (condition: none)
for theme in TH.STACK_THEMES:
    for nd in range(1, 9):
        p = G.negation_stack(nd, theme)
        add(p, "none", "negation_depth", nd, f"negdep-{theme['name']}-{nd}")

# rule-depth ladder (condition: closed_world; no exception so gold=A throughout)
for theme in TH.DEFAULT_THEMES[:2]:
    for d in range(1, 7):
        p = G.chain_default(d, False, theme)
        add(p, "closed_world", "rule_depth", d, f"ruledep-{theme['name']}-{d}")

with open("data/ladder_set.json", "w") as f:
    json.dump(items, f, indent=1)

from collections import Counter
print(f"Ladder set: {len(items)} prompts")
print("by axis:", dict(Counter(e['axis'] for e in items)))
print("negation_depth golds:", [(e['axis_value'], e['gold'])
      for e in items if e['axis'] == 'negation_depth' and e['theme'] == 'authority'])
