"""Score the 44-item WFS set with 95% Wilson confidence intervals.

Reports overall WFS accuracy and the divergent / control breakdown, with error
bars, addressing the small-sample caveat of the 12-prompt headline.
"""
import json
import glob
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

items = {e["task_id"]: e for e in json.load(open("data/wfs_big.json"))}


def wilson(k, n, z=1.96):
    if n == 0:
        return 0, 0, 0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0, c - h), min(1, c + h)


rows = []
for f in glob.glob("data/big_answers/*.json"):
    if f.endswith("raw.json"):
        continue
    d = json.load(open(f))
    a = d["answers"]
    allt = [t for t in items if t in a]
    k = sum(a[t] == items[t]["gold"] for t in allt)
    div = [t for t in allt if items[t]["kind"] == "divergent"]
    ctl = [t for t in allt if items[t]["kind"] == "control"]
    kd = sum(a[t] == items[t]["gold"] for t in div)
    kc = sum(a[t] == items[t]["gold"] for t in ctl)
    rows.append((d["model"], k, len(allt), kd, len(div), kc, len(ctl)))

rows.sort(key=lambda r: r[1] / r[2])
print(f"{'model':22s} overall(95% CI)        divergent      control")
for m, k, n, kd, nd, kc, nc in rows:
    p, lo, hi = wilson(k, n)
    print(f"{m:22s} {k}/{n} {p:.0%} [{lo:.0%},{hi:.0%}]   {kd}/{nd} {kd/nd:.0%}   {kc}/{nc} {kc/nc:.0%}")

# plot overall accuracy with Wilson CIs
labels = [r[0] for r in rows]
ps = [r[1] / r[2] for r in rows]
errs = [wilson(r[1], r[2]) for r in rows]
lo = [p - e[1] for p, e in zip(ps, errs)]
hi = [e[2] - p for p, e in zip(ps, errs)]
fig, ax = plt.subplots(figsize=(10, 5.2))
ax.bar(range(len(labels)), ps, yerr=[lo, hi], capsize=5, color="#4c72b0")
ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=20, ha="right")
ax.set_ylim(0, 1.08); ax.set_ylabel("WFS accuracy (44 prompts) ± 95% Wilson CI")
ax.axhline(24 / 44, ls="--", color="gray", lw=1)
ax.text(0, 24 / 44 + 0.01, "always-C baseline (24/44)", color="gray", fontsize=8)
ax.set_title("Scaled WFS evaluation with confidence intervals (44 prompts: 24 divergent + 20 control)")
plt.tight_layout()
plt.savefig("data/wfs_big_ci.png", dpi=130)
print("\nSaved -> data/wfs_big_ci.png")
