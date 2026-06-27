"""9-model correctness heatmap on the WFS condition (meeting visual)."""
import json, glob
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import numpy as np

recs = {json.loads(l)["id"]: json.loads(l) for l in open("data/nafbench_poc.jsonl")}
items = {e["task_id"]: e for e in json.load(open("data/eval_set.json"))}
wfs = [t for t in items if t.endswith("::wfs")]

def gold(t):
    rid, c = t.split("::"); return recs[rid]["gold_answer"][c]

ans = {}
for f in glob.glob("data/auto_answers/*.json"):
    if f.endswith("raw.json"): continue
    d = json.load(open(f)); ans[d["model"]] = d["answers"]
for m, a in json.load(open("data/claude_answers.json"))["models"].items():
    ans[m] = a

# order models by WFS accuracy
order = sorted(ans, key=lambda m: -sum(ans[m].get(t) == gold(t) for t in wfs))
order = [m for m in order if any(t in ans[m] for t in wfs)]

M = np.zeros((len(order), len(wfs)))
labels = [[""] * len(wfs) for _ in order]
for i, m in enumerate(order):
    for j, t in enumerate(wfs):
        a = ans[m].get(t); g = gold(t)
        M[i, j] = 1 if a == g else 0
        labels[i][j] = a or "·"

fig, ax = plt.subplots(figsize=(13, 5.2))
ax.imshow(M, cmap=plt.matplotlib.colors.ListedColormap(["#d9534f", "#5cb85c"]),
          aspect="auto", vmin=0, vmax=1)
ax.set_yticks(range(len(order))); ax.set_yticklabels(order)
short = [t.split("::")[0] + f"\n[{gold(t)}]" for t in wfs]
ax.set_xticks(range(len(wfs))); ax.set_xticklabels(short, fontsize=7)
for i in range(len(order)):
    for j in range(len(wfs)):
        ax.text(j, i, labels[i][j], ha="center", va="center", fontsize=8,
                color="white", fontweight="bold")
accs = [f"{int(M[i].sum())}/{len(wfs)}" for i in range(len(order))]
for i, a in enumerate(accs):
    ax.text(len(wfs) - 0.4, i, a, ha="left", va="center", fontsize=9)
ax.set_title("Following WELL-FOUNDED semantics: per-item correctness across 9 models\n"
             "green=correct, red=wrong; cell shows the model's answer, [.]=gold")
plt.tight_layout(); plt.savefig("data/model_heatmap.png", dpi=130)
print("Saved -> data/model_heatmap.png  (models x 12 WFS prompts)")
