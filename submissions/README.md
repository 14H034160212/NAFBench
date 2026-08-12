# Submit to the NAF-Bench leaderboard

Fully automated, free, server-side scoring. Gold labels are **never public** —
they live in a private Hugging Face dataset and are read only by the scoring
GitHub Action.

## How to submit

1. Get the test **inputs** from the public dataset
   [`qbao775/naf-bench`](https://huggingface.co/datasets/qbao775/naf-bench):
   `inputs_8k-lite.jsonl`, `inputs_16k.jsonl`, or `inputs_full.jsonl`.
   (`sample_with_gold.jsonl` shows the format and label space.)

2. Run your model and produce a **JSONL**, one line per prompt:

   ```json
   {"id": "hv3hid-decided_d1-i0-cred::cred", "prediction": "A"}
   ```

   `prediction` is `A` (definitely yes), `B` (definitely no), or `C` (cannot be
   determined). Free-form answers like `true`/`false`/`unknown` are also accepted.

3. Add your file here as **`submissions/<team>__<subtask>.jsonl`**, where
   `<subtask>` is one of `8k-lite`, `16k`, `full`
   (e.g. `submissions/my-model__8k-lite.jsonl`), and open a Pull Request.

4. A GitHub Action scores it against the hidden gold and **comments your JOINT
   accuracy** on the PR. When a maintainer merges it, the public
   [`leaderboard/LEADERBOARD.md`](../leaderboard/LEADERBOARD.md) updates
   automatically (best JOINT per team per subtask is kept).

## Metric

**JOINT accuracy** — a program counts only if *all four* specified readings
(SLDNF / well-founded / credulous / skeptical) are answered correctly. Diagnostic
columns (per-prompt, per-reading) are shown too but do not rank.

## Subtasks (by context budget)

`8k-lite` ⊂ `16k` ⊂ `full`. The lite tiers drop the largest search instances so a
competent reasoner can solve them within an 8k / 16k token budget; `full`
includes the largest 3-SAT instances that may need longer context.
