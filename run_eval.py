"""Automated NAF-Bench evaluation harness.

Drives any OpenAI-compatible endpoint, so the same code evaluates:
  * local open-source models via ollama  (base_url=http://localhost:11434/v1)
  * OpenAI models                          (base_url=default, key from env)

Usage:
  python run_eval.py --models deepseek-r1:32b qwen2.5-coder:32b llama3:8b
  OPENAI_API_KEY=... python run_eval.py --provider openai --models gpt-4o-mini

Answers are written to data/auto_answers/<safe_model_name>.json and never
contain secrets. The API key is read ONLY from the environment.
"""
import argparse
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

ANSWER_RE = re.compile(r"ANSWER:\s*([ABC])", re.IGNORECASE)
SYSTEM = ("You are a careful reasoning test subject. Solve the problem using "
          "only your own reasoning. Do not use external tools. Reason step by "
          "step, then end with exactly one line 'ANSWER: X' where X is A, B, or C.")


def parse_answer(text: str):
    if text is None:
        return None
    # drop <think>...</think> (deepseek-r1) so we read the post-thought answer
    visible = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    cands = ANSWER_RE.findall(visible) or ANSWER_RE.findall(text)
    if cands:
        return cands[-1].upper()
    # fallback: last standalone A/B/C token
    toks = re.findall(r"\b([ABC])\b", visible)
    return toks[-1].upper() if toks else None


def _is_reasoning(model):
    return any(model.startswith(p) for p in ("gpt-5", "o1", "o3", "o4"))


def ask(client, model, prompt, max_retries=3, max_tokens=8192, temperature=0.0):
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt}]
    for attempt in range(max_retries):
        try:
            if _is_reasoning(model):
                # reasoning models: no temperature, use max_completion_tokens,
                # need ample budget for hidden reasoning + the final answer
                r = client.chat.completions.create(
                    model=model, messages=msgs, max_completion_tokens=16384)
            else:
                r = client.chat.completions.create(
                    model=model, messages=msgs, temperature=temperature, max_tokens=max_tokens)
            content = r.choices[0].message.content
            return content, parse_answer(content)
        except Exception as e:  # noqa
            if attempt == max_retries - 1:
                return f"<error: {e}>", None
            time.sleep(2 * (attempt + 1))
    return None, None


def run_model(model, eval_items, base_url, api_key, workers, temperature=0.0):
    client = OpenAI(base_url=base_url, api_key=api_key)
    results = {}
    raw = {}

    def task(item):
        content, ans = ask(client, model, item["prompt"], temperature=temperature)
        return item["task_id"], ans, content

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(task, it) for it in eval_items]
        for i, f in enumerate(as_completed(futs), 1):
            tid, ans, content = f.result()
            results[tid] = ans
            raw[tid] = content
            print(f"  [{model}] {i}/{len(eval_items)} {tid} -> {ans}", flush=True)
    dt = time.time() - t0
    print(f"  [{model}] done in {dt:.0f}s", flush=True)
    return results, raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--provider", choices=["ollama", "openai"], default="ollama")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--set", default="data/eval_set.json", help="eval set JSON")
    ap.add_argument("--outdir", default="data/auto_answers", help="output dir")
    ap.add_argument("--temperature", type=float, default=0.0)
    args = ap.parse_args()

    if args.provider == "ollama":
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        api_key = "ollama"  # ignored by ollama
    else:
        base_url = os.environ.get("OPENAI_BASE_URL")  # None -> default OpenAI
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise SystemExit("OPENAI_API_KEY not set in environment")

    eval_items = json.load(open(args.set))
    os.makedirs(args.outdir, exist_ok=True)

    for model in args.models:
        print(f"=== {args.provider}:{model} ({len(eval_items)} prompts) ===", flush=True)
        results, raw = run_model(model, eval_items, base_url, api_key, args.workers, args.temperature)
        safe = model.replace("/", "_").replace(":", "_")
        out = {"model": model, "provider": args.provider, "answers": results}
        json.dump(out, open(f"{args.outdir}/{safe}.json", "w"), indent=1)
        json.dump(raw, open(f"{args.outdir}/{safe}.raw.json", "w"), indent=1)
        print(f"  saved {args.outdir}/{safe}.json", flush=True)


if __name__ == "__main__":
    main()
