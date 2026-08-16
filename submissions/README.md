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

   Traced submissions get an **auxiliary** column, **trace-sound %** (see Metric):
   a rough, regex-based approximation of how often your `trace` actually justified a
   correct answer under the specified semantics. It is auxiliary information only and
   does **not** affect ranking. Answer-only submissions are fully accepted and show
   `–` in that column.

3. Add your file here as **`submissions/<team>__<subtask>.jsonl`**, where
   `<subtask>` is one of `8k-lite`, `16k`, `full`
   (e.g. `submissions/my-model__8k-lite.jsonl`), and open a Pull Request.

4. A GitHub Action scores it against the hidden gold and **comments your score**
   (JOINT, plus the auxiliary trace-sound signal) on the PR within a minute or two.

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

**trace-sound %** (auxiliary, *not* a ranking criterion; traced submissions only) —
of the programs you answered correctly *and* supplied a `trace` for, the share whose
trace commits to the certified query verdict (and, on odd cycles, registers that the
program admits no stable model). The check is **regex-based and imperfect — a rough
approximation of soundness**, not a verified proof audit, so it is reported as
auxiliary information only and does not affect ranking. It gives a coarse signal for
"right answer, unsound/absent reasoning." Ranking is by JOINT alone.

## Subtasks (by context budget)

`8k-lite` ⊂ `16k` ⊂ `full`. The lite tiers drop the largest search instances so a
competent reasoner can solve them within an 8k / 16k token budget; `full`
includes the largest 3-SAT instances that may need longer context.
