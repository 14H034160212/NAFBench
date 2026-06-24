"""Build the NAF-Bench PoC dataset: generate -> certify -> verbalize -> JSON.

Each output record contains the formal program, the certified label under
every semantics, the semantics distance, and -- for each semantics condition
-- the natural-language prompt and the gold 3-way answer.
"""
import json
import os
from collections import Counter

from nafbench.generator import generate_dataset
from nafbench import solvers as S
from nafbench import verbalize as V

OUT = "data/nafbench_poc.jsonl"
CONDITIONS = ["none", "closed_world", "stable", "wfs"]


def main():
    os.makedirs("data", exist_ok=True)
    progs = generate_dataset(seed=0)
    records = []
    dist_hist = Counter()
    for idx, prog in enumerate(progs):
        q = prog.meta["query"]
        cert = S.certify(prog, q)
        dist_hist[cert["semantics_distance"]] += 1
        v = V.verbalize(prog)
        # gold answer per semantics condition
        golds = {}
        for cond in CONDITIONS:
            solver = V.SEMANTICS_TO_SOLVER[cond]
            golds[cond] = V.label_to_gold(cert["labels"][solver])
        prompts = {cond: V.build_prompt(prog, cond) for cond in CONDITIONS}
        records.append({
            "id": f"naf-{idx:03d}",
            "family": prog.meta["family"],
            "axes": {
                "rule_depth": prog.meta["rule_depth"],
                "negation_depth": prog.meta["negation_depth"],
                "cycle": prog.meta["cycle"],
                "stratified": prog.meta["stratified"],
            },
            "program": prog.pretty(),
            "query_atom": q,
            "certified_labels": cert["labels"],
            "n_stable_models": cert["n_stable_models"],
            "semantics_distance": cert["semantics_distance"],
            "divergent": cert["semantics_distance"] >= 2,
            "premises_nl": v["premises"],
            "query_nl": v["query"],
            "gold_answer": golds,
            "prompt": prompts,
        })
    with open(OUT, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    n_div = sum(r["divergent"] for r in records)
    print(f"Wrote {len(records)} records to {OUT}")
    print(f"Semantics-distance histogram: {dict(dist_hist)}")
    print(f"Divergent items (distance>=2): {n_div}")
    # how often does each pair of semantics disagree?
    pairs = Counter()
    for r in records:
        L = r["certified_labels"]
        for a, b in [("stable", "wfs"), ("stable", "sldnf"), ("wfs", "sldnf")]:
            la = L[a] if L[a] != "loop" else "undefined"
            lb = L[b] if L[b] != "loop" else "undefined"
            if la != lb:
                pairs[f"{a} vs {b}"] += 1
    print("Pairwise disagreement counts:", dict(pairs))


if __name__ == "__main__":
    main()
