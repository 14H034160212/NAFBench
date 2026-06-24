"""DPO on solver-certified preference pairs, continuing the SFT adapter.

chosen = certified reasoning; rejected = the documented reversion failure.
This is the DPO step of the Conflict-Aware-Fusion mitigation arm.
"""
import argparse, os, json
os.environ.setdefault("HF_HUB_OFFLINE", "1")
import torch
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
from trl import DPOConfig, DPOTrainer

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="google/gemma-3-4b-it")
ap.add_argument("--sft_adapter", default="runs/sft")
ap.add_argument("--data", default="data/train/dpo.jsonl")
ap.add_argument("--out", default="runs/dpo")
ap.add_argument("--epochs", type=float, default=4.0)
args = ap.parse_args()

tok = AutoTokenizer.from_pretrained(args.model)
base = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16,
                                            device_map="cuda:0")
model = PeftModel.from_pretrained(base, args.sft_adapter, is_trainable=True)
model.config.use_cache = False

rows = [json.loads(l) for l in open(args.data)]
conv = [{"prompt": [{"role": "user", "content": r["prompt"]}],
         "chosen": [{"role": "assistant", "content": r["chosen"]}],
         "rejected": [{"role": "assistant", "content": r["rejected"]}]} for r in rows]
ds = Dataset.from_list(conv)

cfg = DPOConfig(
    output_dir=args.out, num_train_epochs=args.epochs,
    per_device_train_batch_size=1, gradient_accumulation_steps=4,
    learning_rate=5e-6, beta=0.1, logging_steps=2, save_strategy="no",
    bf16=True, max_length=1024, max_prompt_length=768, report_to=[])

trainer = DPOTrainer(model=model, args=cfg, train_dataset=ds, processing_class=tok)
trainer.train()
trainer.save_model(args.out)
print("DPO adapter saved to", args.out)
