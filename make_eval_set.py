"""Build a deterministic, stratified evaluation set from the certified dataset.

The set deliberately MIXES:
  * divergent probes (WFS gold = C) under {stable, wfs}
  * stratified controls (WFS gold = A or B) under {wfs}      -> guards against a
    model trivially scoring by always answering "C" under WFS
  * default-with-exception items under {none, closed_world}  -> CWA reversion

Each entry has a stable task_id so every model is scored on the same prompts.
"""
import json

recs = [json.loads(l) for l in open("data/nafbench_poc.jsonl")]
by_id = {r["id"]: r for r in recs}


def pick(pred, n):
    out = [r for r in recs if pred(r)]
    return out[:n]


eval_items = []


def add(rec, conds):
    for c in conds:
        eval_items.append({
            "task_id": f"{rec['id']}::{c}",
            "rec_id": rec["id"], "cond": c,
            "family": rec["family"], "axes": rec["axes"],
            "divergent": rec["divergent"],
            "gold": rec["gold_answer"][c],
            "certified": rec["certified_labels"],
            "prompt": rec["prompt"][c],
        })


# --- divergent probes: cycle gadgets, varied length & mode, under stable+wfs ---
div = [r for r in recs if r["divergent"]]
# group by (cycle_len, mode) and take one per group for structural spread
seen = set()
div_pick = []
for r in sorted(div, key=lambda r: (r["axes"]["cycle"], r["family"])):
    key = (r["axes"].get("cycle"), r["certified_labels"]["stable"],
           r["program"].count(":-"))
    if key in seen:
        continue
    seen.add(key)
    div_pick.append(r)
div_pick = div_pick[:6]
for r in div_pick:
    add(r, ["stable", "wfs"])

# --- WFS controls with definite gold (A or B): stratified chains & stacks ---
ctrl = [r for r in recs if not r["divergent"]
        and r["gold_answer"]["wfs"] in ("A", "B")
        and r["family"] in ("chain_default", "negation_stack")]
# spread across families/depths/gold
ctrl_pick, used = [], set()
for r in ctrl:
    key = (r["family"], r["gold_answer"]["wfs"], r["axes"]["rule_depth"] % 3)
    if key in used:
        continue
    used.add(key)
    ctrl_pick.append(r)
ctrl_pick = ctrl_pick[:6]
for r in ctrl_pick:
    add(r, ["wfs"])

# --- CWA reversion: default-with-exception, no flag (gold A), none + CWA ---
cwa = [r for r in recs if r["family"] == "chain_default"
       and not r["axes"].get("stratified", True) is False
       and r["gold_answer"]["none"] == "A"][:3]
for r in cwa:
    add(r, ["none", "closed_world"])

with open("data/eval_set.json", "w") as f:
    json.dump(eval_items, f, indent=1)

from collections import Counter
print(f"Eval set: {len(eval_items)} prompts over {len({e['rec_id'] for e in eval_items})} programs")
print("by condition:", dict(Counter(e["cond"] for e in eval_items)))
print("by gold:", dict(Counter(e["gold"] for e in eval_items)))
print("WFS golds:", dict(Counter(e["gold"] for e in eval_items if e["cond"] == "wfs")))
for e in eval_items:
    print(f"  {e['task_id']:24s} fam={e['family']:14s} gold={e['gold']} cert={e['certified']}")
