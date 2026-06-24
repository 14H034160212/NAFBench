"""Combined cross-vendor scoring + plots.

Pulls every model's answers from:
  * data/auto_answers/*.json   (ollama open-source + OpenAI, all 24 conditions)
  * data/claude_answers.json   (Claude via subagents, WFS condition)
and scores against solver-certified gold from the dataset.

Headline = WFS accuracy (12 prompts, mixed gold 6C/3A/3B) across ALL models,
the one condition every model was run on. For models with the full 24-prompt
run we also break out stable / CWA-default / closed_world.
"""
import json
import glob
import os
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

recs = {json.loads(l)["id"]: json.loads(l) for l in open("data/nafbench_poc.jsonl")}
eval_items = {e["task_id"]: e for e in json.load(open("data/eval_set.json"))}


def gold(task):
    rid, cond = task.split("::")
    return recs[rid]["gold_answer"][cond]


# ---- collect all model answer dicts -------------------------------------
answers = {}            # model_name -> {task_id: letter}
provider = {}           # model_name -> "open" | "openai" | "claude"

for f in glob.glob("data/auto_answers/*.json"):
    if f.endswith(".raw.json"):
        continue
    d = json.load(open(f))
    answers[d["model"]] = d["answers"]
    provider[d["model"]] = "openai" if d["provider"] == "openai" else "open"

cl = json.load(open("data/claude_answers.json"))["models"]
for m, a in cl.items():
    answers[m] = a
    provider[m] = "claude"

# ---- WFS headline (all models) ------------------------------------------
wfs_tasks = [t for t in eval_items if t.endswith("::wfs")]
print(f"=== WFS accuracy on {len(wfs_tasks)} prompts (gold mix: "
      f"{sum(gold(t)=='C' for t in wfs_tasks)}xC / "
      f"{sum(gold(t)=='A' for t in wfs_tasks)}xA / "
      f"{sum(gold(t)=='B' for t in wfs_tasks)}xB) ===\n")

wfs_acc = {}
for m, a in answers.items():
    scored = [(t, a.get(t)) for t in wfs_tasks if t in a]
    if not scored:
        continue
    correct = sum(ans == gold(t) for t, ans in scored)
    wfs_acc[m] = (correct, len(scored))

for m in sorted(wfs_acc, key=lambda m: -wfs_acc[m][0] / wfs_acc[m][1]):
    k, n = wfs_acc[m]
    print(f"  {m:22s} [{provider[m]:6s}] {k:2d}/{n}  = {k/n:.0%}")

# ---- "always-C" baseline for reference ----------------------------------
allC = sum(gold(t) == "C" for t in wfs_tasks)
print(f"\n  (trivial 'always-C' baseline: {allC}/{len(wfs_tasks)} = {allC/len(wfs_tasks):.0%})")

# ---- condition breakdown for full-run models ----------------------------
conds = ["closed_world", "stable", "wfs"]
print("\n=== Condition breakdown (full-run models) ===")
print(f"{'model':22s} " + " ".join(f"{c:>13s}" for c in conds) + "   CWA-default")
for m, a in answers.items():
    if provider[m] == "claude":
        continue
    cells = []
    for c in conds:
        ts = [t for t in eval_items if t.endswith("::" + c) and t in a]
        k = sum(a[t] == gold(t) for t in ts)
        cells.append(f"{k}/{len(ts)}" if ts else "-")
    # CWA default = ::none items (gold A) where model fails to apply CWA
    nt = [t for t in eval_items if t.endswith("::none") and t in a]
    kc = sum(a[t] == gold(t) for t in nt)
    print(f"{m:22s} " + " ".join(f"{c:>13s}" for c in cells) + f"   {kc}/{len(nt)}")

# ============================ PLOTS =======================================
# Plot 1: WFS accuracy across all models (sorted), colored by provider
order = sorted(wfs_acc, key=lambda m: wfs_acc[m][0] / wfs_acc[m][1])
vals = [wfs_acc[m][0] / wfs_acc[m][1] for m in order]
pcolor = {"claude": "#4c72b0", "openai": "#55a868", "open": "#c44e52"}
colors = [pcolor[provider[m]] for m in order]

fig, ax = plt.subplots(figsize=(11, 5.5))
bars = ax.barh(range(len(order)), vals, color=colors)
ax.set_yticks(range(len(order)))
ax.set_yticklabels(order)
ax.set_xlim(0, 1.08)
ax.set_xlabel("accuracy vs solver-certified gold (well-founded semantics, 12 prompts)")
ax.set_title("NAF-Bench: following WELL-FOUNDED semantics across vendors\n"
             "(mixed gold 6xundefined / 3xtrue / 3xfalse; 'always-C' would score 50%)")
ax.axvline(allC / len(wfs_tasks), ls="--", color="gray", lw=1)
ax.text(allC / len(wfs_tasks) + 0.01, -0.4, "always-C baseline", color="gray", fontsize=8)
for b, m in zip(bars, order):
    k, n = wfs_acc[m]
    ax.text(b.get_width() + 0.01, b.get_y() + b.get_height() / 2,
            f"{k}/{n}", va="center", fontsize=9)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=pcolor[p], label=p) for p in pcolor],
          title="provider", loc="lower right")
plt.tight_layout()
plt.savefig("data/cross_vendor_wfs.png", dpi=130)
print("\nSaved -> data/cross_vendor_wfs.png")
