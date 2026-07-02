"""Translate-then-solve baseline (PrologMCP-style).

Instead of asking the model to APPLY a negation semantics, we ask it only to
TRANSLATE the natural-language rules into a ground normal logic program. Our
certified solvers then apply the semantics. This isolates the bottleneck:

  direct reasoning   = model understands rules AND applies the semantics
  translate-then-solve = model only translates; the SOLVER applies the semantics

If translation is faithful, translate-then-solve should approach 100% on every
semantics, showing that the failures in the direct condition are failures of
*applying* the semantics, not of understanding the rules.

Usage:
  python translate_solve.py --provider ollama --models qwen2.5-coder:32b llama3:8b
  OPENAI_API_KEY=... python translate_solve.py --provider openai --models gpt-4o-mini gpt-4.1
"""
import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI
from nafbench.parse import parse_program
from nafbench import solvers as S
from nafbench import verbalize as V

TRANSLATE_SYS = (
    "You translate natural-language rule sets into a ground normal logic "
    "program. Output ONLY the program, one statement per line, in this grammar:\n"
    "  fact.\n"
    "  head :- b1, b2, not c1.\n"
    "  QUERY: <the queried atom>\n"
    "Use short ground atom names (no variables). Encode 'X holds if and only if "
    "Y does not' as the rule 'x :- not y.' (one rule per such statement). Encode "
    "'P unless Q' as 'p :- <conditions>, not q.'. Do not solve or explain; output "
    "only the program and the QUERY line.")


def translate_prompt(premises, query):
    return (f"Natural-language rules:\n{premises}\n\n"
            f"Query: {query}\n\n"
            f"Translate into the logic-program grammar now.")


def ask_translation(client, model, prompt):
    is_reasoning = any(model.startswith(p) for p in ("gpt-5", "o1", "o3", "o4"))
    for attempt in range(3):
        try:
            if is_reasoning:
                r = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": TRANSLATE_SYS},
                              {"role": "user", "content": prompt}],
                    max_completion_tokens=16384)
            else:
                r = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": TRANSLATE_SYS},
                              {"role": "user", "content": prompt}],
                    temperature=0, max_tokens=2048)
            usage = getattr(r, "usage", None)
            ctoks = getattr(usage, "completion_tokens", None) if usage else None
            return r.choices[0].message.content, ctoks
        except Exception as e:  # noqa
            if attempt == 2:
                return f"<error: {e}>", None
            time.sleep(2 * (attempt + 1))


def solve_label(prog, query, cond):
    """Apply the certified solver matching the condition; map to A/B/C."""
    solver = V.SEMANTICS_TO_SOLVER[cond]
    if solver == "stable":
        label, _ = S.stable_query(prog, query)
    elif solver == "wfs":
        label = S.wfs_query(prog, query)
    else:
        label = S.prolog_query(prog, query)
    return V.label_to_gold(label)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--provider", choices=["ollama", "openai"], default="ollama")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    if args.provider == "ollama":
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        api_key = "ollama"
    else:
        base_url = os.environ.get("OPENAI_BASE_URL")
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise SystemExit("OPENAI_API_KEY not set")

    recs = {json.loads(l)["id"]: json.loads(l)
            for l in open("data/nafbench_poc.jsonl")}
    eval_items = json.load(open("data/eval_set.json"))
    # unique programs to translate (one translation reused across conditions)
    progs = {}
    for e in eval_items:
        progs.setdefault(e["rec_id"], recs[e["rec_id"]])
    os.makedirs("data/t2s_answers", exist_ok=True)

    for model in args.models:
        client = OpenAI(base_url=base_url, api_key=api_key)
        print(f"=== translate-then-solve {model} ({len(progs)} programs) ===", flush=True)
        translations = {}
        rec_completion_tokens = {}

        def do(rid_rec):
            rid, rec = rid_rec
            txt, ctoks = ask_translation(client, model,
                                         translate_prompt(rec["premises_nl"], rec["query_nl"]))
            prog, q = parse_program(txt)
            return rid, txt, prog, q, ctoks

        parsed_ok = 0
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = [ex.submit(do, item) for item in progs.items()]
            for f in as_completed(futs):
                rid, txt, prog, q, ctoks = f.result()
                translations[rid] = {"text": txt, "ok": prog is not None, "query": q}
                rec_completion_tokens[rid] = ctoks
                if prog is not None:
                    parsed_ok += 1
                    translations[rid]["program"] = prog
                print(f"  [{model}] {rid} parsed={prog is not None} query={q}", flush=True)

        # score every eval task with the solver applied to the translated program
        answers = {}
        completion_tokens = {}
        for e in eval_items:
            tr = translations.get(e["rec_id"])
            if not tr or not tr["ok"]:
                answers[e["task_id"]] = None
                completion_tokens[e["task_id"]] = rec_completion_tokens.get(e["rec_id"])
                continue
            try:
                answers[e["task_id"]] = solve_label(tr["program"], tr["query"], e["cond"])
            except Exception:  # noqa
                answers[e["task_id"]] = None
            completion_tokens[e["task_id"]] = rec_completion_tokens.get(e["rec_id"])

        safe = model.replace("/", "_").replace(":", "_")
        out = {"model": model, "provider": args.provider,
               "method": "translate_then_solve",
               "parsed_ok": parsed_ok, "n_programs": len(progs),
               "answers": answers,
               "completion_tokens": completion_tokens,
               "translations": {k: {"text": v["text"], "ok": v["ok"], "query": v["query"]}
                                for k, v in translations.items()}}
        json.dump(out, open(f"data/t2s_answers/{safe}.json", "w"), indent=1)
        print(f"  parsed {parsed_ok}/{len(progs)} programs; saved data/t2s_answers/{safe}.json",
              flush=True)


if __name__ == "__main__":
    main()
