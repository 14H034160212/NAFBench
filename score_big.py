"""Score the 44-item WFS set with 95% CIs CLUSTERED BY PROGRAM.

Audit finding #3: the 44 prompts are theme-replicates of ~11 distinct program
structures, so a prompt-level Wilson interval pseudoreplicates. We bootstrap
over structures instead (nafbench.clusterstats).
"""
import json
import glob
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from nafbench.clusterstats import cluster_bootstrap_ci

items = {e["task_id"]: e for e in json.load(open("data/wfs_big.json"))}
THEMES = ("meeting", "panel", "network", "committee")


def structure_of(task_id):
    """Cluster key: task_id minus '::cond' and the trailing theme token."""
    base = task_id.split("::", 1)[0]
    parts = base.rsplit("-", 1)
    return parts[0] if len(parts) == 2 and parts[1] in THEMES else base


rows = []
for f in glob.glob("data/big_answers/*.json"):
    if f.endswith("raw.json"):
        continue
    d = json.load(open(f))
    a = d["answers"]
    allt = [t for t in items if t in a]
    by_prog, by_prog_div, by_prog_ctl = {}, {}, {}
    for t in allt:
        s = structure_of(t)
        outcome = int(a[t] == items[t]["gold"])
        by_prog.setdefault(s, []).append(outcome)
        (by_prog_div if items[t]["kind"] == "divergent" else by_prog_ctl).setdefault(s, []).append(outcome)
    p, lo, hi, k, n, npr = cluster_bootstrap_ci(by_prog)
    _, _, _, kd, nd, _ = cluster_bootstrap_ci(by_prog_div)
    _, _, _, kc, nc, _ = cluster_bootstrap_ci(by_prog_ctl)
    rows.append((d["model"], p, lo, hi, k, n, npr, kd, nd, kc, nc))

rows.sort(key=lambda r: r[1])
print(f"{'model':22s} overall (95% CI, clustered)     divergent      control")
for m, p, lo, hi, k, n, npr, kd, nd, kc, nc in rows:
    dv = f"{kd}/{nd} {kd/nd:.0%}" if nd else "--"
    cv = f"{kc}/{nc} {kc/nc:.0%}" if nc else "--"
    print(f"{m:22s} {k}/{n} {p:.0%} [{lo:.0%},{hi:.0%}] ({npr}p)   {dv}   {cv}")

# plot overall accuracy with program-clustered CIs
labels = [r[0] for r in rows]
ps = [r[1] for r in rows]
lo = [r[1] - r[2] for r in rows]
hi = [r[3] - r[1] for r in rows]
n_struct = rows[0][6] if rows else 0
fig, ax = plt.subplots(figsize=(10, 5.2))
ax.bar(range(len(labels)), ps, yerr=[lo, hi], capsize=5, color="#4c72b0")
ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=20, ha="right")
ax.set_ylim(0, 1.08); ax.set_ylabel("WFS accuracy (44 prompts) ± 95% CI (clustered)")
ax.axhline(24 / 44, ls="--", color="gray", lw=1)
ax.text(0, 24 / 44 + 0.01, "always-C baseline (24/44)", color="gray", fontsize=8)
ax.set_title(f"Scaled WFS evaluation, 95% CI clustered by program "
             f"({n_struct} structures x 4 themes = 44 prompts)")
plt.tight_layout()
plt.savefig("data/wfs_big_ci.png", dpi=130)
print("\nSaved -> data/wfs_big_ci.png")
