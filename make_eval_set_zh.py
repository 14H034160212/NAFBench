"""Chinese mirror of the eval set: same programs/conditions, Chinese prompts.

Reconstructs the Program objects (with full meta) from the generator so the
Chinese verbalizer can render them, and reuses the same task_ids and
(language-independent) solver-certified gold.
"""
import json
from nafbench import generator as G
from nafbench import verbalize_zh as VZ

progs = {f"naf-{i:03d}": p for i, p in enumerate(G.generate_dataset(0))}
en = json.load(open("data/eval_set.json"))

items = []
for e in en:
    p = progs[e["rec_id"]]
    items.append({**{k: e[k] for k in ("task_id", "rec_id", "cond", "family",
                                        "divergent", "gold", "certified")},
                  "lang": "zh",
                  "prompt": VZ.build_prompt(p, e["cond"])})

json.dump(items, open("data/eval_set_zh.json", "w"), ensure_ascii=False, indent=1)
print(f"Chinese eval set: {len(items)} prompts")
# show one divergent example
for e in items:
    if e["task_id"] == "naf-050::wfs":
        print(e["prompt"])
        break
