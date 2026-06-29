"""Cycle-length sweep: characterize the dominant axis (which negation phenomenon
is hardest) by sweeping cycle length within each cyclic bin, parity-matched.
Fixed depth/width; conditions cred/skept/wfs."""
import json
from nafbench.instances import build_instance
from nafbench import solvers as S
from nafbench import verbalize_v2 as V2
from nafbench import metrics as MET

BIN_CYCLES = {"even_one_sided": [2, 4, 6], "odd": [3, 5, 7], "even_both_sided": [2, 4, 6]}
DEPTH, WIDTH = 8, 4
CONDS = ["cred", "skept", "wfs"]
THEME = 0

items = []
for b, cyc_opts in BIN_CYCLES.items():
    for cyc in cyc_opts:
        prog = build_instance(DEPTH, WIDTH, b, cycle_len=cyc)
        cert = S.certify_full(prog, "q")
        for c in CONDS:
            prompt = V2.build_prompt(prog, c, THEME)
            items.append({
                "task_id": f"cyc-{b}-k{cyc}::{c}", "rec_id": f"cyc-{b}-k{cyc}",
                "cond": c, "divergence_bin": b, "cycle_len": cyc,
                "gold": V2.gold_for(cert["labels"], c), "labels": cert["labels"],
                "length": MET.length_metrics(prompt), "prompt": prompt,
            })

json.dump(items, open("data/cyclesweep.json", "w"), indent=1)
print(f"cycle-sweep: {len(items)} prompts; bins x cycle lengths:")
for b, cs in BIN_CYCLES.items():
    print(f"  {b:16s} cycles {cs}  signature {items[[e['divergence_bin'] for e in items].index(b)]['labels']}")
