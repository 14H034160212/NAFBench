"""Held-out theme-2 test for the local SFT adapters (Exp 20).

12 prompts = 4 divergence bins x {cred, skept, wfs}, rendered at the held-out
SIZE (depth 8 / eff-width 8) in the held-out narrative surface (v2 theme 2,
'auditor'). Themes 0,1 are what make_sft_multi trains on, so this set measures
genuine cross-verbalization + cross-size transfer (audit finding #4).
"""
import json
from nafbench.instances import build_by_effwidth
from nafbench import solvers as S
from nafbench import verbalize_v2 as VA

BINS = ["control", "even_one_sided", "odd", "even_both_sided"]
CYC = {"control": 2, "even_one_sided": 4, "odd": 3, "even_both_sided": 4}
CONDS = ["cred", "skept", "wfs"]
THEME = 2  # held-out narrative surface

items = []
for b in BINS:
    prog = build_by_effwidth(8, 8, b, cycle_len=CYC[b])
    cert = S.certify_full(prog, "q")
    for c in CONDS:
        gold = VA.gold_for(cert["labels"], c)
        prompt = VA.build_prompt(prog, c, theme=THEME)
        items.append({
            "task_id": f"ho-{b}-{c}::{c}", "rec_id": f"ho-{b}-{c}",
            "cond": c, "divergence_bin": b, "gold": gold, "prompt": prompt,
        })

json.dump(items, open("data/heldout_theme2.json", "w"), indent=1)
print(f"held-out theme-2 set: {len(items)} prompts "
      f"({len(BINS)} bins x {len(CONDS)} conds, depth 8 / ew 8, theme {THEME})")
