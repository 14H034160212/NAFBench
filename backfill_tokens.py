"""Backfill completion-token counts into evaluation outputs.

Supports three families:
    1) run_eval outputs in data/*_answers and data/hl_run*
    2) local HF outputs in data/local_answers
    3) translate-then-solve outputs in data/t2s_answers

Resumable: files that already contain non-empty completion_tokens are skipped.

Usage:
    python backfill_tokens.py --provider openai --scope run_eval
    python backfill_tokens.py --provider ollama --scope run_eval
    python backfill_tokens.py --scope local
    python backfill_tokens.py --provider openai --scope t2s
    python backfill_tokens.py --provider ollama --scope t2s
"""
import argparse
import glob
import json
import os
import subprocess

# outdir -> (eval-set file, temperature)
RUN_EVAL_MAP = {
    "data/auto_answers": ("data/eval_set.json", 0.0),
    "data/big_answers": ("data/wfs_big.json", 0.0),
    "data/cyc_answers": ("data/cyclesweep.json", 0.0),
    "data/ext_answers": ("data/v3_ext.json", 0.0),
    "data/fs_answers": ("data/fewshot.json", 0.0),
    "data/ladder_answers": ("data/ladder_set.json", 0.0),
    "data/mc_answers": ("data/multicycle.json", 0.0),
    "data/pad_answers": ("data/padtest.json", 0.0),
    "data/pilot_answers": ("data/pilot.json", 0.0),
    "data/v2_answers": ("data/v2_eval.json", 0.0),
    "data/v2_full_answers": ("data/v2_full.json", 0.0),
    "data/v3_answers": ("data/v3_full.json", 0.0),
    "data/verify_answers": ("data/verify_set.json", 0.0),
    "data/verify_zh_answers": ("data/verify_set_zh.json", 0.0),
    "data/zh_answers": ("data/eval_set_zh.json", 0.0),
    "data/hl_run1": ("data/headline.json", 0.7),
    "data/hl_run2": ("data/headline.json", 0.7),
    "data/hl_run3": ("data/headline.json", 0.7),
}
REVERSE = {"qwen2.5-coder_32b": "qwen2.5-coder:32b", "llama3_8b": "llama3:8b",
           "deepseek-r1_32b": "deepseek-r1:32b"}


def has_tokens(path):
    d = json.load(open(path))
    ct = d.get("completion_tokens")
    return isinstance(ct, dict) and len(ct) > 0


def run(cmd, env=None):
    print("$", " ".join(cmd), flush=True)
    return subprocess.run(cmd, env=env)


def load_env_for_openai():
    env = dict(os.environ)
    if os.path.exists(".env"):
        for line in open(".env"):
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.strip().split("=", 1)
                env[k] = v
    return env


def backfill_run_eval(provider):
    env = load_env_for_openai() if provider == "openai" else dict(os.environ)
    done = skipped = 0
    for outdir, (setf, temp) in RUN_EVAL_MAP.items():
        for jf in sorted(glob.glob(f"{outdir}/*.json")):
            if jf.endswith(".raw.json"):
                continue
            safe = os.path.basename(jf)[:-5]
            model = REVERSE.get(safe, safe)
            if model.startswith("claude"):
                continue
            prov = "openai" if model.startswith("gpt") else "ollama"
            if prov != provider:
                continue
            if has_tokens(jf):
                skipped += 1
                continue
            print(f">>> backfill run_eval {outdir} {model} (set {setf}, T={temp})", flush=True)
            cmd = [
                "python3", "run_eval.py",
                "--provider", prov,
                "--models", model,
                "--set", setf,
                "--outdir", outdir,
                "--temperature", str(temp),
                "--workers", "6" if prov == "openai" else "3",
            ]
            run(cmd, env=env)
            done += 1
    print(f"[run_eval:{provider}] backfilled {done}, skipped {skipped}")


def collect_sets():
    out = {}
    for sf in glob.glob("data/*.json"):
        try:
            arr = json.load(open(sf))
        except Exception:
            continue
        if isinstance(arr, list) and arr and isinstance(arr[0], dict) and "task_id" in arr[0]:
            out[sf] = {e["task_id"] for e in arr}
    return out


def infer_set_from_answer_keys(keys, sets_map):
    for sf, tids in sets_map.items():
        if keys == tids:
            return sf
    return None


def backfill_local():
    sets_map = collect_sets()
    done = skipped = unresolved = 0
    for jf in sorted(glob.glob("data/local_answers/*.json")):
        if has_tokens(jf):
            skipped += 1
            continue
        d = json.load(open(jf))
        setf = infer_set_from_answer_keys(set(d.get("answers", {}).keys()), sets_map)
        if not setf:
            print(f"!!! cannot infer set for {jf}; skipping", flush=True)
            unresolved += 1
            continue
        model = d["model"]
        tag = d["tag"]
        adapter = d.get("adapter")
        print(f">>> backfill local {tag} ({model}, set {setf})", flush=True)
        cmd = [
            "python3", "eval_local.py",
            "--model", model,
            "--set", setf,
            "--tag", tag,
        ]
        if adapter:
            cmd += ["--adapter", adapter]
        run(cmd, env=dict(os.environ))
        done += 1
    print(f"[local] backfilled {done}, skipped {skipped}, unresolved {unresolved}")


def backfill_t2s(provider):
    env = load_env_for_openai() if provider == "openai" else dict(os.environ)
    done = skipped = 0
    for jf in sorted(glob.glob("data/t2s_answers/*.json")):
        d = json.load(open(jf))
        model = d.get("model")
        if not model or model.startswith("claude"):
            continue
        prov = "openai" if model.startswith("gpt") else "ollama"
        if prov != provider:
            continue
        if has_tokens(jf):
            skipped += 1
            continue
        print(f">>> backfill t2s {model} ({provider})", flush=True)
        cmd = [
            "python3", "translate_solve.py",
            "--provider", provider,
            "--models", model,
            "--workers", "6" if provider == "openai" else "3",
        ]
        run(cmd, env=env)
        done += 1
    print(f"[t2s:{provider}] backfilled {done}, skipped {skipped}")

ap = argparse.ArgumentParser()
ap.add_argument("--provider", choices=["ollama", "openai"], default=None)
ap.add_argument("--scope", choices=["run_eval", "local", "t2s", "all"], default="all")
args = ap.parse_args()

if args.scope in ("run_eval", "t2s") and not args.provider:
    raise SystemExit("--provider is required for scope run_eval or t2s")

if args.scope == "run_eval":
    backfill_run_eval(args.provider)
elif args.scope == "local":
    backfill_local()
elif args.scope == "t2s":
    backfill_t2s(args.provider)
else:
    for provider in ("openai", "ollama"):
        backfill_run_eval(provider)
    backfill_local()
    for provider in ("openai", "ollama"):
        backfill_t2s(provider)
