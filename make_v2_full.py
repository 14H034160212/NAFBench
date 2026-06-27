"""Full v2 grid: all 4 bins x depth x width x theme-replicates x conditions.

Gives a balanced, multi-bin set for the regression
   correct ~ depth + width + bin  (+ theme as replicate for error bars).
"""
import json
from nafbench.instances import build_instance
from nafbench import solvers as S
from nafbench import verbalize_v2 as V2

BINS = ["control", "even_one_sided", "odd", "even_both_sided"]
DEPTHS = [0, 4, 8]
WIDTHS = [0, 4, 8]
THEMES = [0, 1, 2]
CONDS = ["cred", "skept", "wfs"]

items = []
# certify once per logical instance (labels/metrics are theme-independent)
for b in BINS:
    for d in DEPTHS:
        for w in WIDTHS:
            prog = build_instance(d, w, b)
            cert = S.certify_full(prog, "q")
            for th in THEMES:
                for c in CONDS:
                    items.append({
                        "task_id": f"v2-{b}-d{d}-w{w}-t{th}::{c}",
                        "rec_id": f"v2-{b}-d{d}-w{w}-t{th}", "cond": c,
                        "divergence_bin": b, "depth": d, "width": w, "theme": th,
                        "gold": V2.gold_for(cert["labels"], c),
                        "labels": cert["labels"], "metrics": cert["metrics"],
                        "prompt": V2.build_prompt(prog, c, theme=th),
                    })

json.dump(items, open("data/v2_full.json", "w"), indent=1)
from collections import Counter
print(f"v2 full grid: {len(items)} prompts "
      f"({len(BINS)} bins x {len(DEPTHS)}x{len(WIDTHS)} cells x {len(THEMES)} themes x {len(CONDS)} conds)")
print("gold spread:", dict(Counter(e["gold"] for e in items)))
print("gold by (bin,cond):")
for b in BINS:
    row = {c: dict(Counter(e["gold"] for e in items if e["divergence_bin"] == b and e["cond"] == c)) for c in CONDS}
    print(f"  {b:16s} {row}")
