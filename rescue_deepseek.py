"""Rescue DeepSeek-R1's production answers by re-parsing the SAVED raw outputs
with the reasoning-model extractor (no re-run). Writes the updated answers file
and reports coverage before/after. Validation: on items the STRICT parser
already resolved, the reasoning extractor must agree (it delegates to it)."""
import json, sys
from nafbench.answer import parse_answer, parse_answer_reasoning

RUN = "data/production_answers/run1"
raw = json.load(open(f"{RUN}/deepseek-r1_32b.raw.json"))
d = json.load(open(f"{RUN}/deepseek-r1_32b.json"))
ev = {e["task_id"]: e for e in json.load(open("data/production_set.json"))}

before = sum(1 for v in d["answers"].values() if v is not None)
disagree = 0
newans = {}
for t, txt in raw.items():
    q = ev[t]["program"].split(":-")[0].strip() if t in ev else "q"
    strict = parse_answer(txt)
    resc = parse_answer_reasoning(txt, query="q")
    if strict is not None and resc != strict:      # validation
        disagree += 1
    newans[t] = resc
# keep any task_ids not in raw (shouldn't happen)
for t in d["answers"]:
    newans.setdefault(t, d["answers"][t])

after = sum(1 for v in newans.values() if v is not None)
print(f"coverage: {before}/600 -> {after}/600  (rescued {after - before})")
print(f"validation: reasoning extractor disagreed with strict parser on "
      f"{disagree} already-parsed items (should be 0)")

if disagree == 0 and "--write" in sys.argv:
    d["answers"] = newans
    d["rescued_with"] = "parse_answer_reasoning"
    json.dump(d, open(f"{RUN}/deepseek-r1_32b.json", "w"), indent=1)
    print("wrote rescued answers.")
elif disagree:
    print("NOT writing: validation failed.")
else:
    print("(dry run; pass --write to save)")
