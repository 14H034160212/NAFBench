"""Production-scale rule-order robustness. Scores from the SAVED raw outputs with
the reasoning-model extractor (rescues DeepSeek; no-op for the others). Reports
per model: accuracy, and ORDER-SENSITIVITY = fraction of (program,condition)
groups whose answer is not constant across the K rule orders."""
import json, glob, os
from collections import defaultdict
from nafbench.answer import parse_answer_reasoning

ev = {e["task_id"]: e for e in json.load(open("data/reorder_prod_set.json"))}
groups = defaultdict(list)
for t, e in ev.items():
    groups[e["rec_id"]].append(t)
K = len(next(iter(groups.values())))
print(f"production reorder: {len(ev)} prompts, {len(groups)} (program,cond) groups, "
      f"{K} orderings each\n")
print(f"{'model':22s} coverage  accuracy   order-sensitivity (non-constant groups)")
for raw in sorted(glob.glob("data/reorder_prod_answers/*.raw.json")):
    model = os.path.basename(raw)[:-9]
    r = json.load(open(raw))
    ans = {t: parse_answer_reasoning(r.get(t, ""), query="q") for t in ev}
    parsed = sum(v is not None for v in ans.values())
    correct = tot = 0
    nonconst = ngroups = 0
    for rid, tids in groups.items():
        vals = [ans[t] for t in tids]
        nn = [v for v in vals if v is not None]
        gold = ev[tids[0]]["gold"]
        correct += sum(v == gold for v in nn); tot += len(nn)
        if len(nn) >= 2:                     # only judge groups with >=2 answers
            ngroups += 1
            if len(set(nn)) > 1:
                nonconst += 1
    acc = f"{correct/tot:.0%}" if tot else "--"
    os_rate = f"{nonconst}/{ngroups} = {nonconst/ngroups:.0%}" if ngroups else "--"
    print(f"{model:22s} {parsed}/{len(ev)}  {acc:>6}    {os_rate}")
