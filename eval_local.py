"""Evaluate a local HF model (optionally + LoRA adapter) on a NAF-Bench set."""
import argparse, os, json
os.environ.setdefault("HF_HUB_OFFLINE", "1")
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from nafbench.answer import parse_answer

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="google/gemma-3-4b-it")
ap.add_argument("--adapter", default=None)
ap.add_argument("--set", default="data/wfs_big.json")
ap.add_argument("--tag", default="base")
ap.add_argument("--max_new_tokens", type=int, default=600)
args = ap.parse_args()

tok = AutoTokenizer.from_pretrained(args.model)
model = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16,
                                             device_map="cuda:0")
if args.adapter:
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, args.adapter)
model.eval()

items = json.load(open(args.set))
ans = {}
ctokens = {}
for e in items:
    msgs = [{"role": "user", "content": e["prompt"]}]
    enc = tok.apply_chat_template(msgs, add_generation_prompt=True,
                                  return_tensors="pt", return_dict=True)
    enc = {k: v.to(model.device) for k, v in enc.items()}
    plen = enc["input_ids"].shape[1]
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=args.max_new_tokens, do_sample=False,
                             pad_token_id=tok.eos_token_id)
    txt = tok.decode(out[0, plen:], skip_special_tokens=True)
    ans[e["task_id"]] = parse_answer(txt)
    ctokens[e["task_id"]] = int(out.shape[1] - plen)   # generated (completion) tokens

os.makedirs("data/local_answers", exist_ok=True)
json.dump({"model": args.model, "adapter": args.adapter, "tag": args.tag,
           "answers": ans, "completion_tokens": ctokens},
          open(f"data/local_answers/{args.tag}.json", "w"), indent=1)

# score
div = [e for e in items if e.get("kind") == "divergent"]
ctl = [e for e in items if e.get("kind") == "control"]
k = sum(ans[e["task_id"]] == e["gold"] for e in items)
kd = sum(ans[e["task_id"]] == e["gold"] for e in div)
kc = sum(ans[e["task_id"]] == e["gold"] for e in ctl)
print(f"[{args.tag}] overall {k}/{len(items)}  divergent {kd}/{len(div)}  control {kc}/{len(ctl)}")
