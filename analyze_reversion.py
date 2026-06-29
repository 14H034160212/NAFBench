"""Default-semantics reversion — the proposal's signature diagnostic.

For each instance the model's no-instruction ('none') answer is its DEFAULT.
For an explicit semantics c, a 'conflict' item is one where the certified answer
gold(c) differs from the model's default answer (following c requires leaving the
default). Reversion = the model still outputs its default answer on a conflict
item (i.e., it ignored the instruction). Computed from already-collected v3 data.
"""
import json, glob
import numpy as np

ev = {e["task_id"]: e for e in json.load(open("data/v3_full.json"))}
models = {}
for f in glob.glob("data/v3_answers/*.json"):
    if f.endswith("raw.json"): continue
    d = json.load(open(f)); models[d["model"]] = d["answers"]

EXPL = ["closed_world", "cred", "skept", "wfs"]

def default_ans(m, rid):
    return models[m].get(f"{rid}::none")

print("=== default-semantics reversion (v3 grid) ===")
print(f"{'model':20s} conflicts  reverted  reversion_rate  follow_rate")
for m in sorted(models):
    a = models[m]
    conf = rev = follow = 0
    for t, e in ev.items():
        if e["cond"] not in EXPL or t not in a:
            continue
        d = default_ans(m, e["rec_id"])
        if d is None or e["gold"] is None:
            continue
        if e["gold"] != d:                  # conflict: instruction != default
            conf += 1
            if a[t] == d:                   # stuck with default
                rev += 1
            elif a[t] == e["gold"]:         # correctly switched
                follow += 1
    rr = rev / conf if conf else float("nan")
    fr = follow / conf if conf else float("nan")
    print(f"{m:20s} {conf:8d}  {rev:8d}  {rr:11.0%}    {fr:.0%}")

print("\n=== what is each model's default closest to? (none-answer vs each gold) ===")
for m in sorted(models):
    a = models[m]; match = {c: 0 for c in EXPL}; n = 0
    seen = set()
    for t, e in ev.items():
        rid = e["rec_id"]
        if rid in seen or f"{rid}::none" not in a:
            continue
        seen.add(rid); n += 1
        d = a[f"{rid}::none"]
        for c in EXPL:
            g = ev.get(f"{rid}::{c}", {}).get("gold")
            if g is not None and d == g:
                match[c] += 1
    print(f"  {m:20s} " + "  ".join(f"{c}:{match[c]/n:.0%}" for c in EXPL))
