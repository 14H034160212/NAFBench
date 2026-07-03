"""Re-run only the poc-derived sets after build_dataset.py was added to the regen
(the conj/entity fixes reached poc late). Covers eval_set, eval_set_zh,
verify_set, verify_set_zh, and translate-then-solve; both providers."""
import os, subprocess, glob, sys

DIRS = {
    "data/auto_answers": ("data/eval_set.json", 0.0),
    "data/zh_answers": ("data/eval_set_zh.json", 0.0),
    "data/verify_answers": ("data/verify_set.json", 0.0),
    "data/verify_zh_answers": ("data/verify_set_zh.json", 0.0),
}
REVERSE = {"qwen2.5-coder_32b": "qwen2.5-coder:32b", "llama3_8b": "llama3:8b",
           "deepseek-r1_32b": "deepseek-r1:32b"}


def load_env():
    env = dict(os.environ)
    if os.path.exists(".env"):
        for line in open(".env"):
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.strip().split("=", 1); env[k] = v
    return env


prov = sys.argv[1]  # ollama | openai
env = load_env() if prov == "openai" else dict(os.environ)

for outdir, (setf, temp) in DIRS.items():
    for jf in sorted(glob.glob(f"{outdir}/*.json")):
        if jf.endswith(".raw.json"):
            continue
        safe = os.path.basename(jf)[:-5]
        model = REVERSE.get(safe, safe)
        if model.startswith("claude"):
            continue
        p = "openai" if model.startswith("gpt") else "ollama"
        if p != prov:
            continue
        print(f">>> {outdir} {model} ({setf})", flush=True)
        subprocess.run(["python3", "run_eval.py", "--provider", p, "--models", model,
                        "--set", setf, "--outdir", outdir, "--temperature", str(temp),
                        "--workers", "6" if p == "openai" else "3"], env=env)

# translate-then-solve on the fresh poc
for jf in sorted(glob.glob("data/t2s_answers/*.json")):
    if jf.endswith(".raw.json"):
        continue
    safe = os.path.basename(jf)[:-5]
    model = REVERSE.get(safe, safe)
    if model.startswith("claude"):
        continue
    p = "openai" if model.startswith("gpt") else "ollama"
    if p != prov:
        continue
    print(f">>> t2s {model}", flush=True)
    subprocess.run(["python3", "translate_solve.py", "--provider", p, "--models", model,
                    "--workers", "6" if p == "openai" else "3"], env=env)
print(f"[{prov}] pocfix done.")
