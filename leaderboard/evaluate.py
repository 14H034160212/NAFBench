"""NAF-Bench leaderboard evaluator.

Scores a submission against a (hidden) gold file and emits leaderboard metrics.
Designed to run as an EvalAI evaluation script, but usable stand-alone:

    python evaluate.py --submission sub.jsonl --gold data/test_gold.json

Submission format: JSONL, one object per line
    {"id": "<task_id>", "prediction": "<A|B|C or true/false/unknown/...>"}

Gold format: JSON, {task_id: {"gold": "A|B|C", "cond": ..., "divergence_bin": ...,
"rec_id": ...}}. The "none" (no-semantics) condition has gold=null and is used
only for the default-correspondence diagnostic, never scored.

Primary metric: JOINT accuracy --- the fraction of PROGRAMS for which the model
answers ALL FOUR specified readings (SLDNF, WFS, credulous, skeptical) correctly.
A program counts only if every one of its four specified-reading prompts is
answered and correct; this removes credit for lucky/vacuous coincidences that a
per-prompt average would reward.
"""
import argparse
import json
import re
from collections import defaultdict

SPEC = ["closed_world", "cred", "skept", "wfs"]

# ---- answer normalization -------------------------------------------------
# Accept the multiple-choice letters or common free-form phrasings and map to
# the A/B/C label space. Anything unrecognized -> None (counts as wrong, and
# lowers the format-valid rate).
_A = ("a", "true", "yes", "definitely yes", "holds", "entailed")
_B = ("b", "false", "no", "definitely no", "does not hold", "not entailed")
_C = ("c", "unknown", "undefined", "cannot be determined", "cannot be determined.",
      "undetermined", "cannot determine", "indeterminate", "neither", "both",
      "either")


def normalize(pred):
    """Map a raw prediction string to 'A'/'B'/'C', or None if unrecognized."""
    if pred is None:
        return None
    s = str(pred).strip().lower().strip(".)(:").strip()
    if s in ("a", "b", "c"):
        return s.upper()
    # longest-match phrasing
    for label, keys in (("C", _C), ("B", _B), ("A", _A)):
        if s in keys:
            return label
    # fall back: a leading bare letter like "a. definitely yes"
    m = re.match(r"^\(?([abc])\)?\b", s)
    if m:
        return m.group(1).upper()
    return None


def load_submission(path):
    preds = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            preds[obj["id"]] = obj.get("prediction")
    return preds


def evaluate(submission, gold):
    """Return a metrics dict. `gold` maps task_id -> item; `submission` maps
    task_id -> raw prediction."""
    spec_items = {t: it for t, it in gold.items() if it["cond"] in SPEC}
    total_required = len(spec_items)

    # per program: which spec readings are correct
    by_prog = defaultdict(dict)         # rec_id -> {cond: bool}
    prog_bin = {}
    per_reading = {c: [0, 0] for c in SPEC}
    per_bin_prompt = defaultdict(lambda: [0, 0])
    valid = answered = correct = 0

    for tid, it in spec_items.items():
        raw = submission.get(tid)
        norm = normalize(raw)
        if raw is not None:
            answered += 1
        if norm is not None:
            valid += 1
        ok = norm is not None and norm == str(it["gold"]).upper()
        correct += ok
        c, b = it["cond"], it["divergence_bin"]
        per_reading[c][1] += 1
        per_reading[c][0] += ok
        per_bin_prompt[b][1] += 1
        per_bin_prompt[b][0] += ok
        by_prog[it["rec_id"]][c] = ok
        prog_bin[it["rec_id"]] = b

    # JOINT: a program is solved iff all four spec readings present AND correct
    joint_by_bin = defaultdict(lambda: [0, 0])
    joint_solved = 0
    for rid, d in by_prog.items():
        complete = all(c in d for c in SPEC)
        solved = complete and all(d[c] for c in SPEC)
        joint_solved += solved
        jb = joint_by_bin[prog_bin[rid]]
        jb[1] += 1
        jb[0] += solved
    n_prog = len(by_prog)

    def pct(a, b):
        return round(100.0 * a / b, 1) if b else 0.0

    metrics = {
        # PRIMARY
        "joint_accuracy": pct(joint_solved, n_prog),
        # diagnostics
        "per_prompt_accuracy": pct(correct, total_required),
        "coverage": pct(answered, total_required),
        "format_valid_rate": pct(valid, answered) if answered else 0.0,
        "sldnf_accuracy": pct(per_reading["closed_world"][0], per_reading["closed_world"][1]),
        "cred_accuracy": pct(per_reading["cred"][0], per_reading["cred"][1]),
        "skept_accuracy": pct(per_reading["skept"][0], per_reading["skept"][1]),
        "wfs_accuracy": pct(per_reading["wfs"][0], per_reading["wfs"][1]),
        "joint_control": pct(*joint_by_bin["control"]),
        "joint_even_one_sided": pct(*joint_by_bin["even_one_sided"]),
        "joint_odd": pct(*joint_by_bin["odd"]),
        "joint_even_both_sided": pct(*joint_by_bin["even_both_sided"]),
        "n_programs": n_prog,
        "n_prompts_scored": total_required,
    }
    return metrics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--submission", required=True, help="JSONL {id, prediction}")
    ap.add_argument("--gold", required=True, help="JSON {task_id: item}")
    ap.add_argument("--out", default=None, help="write metrics JSON here")
    args = ap.parse_args()

    gold = json.load(open(args.gold))
    submission = load_submission(args.submission)
    metrics = evaluate(submission, gold)

    # EvalAI-style result envelope; primary metric first / used for ranking
    result = {"result": [{"test_split": metrics}],
              "submission_result": metrics}
    out = json.dumps(result, indent=2)
    if args.out:
        open(args.out, "w").write(out)
    print(out)


if __name__ == "__main__":
    main()
