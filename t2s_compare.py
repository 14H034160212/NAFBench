"""Compare DIRECT reasoning vs TRANSLATE-THEN-SOLVE, per model.

Direct  = data/auto_answers/<model>.json   (model applies the semantics)
T2S     = data/t2s_answers/<model>.json    (model only translates; solver applies)
Scored against the same solver-certified gold. Also reports translation
fidelity (how often the solver verdict on the translated program equals gold).
"""
import json
import glob
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

recs = {json.loads(l)["id"]: json.loads(l) for l in open("data/nafbench_poc.jsonl")}
items = {e["task_id"]: e for e in json.load(open("data/eval_set.json"))}


def gold(t):
    rid, c = t.split("::")
    return recs[rid]["gold_answer"][c]


wfs = [t for t in items if t.endswith("::wfs")]
allt = list(items)


def acc(ans, tasks):
    sub = [t for t in tasks if t in ans]
    return sum(ans.get(t) == gold(t) for t in sub), len(sub)


rows = []
for f in glob.glob("data/t2s_answers/*.json"):
    d = json.load(open(f))
    m = d["model"]
    t2s = d["answers"]
    direct_f = f.replace("/t2s_answers/", "/auto_answers/")
    try:
        direct = json.load(open(direct_f))["answers"]
    except FileNotFoundError:
        # Claude models: direct answers live in claude_answers.json
        cl = json.load(open("data/claude_answers.json"))["models"]
        if m in cl:
            direct = cl[m]
        else:
            continue
    dk, dn = acc(direct, wfs)
    tk, tn = acc(t2s, wfs)
    to_k, to_n = acc(t2s, allt)
    rows.append((m, dk, dn, tk, tn, to_k, to_n, d["parsed_ok"], d["n_programs"]))

rows.sort(key=lambda r: r[1] / r[2])
print(f"{'model':22s} direct-WFS  T2S-WFS  T2S-overall  parsed")
for m, dk, dn, tk, tn, ok, on, p, npr in rows:
    print(f"{m:22s}   {dk}/{dn}      {tk}/{tn}     {ok}/{on}      {p}/{npr}")

# ---- plot: direct vs T2S WFS accuracy ----
labels = [r[0] for r in rows]
direct_acc = [r[1] / r[2] for r in rows]
t2s_acc = [r[3] / r[4] for r in rows]
x = range(len(labels))
w = 0.38
fig, ax = plt.subplots(figsize=(11, 5.2))
b1 = ax.bar([i - w / 2 for i in x], direct_acc, w, label="direct reasoning", color="#c44e52")
b2 = ax.bar([i + w / 2 for i in x], t2s_acc, w, label="translate-then-solve", color="#4c72b0")
ax.set_xticks(list(x))
ax.set_xticklabels(labels, rotation=20, ha="right")
ax.set_ylim(0, 1.12)
ax.set_ylabel("WFS accuracy vs certified gold (12 prompts)")
ax.set_title("Direct reasoning vs translate-then-solve (PrologMCP-style)\n"
             "letting the solver apply the semantics lifts strong translators to ~100%")
for b in list(b1) + list(b2):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.02,
            f"{b.get_height():.0%}", ha="center", fontsize=8)
ax.axhline(0.5, ls="--", color="gray", lw=1)
ax.legend(loc="lower center")
plt.tight_layout()
plt.savefig("data/direct_vs_t2s.png", dpi=130)
print("\nSaved -> data/direct_vs_t2s.png")
