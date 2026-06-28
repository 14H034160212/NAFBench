"""Full v3 formal grid (per the agreed design).

Fixed cycle length (even=4, odd=3). Axes: depth x effective_width (cycle folded
into width). All five conditions; two surface themes as replicates. Instance
length (tokens) recorded for confound control.
"""
import json
from nafbench.instances import build_by_effwidth
from nafbench import solvers as S
from nafbench import verbalize_v2 as V2
from nafbench import metrics as MET

BINS = ["control", "even_one_sided", "odd", "even_both_sided"]
CYCLE = {"control": 2, "even_one_sided": 4, "odd": 3, "even_both_sided": 4}
DEPTHS = [2, 8, 16]
EFFW = [4, 8, 16]            # >= min for every bin (control 0, odd 3, even 4)
THEMES = [0, 1]
CONDS = ["none", "closed_world", "cred", "skept", "wfs"]

items = []
for b in BINS:
    for d in DEPTHS:
        for ew in EFFW:
            prog = build_by_effwidth(d, ew, b, cycle_len=CYCLE[b])
            cert = S.certify_full(prog, "q")
            m = prog.meta
            for th in THEMES:
                for c in CONDS:
                    prompt = V2.build_prompt(prog, c, theme=th)
                    items.append({
                        "task_id": f"v3-{b}-d{d}-ew{ew}-t{th}::{c}",
                        "rec_id": f"v3-{b}-d{d}-ew{ew}-t{th}", "cond": c,
                        "divergence_bin": b, "cycle_len": CYCLE[b], "depth": d,
                        "effective_width": m["effective_width"],
                        "width_subgoals": m["width"], "theme": th,
                        "gold": None if c == "none" else V2.gold_for(cert["labels"], c),
                        "labels": cert["labels"], "metrics": cert["metrics"],
                        "length": MET.length_metrics(prompt),
                        "prompt": prompt,
                    })

json.dump(items, open("data/v3_full.json", "w"), indent=1)
from collections import Counter
n_inst = len({e["rec_id"] for e in items})
print(f"v3 full grid: {len(items)} prompts over {n_inst} instances "
      f"({len(BINS)} bins x {len(DEPTHS)}d x {len(EFFW)}w x {len(THEMES)} themes x {len(CONDS)} conds)")
print("token range:", min(e['length']['tokens'] for e in items), "..",
      max(e['length']['tokens'] for e in items))
print("gold (excl none):", dict(Counter(e["gold"] for e in items if e["gold"])))
