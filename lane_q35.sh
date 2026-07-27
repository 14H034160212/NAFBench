#!/usr/bin/env bash
# Qwen3.5-9B lane (gemma4-rl env, transformers 5.5 native): retrain SFT + re-eval
# all four q35 files (base/sft x 600/2048) on corrected wfs_big.
set -e; cd "$(dirname "$0")"
export HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=2
PY="${PYTHON:-python3}"
M=Qwen/Qwen3.5-9B
echo "### TRAIN q35_sft (seed 1)"
$PY train_sft.py --model $M --data data/train/sft.jsonl --out runs/q35_sft --seed 1
echo "### EVAL q35"
$PY eval_local.py --model $M --set data/wfs_big.json --tag base_q35   --max_new_tokens 600
$PY eval_local.py --model $M --set data/wfs_big.json --tag base_q35_t --max_new_tokens 2048
$PY eval_local.py --model $M --adapter runs/q35_sft --set data/wfs_big.json --tag sft_q35   --max_new_tokens 600
$PY eval_local.py --model $M --adapter runs/q35_sft --set data/wfs_big.json --tag sft_q35_t --max_new_tokens 2048
echo "### Q35 LANE DONE"
