"""Generic (abstract) verbalization of the 44-prompt WFS set — the TEST framing
for the cross-verbalization SFT check (adapters were trained on narrative)."""
import json
from collections import Counter
from nafbench.generator import cycle_gadget
from nafbench import generator as G
from nafbench import solvers as S
from nafbench import verbalize_generic as VG
import nafbench.themes as TH

items = []
# divergent: even cycles k in {2,4,6} x disj/conj x 4 themes
for k in (2, 4, 6):
    for mode in ("disj", "conj"):
        for th in TH.CYCLE_THEMES:
            p = cycle_gadget(k, mode, 0, th)
            cert = S.certify_full(p, "q")
            items.append({"task_id": f"gcyc{k}-{mode}-{th['name']}::wfs",
                          "rec_id": f"gcyc{k}-{mode}-{th['name']}", "cond": "wfs",
                          "kind": "divergent", "gold": VG.gold_for(cert["labels"], "wfs"),
                          "prompt": VG.build_prompt(p, "wfs")})
# controls: default-with-exception + negation stacks
for th in TH.DEFAULT_THEMES[:2]:
    for d in (1, 2, 3):
        for exc in (False, True):
            p = G.chain_default(d, exc, th); cert = S.certify_full(p, "q")
            items.append({"task_id": f"gdef-{th['name']}-{d}-{int(exc)}::wfs",
                          "rec_id": f"gdef-{th['name']}-{d}-{int(exc)}", "cond": "wfs",
                          "kind": "control", "gold": VG.gold_for(cert["labels"], "wfs"),
                          "prompt": VG.build_prompt(p, "wfs")})
for th in TH.STACK_THEMES:
    for nd in (1, 2, 3, 4):
        p = G.negation_stack(nd, th); cert = S.certify_full(p, "q")
        items.append({"task_id": f"gstk-{th['name']}-{nd}::wfs",
                      "rec_id": f"gstk-{th['name']}-{nd}", "cond": "wfs",
                      "kind": "control", "gold": VG.gold_for(cert["labels"], "wfs"),
                      "prompt": VG.build_prompt(p, "wfs")})

json.dump(items, open("data/wfs_big_generic.json", "w"), indent=1)
print("generic WFS set:", len(items), "| kind", dict(Counter(e["kind"] for e in items)),
      "| gold", dict(Counter(e["gold"] for e in items)))
