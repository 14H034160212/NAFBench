"""Force re-run every (dir, model) on the REGENERATED sets after the audit fixes.

Unlike backfill_tokens.py this does NOT skip files with tokens -- the prompts
themselves changed (conj 'if', renamed entities, new cred/skept wording), so
every affected answer file must be recomputed. Claude/Opus files are produced by
a subagent and are skipped here.

Usage:
  python rerun_all.py --provider ollama          # free/local
  python rerun_all.py --provider openai           # paid (.env key)
  python rerun_all.py --provider openai --only gpt-4o-mini,gpt-4.1   # subset
"""
import argparse, glob, json, os, subprocess

# outdir -> (eval-set file, temperature)
DIR_SET = {
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
    "data/gen_answers": ("data/generalization.json", 0.0),
    "data/hl_run1": ("data/headline.json", 0.7),
    "data/hl_run2": ("data/headline.json", 0.7),
    "data/hl_run3": ("data/headline.json", 0.7),
}
REVERSE = {"qwen2.5-coder_32b": "qwen2.5-coder:32b", "llama3_8b": "llama3:8b",
           "deepseek-r1_32b": "deepseek-r1:32b"}


def load_env():
    env = dict(os.environ)
    if os.path.exists(".env"):
        for line in open(".env"):
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.strip().split("=", 1)
                env[k] = v
    return env


ap = argparse.ArgumentParser()
ap.add_argument("--provider", choices=["ollama", "openai"], required=True)
ap.add_argument("--only", default=None, help="comma-separated model subset")
args = ap.parse_args()
env = load_env() if args.provider == "openai" else dict(os.environ)
only = set(args.only.split(",")) if args.only else None

jobs = []
for outdir, (setf, temp) in DIR_SET.items():
    for jf in sorted(glob.glob(f"{outdir}/*.json")):
        if jf.endswith(".raw.json"):
            continue
        safe = os.path.basename(jf)[:-5]
        model = REVERSE.get(safe, safe)
        if model.startswith("claude"):
            continue
        prov = "openai" if model.startswith("gpt") else "ollama"
        if prov != args.provider:
            continue
        if only and model not in only:
            continue
        jobs.append((outdir, setf, temp, model, prov))

print(f"[{args.provider}] {len(jobs)} (dir,model) jobs to re-run", flush=True)
for i, (outdir, setf, temp, model, prov) in enumerate(jobs, 1):
    print(f"\n>>> [{i}/{len(jobs)}] {outdir} {model} (set {setf}, T={temp})", flush=True)
    cmd = ["python3", "run_eval.py", "--provider", prov, "--models", model,
           "--set", setf, "--outdir", outdir, "--temperature", str(temp),
           "--workers", "6" if prov == "openai" else "3"]
    subprocess.run(cmd, env=env)
print(f"\n[{args.provider}] done.")
