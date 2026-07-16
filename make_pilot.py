"""Pilot set for the decisions in A. Mensfelt's latest note:

  (1) cycle-length shortcut: even bins at cycle 2 vs 4, odd at 1 vs 3
      (do models pattern-match trivial cycles like a:-not b,b:-not a?)
  (2) easy/hard boundary: (depth=2, eff_width=min) vs (depth=16, eff_width=16),
      where eff_width = shared subgoals + cycle length, min = cycle length.
  (3) condition screening: all five conditions, incl. the no-instruction default.

Records solver-certified labels, solver hardness, and INSTANCE LENGTH (tokens)
to control for length as a confound.
"""
import json
from nafbench.instances import build_by_effwidth, BIN_SIGNATURE
from nafbench import solvers as S
from nafbench import verbalize_v2 as V2
from nafbench import metrics as MET

CONDS = ["none", "closed_world", "cred", "skept", "wfs"]
DEPTHS = [2, 16]            # min depth = 2 (per note)
CYCLES = {"control": [2], "even_one_sided": [2, 4], "odd": [1, 3]}

items = []
for b, cyc_opts in CYCLES.items():
    for cyc in cyc_opts:
        cmin = 0 if b == "control" else cyc
        for d in DEPTHS:
            for ew in sorted({cmin, 16}):          # boundary: min vs 16
                prog = build_by_effwidth(d, ew, b, cycle_len=cyc)
                cert = S.certify_full(prog, "q")
                m = prog.meta
                for c in CONDS:
                    prompt = V2.build_prompt(prog, c, theme=0)
                    gold = None if c == "none" else V2.gold_for(cert["labels"], c)
                    items.append({
                        "task_id": f"pilot-{b}-cyc{cyc}-d{d}-ew{ew}::{c}",
                        "rec_id": f"pilot-{b}-cyc{cyc}-d{d}-ew{ew}", "cond": c,
                        "divergence_bin": b, "cycle_len": cyc, "depth": d,
                        "width_subgoals": m["width"], "effective_width": m["effective_width"],
                        "gold": gold, "labels": cert["labels"], "metrics": cert["metrics"],
                        "length": MET.length_metrics(prompt),
                        "prompt": prompt,
                    })

json.dump(items, open("data/pilot.json", "w"), indent=1)
from collections import Counter
print(f"pilot set: {len(items)} prompts over "
      f"{len({e['rec_id'] for e in items})} instances")
print("by bin:", dict(Counter(e["divergence_bin"] for e in items)))
print("token length range:", min(e["length"]["tokens"] for e in items), "..",
      max(e["length"]["tokens"] for e in items))
print("effective_width values:", sorted({e["effective_width"] for e in items}))
