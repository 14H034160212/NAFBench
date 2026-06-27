"""Assemble the static Cloudflare-Pages demo: embed precomputed data into
site/data.js and copy the figures into site/img/. No backend; everything the
page needs is baked in (the solvers/models cannot run in a browser)."""
import json, os, glob, shutil

os.makedirs("site/img", exist_ok=True)
recs = {json.loads(l)["id"]: json.loads(l) for l in open("data/nafbench_poc.jsonl")}

# ---- 1) 9-model WFS panel (12 prompts) ----
eset = {e["task_id"]: e for e in json.load(open("data/eval_set.json"))}
wfs_tasks = [t for t in eset if t.endswith("::wfs")]
answers = {}
for f in glob.glob("data/auto_answers/*.json"):
    if f.endswith("raw.json"): continue
    d = json.load(open(f)); answers[d["model"]] = d["answers"]
for m, a in json.load(open("data/claude_answers.json"))["models"].items():
    answers[m] = a
def gold(t): rid, c = t.split("::"); return recs[rid]["gold_answer"][c]

models_order = sorted([m for m in answers if any(t in answers[m] for t in wfs_tasks)],
                      key=lambda m: -sum(answers[m].get(t) == gold(t) for t in wfs_tasks))
wfs_items = []
for t in wfs_tasks:
    rid = t.split("::")[0]
    wfs_items.append({"id": rid, "rules": recs[rid]["premises_nl"],
                      "question": recs[rid]["query_nl"], "gold": gold(t),
                      "certified": recs[rid]["certified_labels"]})
wfs_panel = {"models": models_order, "items": wfs_items,
             "answers": {m: [answers[m].get(t) for t in wfs_tasks] for m in models_order},
             "acc": {m: f"{sum(answers[m].get(t)==gold(t) for t in wfs_tasks)}/{len(wfs_tasks)}"
                     for m in models_order}}

# ---- 2) v2 explorer (bin x depth x width, theme 0) ----
v2 = [e for e in json.load(open("data/v2_full.json")) if e["theme"] == 0]
v2_index = {}
for e in v2:
    key = f"{e['divergence_bin']}|{e['depth']}|{e['width']}"
    v2_index.setdefault(key, {"bin": e["divergence_bin"], "depth": e["depth"],
                              "width": e["width"], "labels": e["labels"],
                              "metrics": e["metrics"], "conds": {}})
    v2_index[key]["conds"][e["cond"]] = {"prompt": e["prompt"], "gold": e["gold"]}
v2_list = list(v2_index.values())
bins = ["control", "even_one_sided", "odd", "even_both_sided"]
depths = sorted({e["depth"] for e in v2}); widths = sorted({e["width"] for e in v2})

data = {"wfs_panel": wfs_panel, "v2": v2_list, "v2_bins": bins,
        "v2_depths": depths, "v2_widths": widths,
        "figures": [os.path.basename(p) for p in sorted(glob.glob("data/*.png"))]}

with open("site/data.js", "w") as f:
    f.write("window.NAFBENCH = " + json.dumps(data, ensure_ascii=False) + ";\n")

for p in glob.glob("data/*.png"):
    shutil.copy(p, "site/img/")

print(f"site/data.js written: {len(models_order)} models, {len(wfs_items)} WFS items, "
      f"{len(v2_list)} v2 cells, {len(data['figures'])} figures")
