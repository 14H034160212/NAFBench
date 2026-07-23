#!/usr/bin/env bash
# ≥30-sample supplementary runs on the 44-program diverse WFS set (wfs_big).
# Sequential to avoid two 32B models contending on GPU. Logs completion tokens
# (run_eval / translate_solve_set both record them).
set -u
cd /data/qbao775/NAFBench
MODELS="qwen2.5-coder:32b llama3:8b deepseek-r1:32b"
LOG=/tmp/claude-1022/-data-qbao775-NAFBench/1d1bd52a-b041-4cd7-aedf-93bf1fc8e7fc/scratchpad
echo "START $(date)"

echo "=== [1/3] DIRECT baseline (wfs_big) ==="
python3 run_eval.py --provider ollama --models $MODELS \
  --set data/wfs_big.json --outdir data/wfs_big_answers --workers 2 \
  > "$LOG/wfs_big_direct.out" 2>&1

echo "=== [2/3] VERIFY / Mitigation-3 (wfs_big_verify) ==="
python3 run_eval.py --provider ollama --models $MODELS \
  --set data/wfs_big_verify.json --outdir data/wfs_big_verify_answers --workers 2 \
  > "$LOG/wfs_big_verify.out" 2>&1

echo "=== [3/3] TRANSLATE-THEN-SOLVE (wfs_big) ==="
python3 translate_solve_set.py --provider ollama --models $MODELS \
  --set data/wfs_big.json --outdir data/t2s_big_answers --workers 2 \
  > "$LOG/wfs_big_t2s.out" 2>&1

echo "DONE $(date)"
