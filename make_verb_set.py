"""Verbalization-comparison set (A. Mensfelt's question: compare the influence of
different verbalizations on local models).

Renders the SAME canonical program under the three surface framings (THEMES_V2:
checklist/escalation, sensor/alarm, auditor/override) via verbalize_v2, holding
the logic (hence the certified gold) fixed. Any change in a model's answer across
themes is pure verbalization sensitivity -- the answer should be invariant.
Grouped by (program, cond); one group = the same item in 3 framings.
"""
import json
from nafbench.instances import build_instance
from nafbench.solvers import stable_cred_skept, wfs_query
from nafbench import verbalize_v2 as V2
from nafbench.verbalize_v2 import gold_for

BINS = ["control", "even_one_sided", "odd", "even_both_sided"]
CYC = {"control": 2, "even_one_sided": 4, "odd": 3, "even_both_sided": 4}
SIZES = [(4, 4), (8, 2)]
CONDS = ["closed_world", "cred", "skept", "wfs"]
THEMES = [0, 1, 2]
WMAP = {"true": "T", "false": "F", "undefined": "u"}

items = []
for b in BINS:
    for (d, w) in SIZES:
        prog = build_instance(d, w, b, CYC[b])
        cr, sk, nmods, conf, ch = stable_cred_skept(prog, "q")
        wl = WMAP[wfs_query(prog, "q")]
        sldnf = "loop" if b != "control" else "T"
        labels = {"cred": cr, "skept": sk, "wfs": wl, "sldnf": sldnf}
        for c in CONDS:
            for th in THEMES:
                prompt = V2.build_prompt(prog, c, theme=th)
                items.append({
                    "task_id": f"verb-{b}-d{d}-w{w}-{c}-t{th}::{c}",
                    "rec_id": f"verb-{b}-d{d}-w{w}-{c}",   # group across themes
                    "cond": c, "divergence_bin": b, "theme": th,
                    "depth": d, "width": w, "cycle_len": CYC[b],
                    "gold": gold_for(labels, c), "labels": labels,
                    "prompt": prompt,
                })

json.dump(items, open("data/verb_set.json", "w"), indent=1)
ngrp = len({e["rec_id"] for e in items})
print(f"verb set: {len(items)} prompts = {len(BINS)} bins x {len(SIZES)} sizes x "
      f"{len(CONDS)} conds x {len(THEMES)} themes  ({ngrp} (program,cond) groups)")
