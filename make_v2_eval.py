"""Build the v2 grid eval set to test the width-vs-depth hypothesis.

Main grid: bin = even_one_sided (the richest (T,F,u,loop) signature), so the
three conditions cred/skept/wfs have gold A/B/C respectively -- no trivial
baseline. Sweep depth x width; record solver hardness per instance.
"""
import json
from nafbench.instances import build_instance
from nafbench import solvers as S
from nafbench import verbalize_v2 as V2

BIN = "even_one_sided"
DEPTHS = [0, 2, 4, 6, 8]
WIDTHS = [0, 2, 4, 6, 8]
CONDS = ["cred", "skept", "wfs"]   # gold spans A / B / C for this bin

items = []
for d in DEPTHS:
    for w in WIDTHS:
        prog = build_instance(d, w, BIN)
        cert = S.certify_full(prog, "q")
        for c in CONDS:
            items.append({
                "task_id": f"v2-{BIN}-d{d}-w{w}::{c}",
                "rec_id": f"v2-{BIN}-d{d}-w{w}", "cond": c,
                "divergence_bin": BIN, "depth": d, "width": w,
                "gold": V2.gold_for(cert["labels"], c),
                "labels": cert["labels"],
                "metrics": cert["metrics"],
                "prompt": V2.build_prompt(prog, c),
            })

json.dump(items, open("data/v2_eval.json", "w"), indent=1)
from collections import Counter
print(f"v2 grid eval: {len(items)} prompts "
      f"({len(DEPTHS)}x{len(WIDTHS)} cells x {len(CONDS)} conds)")
print("gold spread:", dict(Counter(e["gold"] for e in items)))
print("gold by cond:", {c: dict(Counter(e["gold"] for e in items if e["cond"] == c)) for c in CONDS})
print("\n--- sample prompt (cred, d=4, w=4) ---")
print(next(e["prompt"] for e in items if e["task_id"] == f"v2-{BIN}-d4-w4::cred"))
