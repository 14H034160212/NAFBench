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

   **Optional — submit the reasoning too (recommended):** add a `trace` field with
   your model's full reasoning for that prompt:

   ```json
   {"id": "hv3hid-decided_d1-i0-cred::cred", "prediction": "A", "trace": "Under the credulous reading we look for a stable model in which q holds ... "}
   ```

   Traced submissions get a second scored column, **reasoned soundly %** (see
   Metric): of the programs you got right, how many your `trace` actually justified
   under the specified semantics — checked against the private certification, not by
   string match. Answer-only submissions are still fully accepted and simply show
   `–` in that column.

3. Add your file here as **`submissions/<team>__<subtask>.jsonl`**, where
   `<subtask>` is one of `8k-lite`, `16k`, `full`
   (e.g. `submissions/my-model__8k-lite.jsonl`), and open a Pull Request.

4. A GitHub Action scores it against the hidden gold and **comments your score**
   (JOINT + reasoned soundly) on the PR within a minute or two.

5. **Auto-merge:** if your PR changes *only* `submissions/<team>__<subtask>.jsonl`
   file(s) and scored cleanly, it is **merged automatically** and the public
   leaderboard ([`LEADERBOARD.md`](../leaderboard/LEADERBOARD.md), the
   [`leaderboard.json`](https://huggingface.co/datasets/qbao775/naf-bench) feed,
   and the [live board](https://huggingface.co/spaces/qbao775/naf-bench-leaderboard))
   updates on its own — no maintainer action needed. Best JOINT per team per
   subtask is kept. A PR that touches anything else (code, workflows, …) is held
   for manual maintainer review instead.

## Metric

**JOINT accuracy** (primary) — a program counts only if *all four* specified
readings (SLDNF / well-founded / credulous / skeptical) are answered correctly.
Diagnostic columns (per-prompt, per-reading) are shown too but do not rank.

**reasoned soundly %** (secondary, traced submissions only) — of the programs you
answered correctly *and* supplied a `trace` for, the share whose trace commits to
the certified query verdict (and, on odd cycles, registers that the program admits
no stable model). This is a v1 soundness audit: it catches "right answer, wrong (or
absent) reasoning" — a constant-guesser can score well on JOINT but cannot score
here. It audits the query verdict + odd-cycle recognition against the private
per-instance certification; a fuller per-atom proof audit is planned.

## Subtasks (by context budget)

`8k-lite` ⊂ `16k` ⊂ `full`. The lite tiers drop the largest search instances so a
competent reasoner can solve them within an 8k / 16k token budget; `full`
includes the largest 3-SAT instances that may need longer context.
