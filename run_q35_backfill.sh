#!/usr/bin/env bash
# Backfill completion tokens for the 4 Qwen3.5-9B local files.
# Deterministic (do_sample=False) so answers reproduce; only tokens get added.
set -euo pipefail
cd "$(dirname "$0")"
export CUDA_VISIBLE_DEVICES=1
PY="${PYTHON:-python3}"
M=Qwen/Qwen3.5-9B
S=data/wfs_big.json

echo "=== base_q35 (600) ==="
$PY eval_local.py --model $M --set $S --tag base_q35   --max_new_tokens 600
echo "=== base_q35_t (2048) ==="
$PY eval_local.py --model $M --set $S --tag base_q35_t --max_new_tokens 2048
echo "=== sft_q35 (600) ==="
$PY eval_local.py --model $M --adapter runs/q35_sft --set $S --tag sft_q35   --max_new_tokens 600
echo "=== sft_q35_t (2048) ==="
$PY eval_local.py --model $M --adapter runs/q35_sft --set $S --tag sft_q35_t --max_new_tokens 2048
echo "=== ALL DONE ==="
