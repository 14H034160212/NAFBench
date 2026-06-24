"""Summary of the mitigation-by-training runs (base vs SFT vs SFT+DPO).

Reads data/local_answers/*.json, scores against the held-out 44-prompt WFS set,
shows seed error bars for the multi-seed Qwen2.5-7B SFT.
"""
import json, glob, statistics as st
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

items = json.load(open("data/wfs_big.json"))
def score(tag, kind=None):
    a = json.load(open(f"data/local_answers/{tag}.json"))["answers"]
    sub = items if kind is None else [e for e in items if e["kind"] == kind]
    return sum(a[e["task_id"]] == e["gold"] for e in sub), len(sub)

def acc(tag, kind=None):
    k, n = score(tag, kind); return k / n

print("=== mitigation-by-training (held-out 44-prompt WFS set) ===")
rows = []
# gemma-3-4b-it (Exp 8)
rows.append(("gemma-3-4b-it base", acc("base"), acc("base","divergent")))
rows.append(("gemma-3-4b-it +SFT", acc("sft"), acc("sft","divergent")))
# qwen2.5-7b base / SFT (3 seeds) / SFT+DPO
rows.append(("qwen2.5-7b base", acc("base_qwen"), acc("base_qwen","divergent")))
seeds = [t for t in ["sft_qwen_s1","sft_qwen_s2","sft_qwen_s3"] if glob.glob(f"data/local_answers/{t}.json")]
ov = [acc(t) for t in seeds]; dv = [acc(t,"divergent") for t in seeds]
print(f"qwen2.5-7b +SFT seeds overall: {[round(x,3) for x in ov]} mean {st.mean(ov):.3f} "
      f"std {st.pstdev(ov):.3f} | divergent {[round(x,3) for x in dv]}")
rows.append((f"qwen2.5-7b +SFT (n={len(seeds)})", st.mean(ov), st.mean(dv)))
rows.append(("qwen2.5-7b +SFT+DPO", acc("sftdpo_qwen"), acc("sftdpo_qwen","divergent")))
# qwen3.5-9b (thinking-aware eval, 2048-token budget) if present
if glob.glob("data/local_answers/base_q35_t.json"):
    rows.append(("qwen3.5-9b base (think)", acc("base_q35_t"), acc("base_q35_t","divergent")))
if glob.glob("data/local_answers/sft_q35_t.json"):
    rows.append(("qwen3.5-9b +SFT (think)", acc("sft_q35_t"), acc("sft_q35_t","divergent")))

for name, o, d in rows:
    print(f"  {name:26s} overall {o:.0%}  divergent {d:.0%}")

# plot
labels = [r[0] for r in rows]
ov_v = [r[1] for r in rows]; dv_v = [r[2] for r in rows]
err = [0]*len(rows)
if len(seeds) > 1:
    err[3] = st.pstdev(ov)  # the SFT(n) bar
x = range(len(labels)); w = 0.4
fig, ax = plt.subplots(figsize=(12, 5.5))
ax.bar([i-w/2 for i in x], ov_v, w, yerr=[err,[0]*len(err)] if any(err) else None,
       capsize=4, label="overall (44)", color="#4c72b0")
ax.bar([i+w/2 for i in x], dv_v, w, label="divergent (24, gold C)", color="#dd8452")
ax.set_xticks(list(x)); ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=8)
ax.set_ylim(0,1.08); ax.set_ylabel("WFS accuracy (held-out 44)")
ax.axhline(24/44, ls="--", color="gray", lw=1)
ax.set_title("Mitigation by training: solver-certified SFT (+DPO) across models\n"
             "(error bar = seed std on Qwen2.5-7B SFT; divergent reaches ceiling)")
ax.legend()
plt.tight_layout(); plt.savefig("data/train_summary.png", dpi=130)
print("Saved -> data/train_summary.png")
