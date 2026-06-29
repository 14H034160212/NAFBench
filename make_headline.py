"""Balanced 'headline' set for error bars: the 3 divergent bins x 3 themes x 5
conditions at fixed moderate size (depth=8, effective_width=8). Run multiple
times at T>0 to get sampling variance; CIs computed over instance x theme x run."""
import json
from nafbench.instances import build_by_effwidth
from nafbench import solvers as S
from nafbench import verbalize_v2 as V2

BINS = ["even_one_sided", "odd", "even_both_sided"]
CYC = {"even_one_sided": 4, "odd": 3, "even_both_sided": 4}
THEMES = [0, 1, 2]
CONDS = ["none", "closed_world", "cred", "skept", "wfs"]

items = []
for b in BINS:
    prog = build_by_effwidth(8, 8, b, cycle_len=CYC[b])
    cert = S.certify_full(prog, "q")
    for th in THEMES:
        for c in CONDS:
            items.append({
                "task_id": f"hl-{b}-t{th}::{c}", "rec_id": f"hl-{b}-t{th}",
                "cond": c, "divergence_bin": b, "theme": th,
                "gold": None if c == "none" else V2.gold_for(cert["labels"], c),
                "labels": cert["labels"], "n_stable_models": cert["n_stable_models"],
                "program": prog.pretty(),
                "prompt": V2.build_prompt(prog, c, theme=th),
            })

json.dump(items, open("data/headline.json", "w"), indent=1)
print(f"headline set: {len(items)} prompts ({len(BINS)} bins x {len(THEMES)} themes x {len(CONDS)} conds)")
