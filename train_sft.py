"""LoRA SFT on solver-certified chain-of-thought (mitigation arm, SFT step)."""
import argparse, os
os.environ.setdefault("HF_HUB_OFFLINE", "1")
import torch
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig
from trl import SFTConfig, SFTTrainer

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="google/gemma-3-4b-it")
ap.add_argument("--data", default="data/train/sft.jsonl")
ap.add_argument("--out", default="runs/sft")
ap.add_argument("--epochs", type=float, default=3.0)
ap.add_argument("--max_steps", type=int, default=-1)
ap.add_argument("--seed", type=int, default=42)
args = ap.parse_args()

tok = AutoTokenizer.from_pretrained(args.model)
model = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16,
                                             device_map="cuda:0")
model.config.use_cache = False
ds = load_dataset("json", data_files=args.data, split="train")

peft_cfg = LoraConfig(
    r=16, lora_alpha=32, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"])

cfg = SFTConfig(
    output_dir=args.out, num_train_epochs=args.epochs, max_steps=args.max_steps,
    per_device_train_batch_size=2, gradient_accumulation_steps=4,
    learning_rate=2e-4, lr_scheduler_type="cosine", warmup_ratio=0.05,
    logging_steps=5, save_strategy="no", bf16=True, max_length=1024,
    gradient_checkpointing=True, report_to=[], seed=args.seed, data_seed=args.seed)

trainer = SFTTrainer(model=model, args=cfg, train_dataset=ds, peft_config=peft_cfg,
                     processing_class=tok)
trainer.train()
trainer.save_model(args.out)
tok.save_pretrained(args.out)
print("SFT adapter saved to", args.out)
