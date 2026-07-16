"""Multi-cycle experiment (A. Mensfelt's extended cycle parametrization).

Independent and interdependent multi-cycle structures, swept over the number of
cycles. All share signature (T,F,u,loop) so cred/skept/wfs gold = A/B/C; the new
knob is the number of cycles (= number of stable models). Records the underlying
logic program and the stable-model count with each instance (per request).
"""
import json
from nafbench.instances import build_multi_independent, build_interdependent
from nafbench import solvers as S
from nafbench import verbalize_generic as VG
from nafbench import metrics as MET

CONDS = ["none", "cred", "skept", "wfs"]
BUILDERS = {"independent": build_multi_independent, "interdependent": build_interdependent}
NCYCLES = [1, 2, 3, 4]

items = []
for sub, build in BUILDERS.items():
    for n in NCYCLES:
        prog = build(n)
        cert = S.certify_full(prog, "q")
        for c in CONDS:
            prompt = VG.build_prompt(prog, c)
            items.append({
                "task_id": f"mc-{sub}-n{n}::{c}", "rec_id": f"mc-{sub}-n{n}",
                "cond": c, "subtype": sub, "n_cycles": n,
                "gold": None if c == "none" else VG.gold_for(cert["labels"], c),
                "labels": cert["labels"],
                "n_stable_models": cert["n_stable_models"],   # per request
                "program": prog.pretty(),                     # per request
                "length": MET.length_metrics(prompt), "prompt": prompt,
            })

json.dump(items, open("data/multicycle.json", "w"), indent=1)
print(f"multi-cycle set: {len(items)} prompts")
for sub in BUILDERS:
    print(f"  {sub}: " + "  ".join(
        f"n{n}->{next(e['n_stable_models'] for e in items if e['subtype']==sub and e['n_cycles']==n)}models"
        for n in NCYCLES))
print("sample program (interdependent n=2):")
print("  " + next(e["program"] for e in items if e["task_id"] == "mc-interdependent-n2::cred").replace("\n", "\n  "))
