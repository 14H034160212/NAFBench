#!/bin/bash
cd "$(dirname "$0")"
# wait for the original deepseek grid run to release the GPU
while pgrep -f "run_eval.py.*deepseek-r1:32b.*v2_eval" >/dev/null; do sleep 20; done
echo "[aux] original grid done, starting aux runs at $(date)"
mkdir -p data/grid_large_answers data/verb_answers
for M in llama3:8b qwen2.5-coder:32b deepseek-r1:32b; do
  for SET in "grid_large_set.json:grid_large_answers" "verb_set.json:verb_answers"; do
    S="${SET%%:*}"; OUT="${SET##*:}"
    echo "[aux] $(date) model=$M set=$S"
    python3 run_eval.py --provider ollama --models "$M" \
      --set "data/$S" --outdir "data/$OUT" --temperature 0.0 --workers 3
  done
done
echo "[aux] ALL DONE at $(date)"
