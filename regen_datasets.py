"""Regenerate every certified dataset after the audit fixes, and PROVE the gold
labels are unchanged (only prompt TEXT should move: conj 'if', renamed entities,
new cred/skept wording). Any gold drift is a red flag and is printed."""
import json, glob, subprocess, sys, os

BUILD_ORDER = [
    "make_eval_set.py",            # poc jsonl + eval_set  (base)
    "make_eval_set_zh.py",         # -> eval_set_zh (needs eval_set)
    "make_big_wfs.py",             # -> wfs_big
    "make_ladder.py", "make_cyclesweep.py", "make_fewshot.py",
    "make_pilot.py", "make_multicycle.py",
    "make_v2_eval.py", "make_v2_full.py", "make_v3_full.py", "make_v3_ext.py",
    "make_headline.py", "make_padtest.py", "make_generalization.py",
    "make_wfs_generic.py", "make_heldout_theme2.py",
    "make_verify_set.py", "make_verify_set_zh.py",
    "make_sft_multi.py", "make_training_data.py",
]

TEST_SETS = [f for f in glob.glob("data/*.json")]


def golds(path):
    try:
        arr = json.load(open(path))
    except Exception:
        return {}
    if not (isinstance(arr, list) and arr and isinstance(arr[0], dict) and "task_id" in arr[0]):
        return {}
    return {e["task_id"]: e.get("gold") for e in arr}


before = {p: golds(p) for p in TEST_SETS}

PY = sys.executable
for script in BUILD_ORDER:
    print(f"\n$ python {script}", flush=True)
    r = subprocess.run([PY, script])
    if r.returncode != 0:
        print(f"!!! {script} FAILED (exit {r.returncode})")
        sys.exit(1)

print("\n=== GOLD-DRIFT CHECK (must be empty) ===")
drift = 0
for p in TEST_SETS:
    now = golds(p)
    old = before.get(p, {})
    common = set(old) & set(now)
    changed = [t for t in common if old[t] != now[t]]
    if changed:
        drift += len(changed)
        print(f"  {p}: {len(changed)} gold(s) changed, e.g. "
              f"{changed[0]} {old[changed[0]]}->{now[changed[0]]}")
    if set(old) != set(now):
        print(f"  {p}: task_id set changed (+{len(set(now)-set(old))} / -{len(set(old)-set(now))})")
print(f"total gold drift: {drift}")
