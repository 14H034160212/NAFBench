"""Production headline set — fixed (depth, width), one verbalization, all bins.

Per the agreed plan: a single fixed (depth, width) for every bin, one theme, all
conditions. This emits the BASE prompts (4 bins x 5 conditions = 20 prompts).

"30 instances per cell" — OPEN DESIGN QUESTION (asked A. Słusarz):
Our controlled-NL prompt is a *deterministic* function of
(bin, depth, width, cycle_len, theme), and the verbalizer only renders small
cycle lengths, so we cannot mint 30 distinct NL programs per cell at a fixed size
without extending the generator. The three readings are:
  (a) 30 stochastic DECODE SAMPLES of each prompt at T>0  -> run_production.sh
      does this now (no generator change); CIs cluster by the base program.
  (b) 30 distinct PROGRAMS per cell -> needs a gold-preserving structural-
      variation extension to the generator (scoped, not yet built).
  (c) 30 SURFACE variants -> conflicts with "one verbalization".
This script builds the base set for (a); switching to (b) only changes how the
set is expanded, not the driver.
"""
import json
from nafbench.instances import build_instance
from nafbench import solvers as S
from nafbench import verbalize_v2 as V2
from nafbench import metrics as MET

DEPTH, WIDTH, THEME = 4, 4, 0          # fixed cell (size is inert per Exp 13/15)
BINS = ["control", "even_one_sided", "odd", "even_both_sided"]
CYC = {"control": 2, "even_one_sided": 4, "odd": 3, "even_both_sided": 4}
CONDS = ["none", "closed_world", "cred", "skept", "wfs"]

items = []
for b in BINS:
    prog = build_instance(DEPTH, WIDTH, b, cycle_len=CYC[b])
    cert = S.certify_full(prog, "q")
    for c in CONDS:
        prompt = V2.build_prompt(prog, c, theme=THEME)
        items.append({
            "task_id": f"prod-{b}-{c}::{c}", "rec_id": f"prod-{b}",
            "cond": c, "divergence_bin": b, "cycle_len": CYC[b],
            "depth": DEPTH, "width": WIDTH,
            "gold": None if c == "none" else V2.gold_for(cert["labels"], c),
            "labels": cert["labels"], "n_stable_models": cert["n_stable_models"],
            "metrics": cert["metrics"], "program": prog.pretty(),
            "length": MET.length_metrics(prompt), "prompt": prompt,
        })

json.dump(items, open("data/production_set.json", "w"), indent=1)
print(f"production base set: {len(items)} prompts "
      f"({len(BINS)} bins x {len(CONDS)} conds, depth {DEPTH} / width {WIDTH}, theme {THEME})")
print("NOTE: expand to 30 instances/cell per the definition A. Słusarz confirms "
      "(default: 30 decode samples via run_production.sh).")
