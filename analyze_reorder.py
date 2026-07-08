"""Rule-order robustness. Since gold is invariant across orderings of a
(bin, condition) group, we report per model:
  - accuracy over all prompts;
  - ORDER-SENSITIVITY: fraction of (bin,cond) groups where the model's answer is
    NOT constant across the K orderings (i.e. rule order flipped its answer);
  - the worst within-group spread (max-min accuracy across orderings).
A robust model has near-zero order-sensitivity.
"""
import json, glob
from collections import defaultdict

ev = {e["task_id"]: e for e in json.load(open("data/reorder_set.json"))}
groups = defaultdict(list)          # rec_id -> task_ids
for t, e in ev.items():
    groups[e["rec_id"]].append(t)

print(f"reorder set: {len(ev)} prompts, {len(groups)} (bin,cond) groups, "
      f"{len(next(iter(groups.values())))} orderings each\n")
print(f"{'model':22s} accuracy   order-sensitivity (groups w/ non-constant answer)")
for f in sorted(glob.glob("data/reorder_answers/*.json")):
    if f.endswith("raw.json"):
        continue
    d = json.load(open(f)); a = d["answers"]; m = d["model"]
    correct = tot = 0
    nonconst = 0; examples = []
    for rid, tids in groups.items():
        ans = [a.get(t) for t in tids]
        gold = ev[tids[0]]["gold"]
        correct += sum(x == gold for x in ans); tot += len(ans)
        if len(set(ans)) > 1:          # answer changed with rule order
            nonconst += 1
            examples.append((rid, [f"{ev[t]['order_id']}:{a.get(t)}" for t in tids]))
    print(f"{m:22s} {correct}/{tot} = {correct/tot:.0%}   "
          f"{nonconst}/{len(groups)} = {nonconst/len(groups):.0%}")
    for rid, ex in examples[:3]:
        print(f"    flipped: {rid}  {ex}")
