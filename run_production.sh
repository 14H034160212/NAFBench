#!/usr/bin/env bash
# Production run driver. Runs the full model panel over the production set with N
# sampled repeats (default 30) at T>0 into data/production_answers/run{i}.
# Ready to launch once A. Słusarz confirms (i) the four prompts are final and
# (ii) what "30 instances per cell" means (see make_production.py).
#
# Usage: bash run_production.sh [N] [temperature]
set -e; cd /data/qbao775/NAFBench
N="${1:-30}"; T="${2:-0.7}"
SET=data/production_set.json
OLLAMA_MODELS="qwen2.5-coder:32b llama3:8b deepseek-r1:32b"
OPENAI_MODELS="gpt-4o-mini gpt-4.1 gpt-5"

[ -f "$SET" ] || python3 make_production.py
echo "### production run: N=$N repeats, T=$T, set=$SET"
for i in $(seq 1 "$N"); do
  OUT="data/production_answers/run$i"; mkdir -p "$OUT"
  echo "### repeat $i/$N -> $OUT"
  python3 run_eval.py --provider ollama --models $OLLAMA_MODELS \
      --set "$SET" --outdir "$OUT" --temperature "$T" --workers 3
  set -a; . ./.env 2>/dev/null; set +a
  python3 run_eval.py --provider openai --models $OPENAI_MODELS \
      --set "$SET" --outdir "$OUT" --temperature "$T" --workers 6
done
echo "### PRODUCTION RUN DONE ($N repeats)"
python3 analyze_production.py
