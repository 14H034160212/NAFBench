"""Plots for the cross-lingual (EN vs ZH) and self-verification experiments."""
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


def acc(ans):
    sub = [t for t in wfs if t in ans]
    return sum(ans.get(t) == gold(t) for t in sub) / len(sub)


# ---- EN vs ZH ----
en_zh = []
for f in sorted(glob.glob("data/auto_answers/*.json")):
    if f.endswith("raw.json"):
        continue
    m = json.load(open(f))["model"]
    en = json.load(open(f))["answers"]
    zf = f.replace("/auto_answers/", "/zh_answers/")
    try:
        zh = json.load(open(zf))["answers"]
    except FileNotFoundError:
        continue
    en_zh.append((m, acc(en), acc(zh)))

# ---- direct vs self-verify ----
verify = []
for f in sorted(glob.glob("data/verify_answers/*.json")):
    if f.endswith("raw.json"):
        continue
    d = json.load(open(f))
    m = d["model"]
    df = f.replace("/verify_answers/", "/auto_answers/")
    direct = json.load(open(df))["answers"]
    verify.append((m, acc(direct), acc(d["answers"])))

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

labels = [r[0] for r in en_zh]
x = range(len(labels))
w = 0.38
ax1.bar([i - w / 2 for i in x], [r[1] for r in en_zh], w, label="English", color="#4c72b0")
ax1.bar([i + w / 2 for i in x], [r[2] for r in en_zh], w, label="Chinese", color="#dd8452")
ax1.set_xticks(list(x)); ax1.set_xticklabels(labels, rotation=20, ha="right")
ax1.set_ylim(0, 1.1); ax1.set_ylabel("WFS accuracy (12 prompts)")
ax1.set_title("Cross-lingual: English vs Chinese\n(same programs, faithful translation)")
ax1.axhline(0.5, ls="--", color="gray", lw=1); ax1.legend()

labels2 = [r[0] for r in verify]
x2 = range(len(labels2))
ax2.bar([i - w / 2 for i in x2], [r[1] for r in verify], w, label="direct", color="#c44e52")
ax2.bar([i + w / 2 for i in x2], [r[2] for r in verify], w, label="self-verify scaffold", color="#55a868")
ax2.set_xticks(list(x2)); ax2.set_xticklabels(labels2, rotation=20, ha="right")
ax2.set_ylim(0, 1.1); ax2.set_ylabel("WFS accuracy (12 prompts)")
ax2.set_title("Mitigation: verify-before-infer scaffold\n(prompt-only, no solver)")
ax2.axhline(0.5, ls="--", color="gray", lw=1); ax2.legend()

plt.tight_layout()
plt.savefig("data/crosslingual_mitigation.png", dpi=130)
print("Saved -> data/crosslingual_mitigation.png")
print("EN vs ZH (WFS):", [(m, round(e, 2), round(z, 2)) for m, e, z in en_zh])
print("direct vs verify (WFS):", [(m, round(d, 2), round(v, 2)) for m, d, v in verify])
