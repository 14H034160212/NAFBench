"""Extended-range grid: push depth and effective-width to 32 to see whether the
moderation effects grow with range (they were weak in 2-16). Cycle fixed 4/3,
5 conditions, 1 theme (range is the focus), length recorded."""
import json
from nafbench.instances import build_by_effwidth
from nafbench import solvers as S
from nafbench import verbalize_v2 as V2
from nafbench import metrics as MET

BINS = ["control", "even_one_sided", "odd", "even_both_sided"]
CYCLE = {"control": 2, "even_one_sided": 4, "odd": 3, "even_both_sided": 4}
DEPTHS = [2, 16, 32]
EFFW = [4, 16, 32]
CONDS = ["none", "closed_world", "cred", "skept", "wfs"]
THEME = 0

items = []
for b in BINS:
    for d in DEPTHS:
        for ew in EFFW:
            prog = build_by_effwidth(d, ew, b, cycle_len=CYCLE[b])
            cert = S.certify_full(prog, "q")
            m = prog.meta
            for c in CONDS:
                prompt = V2.build_prompt(prog, c, THEME)
                items.append({
                    "task_id": f"ext-{b}-d{d}-ew{ew}::{c}",
                    "rec_id": f"ext-{b}-d{d}-ew{ew}", "cond": c,
                    "divergence_bin": b, "cycle_len": CYCLE[b], "depth": d,
                    "effective_width": m["effective_width"], "width_subgoals": m["width"],
                    "gold": None if c == "none" else V2.gold_for(cert["labels"], c),
                    "labels": cert["labels"], "length": MET.length_metrics(prompt),
                    "prompt": prompt,
                })

json.dump(items, open("data/v3_ext.json", "w"), indent=1)
print(f"extended grid: {len(items)} prompts over {len({e['rec_id'] for e in items})} instances")
print("token range:", min(e['length']['tokens'] for e in items), "..",
      max(e['length']['tokens'] for e in items))
