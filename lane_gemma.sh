#!/usr/bin/env bash
# Gemma-3-4b lane: retrain single-framing + multi-framing SFT on corrected data,
# then re-eval base/sft/sftM on wfs_big, generic, and held-out theme-2.
set -e; cd "$(dirname "$0")"
export HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=7
M=google/gemma-3-4b-it
echo "### TRAIN gemma sft (single-framing)"
python3 train_sft.py --model $M --data data/train/sft.jsonl --out runs/sft --seed 42
echo "### TRAIN gemma sft_multi (themes 0,1)"
python3 train_sft.py --model $M --data data/train/sft_multi.jsonl --out runs/sft_multi --epochs 3 --seed 42
echo "### EVAL gemma"
python3 eval_local.py --model $M --set data/wfs_big.json --tag base
python3 eval_local.py --model $M --adapter runs/sft --set data/wfs_big.json --tag sft
python3 eval_local.py --model $M --set data/wfs_big_generic.json --tag base_gen
python3 eval_local.py --model $M --adapter runs/sft --set data/wfs_big_generic.json --tag sft_gen
python3 eval_local.py --model $M --adapter runs/sft_multi --set data/wfs_big_generic.json --tag sftM_gen
python3 eval_local.py --model $M --set data/heldout_theme2.json --tag base_ho
python3 eval_local.py --model $M --adapter runs/sft --set data/heldout_theme2.json --tag sft1_ho
python3 eval_local.py --model $M --adapter runs/sft_multi --set data/heldout_theme2.json --tag sftM_ho
echo "### GEMMA LANE DONE"
