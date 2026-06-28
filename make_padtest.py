"""Length-matched padding test: separate STRUCTURE from LENGTH.

For each cyclic bin and condition, three matched variants:
  low_nat  : depth=2, eff_width=min            (simple, short)
  low_pad  : same simple instance, padded with inert filler to the HARD length
  high_nat : depth=16, eff_width=16            (complex, long)

Comparisons:
  length effect   = low_pad  vs low_nat   (same structure, longer)
  structure effect= high_nat vs low_pad   (same length, more structure)
"""
import json
from nafbench.instances import build_by_effwidth
from nafbench import solvers as S
from nafbench import verbalize_v2 as V2
from nafbench import metrics as MET

CYCLE = {"even_one_sided": 4, "odd": 3, "even_both_sided": 4}
CONDS = ["closed_world", "cred", "skept", "wfs"]
THEME = 0

items = []
for b, cyc in CYCLE.items():
    cmin = cyc
    low = build_by_effwidth(2, cmin, b, cycle_len=cyc)
    high = build_by_effwidth(16, 16, b, cycle_len=cyc)
    cert_low = S.certify_full(low, "q"); cert_high = S.certify_full(high, "q")
    for c in CONDS:
        p_high = V2.build_prompt(high, c, THEME)
        tgt = MET.length_metrics(p_high)["tokens"]
        variants = {
            "low_nat":  V2.build_prompt(low, c, THEME),
            "low_pad":  V2.build_prompt(low, c, THEME, pad_to_tokens=tgt),
            "high_nat": p_high,
        }
        # low and high share the same bin signature => same gold per condition
        gold_low = V2.gold_for(cert_low["labels"], c)
        gold_high = V2.gold_for(cert_high["labels"], c)
        for var, prompt in variants.items():
            gold = gold_high if var == "high_nat" else gold_low
            items.append({
                "task_id": f"pad-{b}-{var}::{c}", "rec_id": f"pad-{b}-{var}",
                "cond": c, "divergence_bin": b, "variant": var,
                "structure": "high" if var == "high_nat" else "low",
                "padded": var == "low_pad",
                "gold": gold, "length": MET.length_metrics(prompt), "prompt": prompt,
            })

json.dump(items, open("data/padtest.json", "w"), indent=1)
# verify length matching
import statistics as st
for b in CYCLE:
    ln = {v: [e["length"]["tokens"] for e in items if e["divergence_bin"] == b and e["variant"] == v]
          for v in ["low_nat", "low_pad", "high_nat"]}
    print(f"{b:16s} tokens  low_nat~{int(st.mean(ln['low_nat']))}  "
          f"low_pad~{int(st.mean(ln['low_pad']))}  high_nat~{int(st.mean(ln['high_nat']))}")
print(f"{len(items)} prompts")
