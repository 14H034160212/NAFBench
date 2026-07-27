set -e; cd "$(dirname "$0")"
export HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=7
echo "### TRAIN multi-verbalization SFT"
python3 train_sft.py --data data/train/sft_multi.jsonl --out runs/sft_multi --epochs 3
echo "### EVAL on UNSEEN framing (theme2)"
python3 eval_local.py --model google/gemma-3-4b-it --set data/heldout_theme2.json --tag base_ho
python3 eval_local.py --model google/gemma-3-4b-it --adapter runs/sft --set data/heldout_theme2.json --tag sft1_ho
python3 eval_local.py --model google/gemma-3-4b-it --adapter runs/sft_multi --set data/heldout_theme2.json --tag sftM_ho
echo "### EVAL multi-SFT on abstract set (Exp19 comparison)"
python3 eval_local.py --model google/gemma-3-4b-it --adapter runs/sft_multi --set data/wfs_big_generic.json --tag sftM_gen
echo "### MULTIVERB DONE"
