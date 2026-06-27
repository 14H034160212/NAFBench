"""Build a v2 dataset grid (bin x depth x width) with 4 labels + solver metrics,
and plot solver hardness vs the depth/width knobs."""
import json
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from nafbench.instances import build_instance, BIN_SIGNATURE
from nafbench import solvers as S
from nafbench import verbalize as V  # reuse? v2 verbalization is future work; store formal only

BINS = ["control", "even_one_sided", "odd", "even_both_sided"]
DEPTHS = [0, 1, 2, 4, 8]
WIDTHS = [0, 2, 4, 8]

records = []
for b in BINS:
    for d in DEPTHS:
        for w in WIDTHS:
            prog = build_instance(d, w, b)
            r = S.certify_full(prog, "q")
            records.append({
                "id": f"v2-{b}-d{d}-w{w}",
                "divergence_bin": b, "depth": d, "width": w,
                "cycle_len": prog.meta["cycle_len"],
                "program": prog.pretty(), "query": "q",
                "labels": r["labels"], "expected": list(BIN_SIGNATURE[b]),
                "n_distinct_labels": r["n_distinct_labels"],
                "metrics": r["metrics"],
            })
with open("data/nafbench_v2.jsonl", "w") as f:
    for r in records:
        f.write(json.dumps(r) + "\n")
print(f"Wrote {len(records)} v2 records to data/nafbench_v2.jsonl")
from collections import Counter
print("divergence-label counts (n distinct of 4):",
      dict(Counter(r["n_distinct_labels"] for r in records)))

# hardness vs width (averaged over bins) at depth 0, and vs depth at width 0
def infer(b, d, w):
    return S.certify_full(build_instance(d, w, b), "q")["metrics"]["prolog_inferences"]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6))
for b in BINS:
    ax1.plot(WIDTHS, [infer(b, 2, w) for w in WIDTHS], marker="o", label=b)
    ax2.plot(DEPTHS, [infer(b, d, 2) for d in DEPTHS], marker="s", label=b)
ax1.set_xlabel("width (shared subgoals)"); ax1.set_ylabel("Prolog inferences (statistics/2)")
ax1.set_title("Solver hardness vs WIDTH (depth=2)"); ax1.grid(alpha=0.3); ax1.legend(fontsize=8)
ax2.set_xlabel("depth (rule-chain length)"); ax2.set_ylabel("Prolog inferences")
ax2.set_title("Solver hardness vs DEPTH (width=2)"); ax2.grid(alpha=0.3); ax2.legend(fontsize=8)
plt.tight_layout(); plt.savefig("data/v2_hardness.png", dpi=130)
print("Saved -> data/v2_hardness.png")
