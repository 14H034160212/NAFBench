#!/usr/bin/env bash
# Qwen2.5-7B lane: retrain 3 SFT seeds + DPO on corrected data, then re-eval.
set -e; cd /data/qbao775/NAFBench
export HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=0
M=Qwen/Qwen2.5-7B-Instruct
for s in 1 2 3; do
  echo "### TRAIN qwen_sft$s (seed $s)"
  python3 train_sft.py --model $M --data data/train/sft.jsonl --out runs/qwen_sft$s --seed $s
done
echo "### TRAIN qwen_dpo (on top of qwen_sft1)"
python3 train_dpo.py --model $M --sft_adapter runs/qwen_sft1 --data data/train/dpo.jsonl --out runs/qwen_dpo
echo "### EVAL qwen"
python3 eval_local.py --model $M --set data/wfs_big.json --tag base_qwen
for s in 1 2 3; do
  python3 eval_local.py --model $M --adapter runs/qwen_sft$s --set data/wfs_big.json --tag sft_qwen_s$s
done
python3 eval_local.py --model $M --adapter runs/qwen_dpo --set data/wfs_big.json --tag sftdpo_qwen
echo "### QWEN LANE DONE"
