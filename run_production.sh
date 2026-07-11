#!/usr/bin/env bash
# Production run driver (option b). The 30 instances per cell are DISTINCT
# programs baked into data/production_set.json (600 prompts, 120 programs), so we
# do a single deterministic pass per model (add repeats only for decode-noise
# CIs). Prompts are final; A. Słusarz confirmed option (b).
#
# Usage: bash run_production.sh [N_REPEATS=1] [temperature=0.0]
set -e; cd /data/qbao775/NAFBench
N="${1:-1}"; T="${2:-0.0}"
SET=data/production_set.json
OLLAMA_MODELS="qwen2.5-coder:32b llama3:8b deepseek-r1:32b"
OPENAI_MODELS="gpt-4o-mini gpt-4.1 gpt-5"

[ -f "$SET" ] || python3 make_production.py
echo "### production run: N=$N pass(es), T=$T, set=$SET (600 prompts / 120 programs)"
for i in $(seq 1 "$N"); do
  OUT="data/production_answers/run$i"; mkdir -p "$OUT"
  echo "### pass $i/$N -> $OUT"
  python3 run_eval.py --provider ollama --models $OLLAMA_MODELS \
      --set "$SET" --outdir "$OUT" --temperature "$T" --workers 3
  set -a; . ./.env 2>/dev/null; set +a
  python3 run_eval.py --provider openai --models $OPENAI_MODELS \
      --set "$SET" --outdir "$OUT" --temperature "$T" --workers 6
done
echo "### PRODUCTION RUN DONE ($N pass(es))"
python3 analyze_production.py
