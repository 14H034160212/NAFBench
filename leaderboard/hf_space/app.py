"""NAF-Bench leaderboard — Hugging Face Space.

Participants upload a predictions JSONL for one subtask; the Space scores it
against a PRIVATE gold dataset (never exposed) using the JOINT metric, records
the result to a submissions dataset, and renders the public leaderboard.

Spaces secrets required:
  HF_TOKEN   — write token with access to the private gold + submissions repos.

Repos (override via env):
  GOLD_REPO         private dataset holding gold_<subtask>.json  (default qbao775/naf-bench-gold)
  SUBMISSIONS_REPO  dataset holding leaderboard.jsonl            (default qbao775/naf-bench-submissions)
"""
import json
import os
import re
import time
from collections import defaultdict

import gradio as gr
from huggingface_hub import HfApi, hf_hub_download

HF_TOKEN = os.environ.get("HF_TOKEN")
GOLD_REPO = os.environ.get("GOLD_REPO", "qbao775/naf-bench-gold")
SUBMISSIONS_REPO = os.environ.get("SUBMISSIONS_REPO", "qbao775/naf-bench-submissions")
SUBTASKS = ["8k-lite", "16k", "full"]
LB_FILE = "leaderboard.jsonl"
api = HfApi(token=HF_TOKEN)

# ---------------------------------------------------------------- scoring
SPEC = ["closed_world", "cred", "skept", "wfs"]
_A = ("a", "true", "yes", "definitely yes", "holds", "entailed")
_B = ("b", "false", "no", "definitely no", "does not hold", "not entailed")
_C = ("c", "unknown", "undefined", "cannot be determined", "cannot be determined.",
      "undetermined", "cannot determine", "indeterminate", "neither", "both", "either")


def normalize(pred):
    if pred is None:
        return None
    s = str(pred).strip().lower().strip(".)(:").strip()
    if s in ("a", "b", "c"):
        return s.upper()
    for label, keys in (("C", _C), ("B", _B), ("A", _A)):
        if s in keys:
            return label
    m = re.match(r"^\(?([abc])\)?\b", s)
    return m.group(1).upper() if m else None


def evaluate(submission, gold):
    spec_items = {t: it for t, it in gold.items() if it["cond"] in SPEC}
    by_prog = defaultdict(dict)
    per_reading = {c: [0, 0] for c in SPEC}
    valid = answered = correct = 0
    for tid, it in spec_items.items():
        raw = submission.get(tid)
        norm = normalize(raw)
        answered += raw is not None
        valid += norm is not None
        ok = norm is not None and norm == str(it["gold"]).upper()
        correct += ok
        per_reading[it["cond"]][1] += 1
        per_reading[it["cond"]][0] += ok
        by_prog[it["rec_id"]][it["cond"]] = ok
    joint = sum(1 for d in by_prog.values() if all(d.get(c) for c in SPEC))
    n_prog = len(by_prog)
    tot = len(spec_items)

    def pct(a, b):
        return round(100.0 * a / b, 1) if b else 0.0
    return {
        "joint_accuracy": pct(joint, n_prog),
        "per_prompt_accuracy": pct(correct, tot),
        "coverage": pct(answered, tot),
        "format_valid_rate": pct(valid, answered) if answered else 0.0,
        "sldnf": pct(*per_reading["closed_world"]),
        "cred": pct(*per_reading["cred"]),
        "skept": pct(*per_reading["skept"]),
        "wfs": pct(*per_reading["wfs"]),
        "n_programs": n_prog,
    }


# ---------------------------------------------------------------- data io
_gold_cache = {}


def load_gold(subtask):
    if subtask not in _gold_cache:
        p = hf_hub_download(GOLD_REPO, f"gold_{subtask}.json", repo_type="dataset",
                            token=HF_TOKEN)
        _gold_cache[subtask] = json.load(open(p))
    return _gold_cache[subtask]


def load_leaderboard():
    try:
        p = hf_hub_download(SUBMISSIONS_REPO, LB_FILE, repo_type="dataset",
                            token=HF_TOKEN, force_download=True)
        return [json.loads(l) for l in open(p) if l.strip()]
    except Exception:
        return []


def append_leaderboard(row):
    rows = load_leaderboard()
    rows.append(row)
    body = "\n".join(json.dumps(r) for r in rows) + "\n"
    api.upload_file(path_or_fileobj=body.encode(), path_in_repo=LB_FILE,
                    repo_id=SUBMISSIONS_REPO, repo_type="dataset",
                    commit_message=f"submission: {row['team']} / {row['subtask']}")


def best_per_team(rows, subtask):
    best = {}
    for r in rows:
        if r["subtask"] != subtask:
            continue
        k = r["team"]
        if k not in best or r["joint_accuracy"] > best[k]["joint_accuracy"]:
            best[k] = r
    ranked = sorted(best.values(), key=lambda r: -r["joint_accuracy"])
    return [[i + 1, r["team"], r["joint_accuracy"], r["per_prompt_accuracy"],
             r.get("sldnf"), r.get("cred"), r.get("skept"), r.get("wfs")]
            for i, r in enumerate(ranked)]


LB_HEADERS = ["#", "team", "JOINT %", "per-prompt %", "sldnf", "cred", "skept", "wfs"]


# ---------------------------------------------------------------- app logic
def do_submit(team, subtask, fileobj):
    team = (team or "").strip()
    if not team:
        return "Please enter a team name.", None
    if fileobj is None:
        return "Please upload a predictions .jsonl file.", None
    try:
        preds = {}
        for l in open(fileobj.name):
            l = l.strip()
            if l:
                o = json.loads(l)
                preds[o["id"]] = o.get("prediction")
    except Exception as e:
        return f"Could not parse submission (need JSONL of {{id, prediction}}): {e}", None
    try:
        gold = load_gold(subtask)
    except Exception as e:
        return f"Gold not available for {subtask} yet: {e}", None
    m = evaluate(preds, gold)
    row = {"team": team, "subtask": subtask, "time": int(time.time()), **m}
    try:
        append_leaderboard(row)
    except Exception as e:
        return (f"Scored (JOINT {m['joint_accuracy']}%) but could not save: {e}",
                refresh(subtask))
    msg = (f"✅ {team} on **{subtask}**: JOINT **{m['joint_accuracy']}%** | "
           f"per-prompt {m['per_prompt_accuracy']}% | coverage {m['coverage']}% "
           f"(sldnf {m['sldnf']} / cred {m['cred']} / skept {m['skept']} / wfs {m['wfs']})")
    return msg, best_per_team(load_leaderboard(), subtask)


def refresh(subtask):
    return best_per_team(load_leaderboard(), subtask)


with gr.Blocks(title="NAF-Bench Leaderboard") as demo:
    gr.Markdown(
        "# NAF-Bench Leaderboard\n"
        "Does an LLM follow a **specified** negation semantics (SLDNF / well-founded / "
        "credulous / skeptical stable-model)? Primary metric: **JOINT accuracy** — a "
        "program counts only if all four specified readings are answered correctly.\n\n"
        "**Submit** a JSONL, one line per prompt: `{\"id\": \"<prompt id>\", "
        "\"prediction\": \"A|B|C\"}`. Get the input prompts from the public dataset. "
        "Three subtasks by context budget: `8k-lite` ⊂ `16k` ⊂ `full`.")
    with gr.Row():
        team = gr.Textbox(label="Team / model name")
        subtask = gr.Dropdown(SUBTASKS, value="8k-lite", label="Subtask")
    fileobj = gr.File(label="predictions.jsonl", file_types=[".jsonl", ".json"])
    submit = gr.Button("Score & submit", variant="primary")
    status = gr.Markdown()
    table = gr.Dataframe(headers=LB_HEADERS, label="Leaderboard", interactive=False)
    submit.click(do_submit, [team, subtask, fileobj], [status, table])
    subtask.change(refresh, subtask, table)
    demo.load(refresh, subtask, table)

if __name__ == "__main__":
    demo.launch()
