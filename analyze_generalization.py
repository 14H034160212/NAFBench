"""Generalization: does semantic-following transfer across verbalizations?
Compares narrative (A) vs abstract (B) framing, and cross-framing few-shot."""
import json, glob
import numpy as np

ev = {e["task_id"]: e for e in json.load(open("data/generalization.json"))}
models, ctok = {}, {}
for f in glob.glob("data/gen_answers/*.json"):
    if f.endswith("raw.json"): continue
    d = json.load(open(f)); models[d["model"]] = d["answers"]
    ctok[d["model"]] = d.get("completion_tokens", {})

def acc(m, framing):
    sub = [models[m].get(e["task_id"]) == e["gold"]
           for e in ev.values() if e["framing"] == framing and e["task_id"] in models[m]]
    return np.mean(sub) if sub else float("nan")

def toks(m, framing):
    vs = [ctok[m].get(e["task_id"]) for e in ev.values()
          if e["framing"] == framing and ctok[m].get(e["task_id"]) is not None]
    return np.mean(vs) if vs else float("nan")

print("=== does accuracy transfer across verbalization? (n=9 per framing) ===")
print(f"{'model':20s}  narrative(A)  abstract(B)  drop   | B+fewshot(A-exemplar)")
for m in sorted(models):
    a, b, bf = acc(m, "A_narrative"), acc(m, "B_abstract"), acc(m, "B_abstract_fewshotA")
    print(f"{m:20s}    {a:5.0%}        {b:5.0%}     {b-a:+4.0%}  |  {bf:5.0%}  ({bf-b:+.0%} vs B)")

print("\n=== completion tokens used (mean) — cost by framing ===")
for m in sorted(models):
    print(f"  {m:20s} narrative {toks(m,'A_narrative'):.0f}   abstract {toks(m,'B_abstract'):.0f}")
