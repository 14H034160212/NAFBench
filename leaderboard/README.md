# NAF-Bench Leaderboard

A public leaderboard for **negation and non-monotonic reasoning** in LLMs: given
a rulebook and a *named* reading of negation, does a model apply that reading — or
fall back to a hard-wired default? Every instance is solver-certified, so the
ground truth is exact and the benchmark can be regenerated harder as models
improve.

## What is scored

Each program is presented under four **readings of negation** — SLDNF /
closed-world, well-founded (WFS, three-valued), and stable-model **credulous** and
**skeptical** — plus a no-instruction baseline. The same program can have four
different correct answers, so getting one right by defaulting proves nothing.

**Primary metric — JOINT accuracy.** A program counts as solved only if the model
answers **all four** specified readings correctly. This removes credit for lucky /
vacuous coincidences (e.g. an odd cycle makes the skeptical answer vacuously
"yes", which plain forward-chaining also produces). Diagnostic columns
(per-reading accuracy, per-bin JOINT, format-valid rate, coverage) are reported
but do **not** determine ranking.

Ranking is by `joint_accuracy` on the hidden **test** split.

## Data

| split | file | gold | use |
|---|---|---|---|
| dev | `data/dev.jsonl` | included | debugging / prompt development (this is the public benchmark) |
| test | `data/test_public.jsonl` | **hidden** | leaderboard scoring |

`data/test_gold.json` (hidden answers) **and** `data/test_public.jsonl` (test
prompts) are both kept out of the public repo — only the generator
`make_leaderboard.py` ships. Maintainers regenerate the test set locally and
upload the prompts to the evaluation server and the gold as server-side
annotation. This matters because the benchmark is solver-certified: the answer to
any prompt is *recoverable by running a solver on it*, so publishing the test
prompts would let anyone build an answer key and fine-tune on it. Keeping the test
set off the public repo (and rolling in fresh programs over time) is what makes it
contamination-resistant. Programs are generated with seeds disjoint from every
public release and deduplicated by canonical key.

Note on tracks: because a solver trivially gets 100%, the **Standard** track is an
honor-system "base model, no tools" condition; the **Enhanced** track is where
solver-augmented systems belong.

Regenerate splits with `python make_leaderboard.py` (raise `DEPTH`/`WIDTH`/`CYC`
for a harder tier if frontier models saturate).

## Two tracks

Report both if you like, but they are ranked separately so base models and
augmented systems are compared fairly.

- **Standard** — fixed prompt template, **single** generation, temperature 0, no
  external tools, no test-set fine-tuning, fixed max tokens. Measures the base
  model.
- **Enhanced** — chain-of-thought, self-consistency, symbolic solvers, agents, or
  task-specific training are all allowed, **but the method must be fully
  disclosed** (`method_url` in metadata).

## Submission format

A JSONL file, one line per prompt in `test_public.jsonl`:

```json
{"id": "naflb-odd-i3-wfs::wfs", "prediction": "C"}
```

`prediction` accepts the choice letter (`A`/`B`/`C`) or a phrasing the evaluator
normalizes (`true`/`false`/`yes`/`no`/`unknown`/`cannot be determined`/…).
Unparseable predictions are counted wrong and lower `format_valid_rate`.
Answer the `none`-condition items too (they feed the default-correspondence
diagnostic); they are not scored for accuracy.

Include a `metadata.json` (see `metadata_schema.json`) — `track`, `model_name`,
`prompt_setting`, `reasoning_mode`, `external_tools` are required.

## Scoring locally

```bash
python evaluate.py --submission your_submission.jsonl --gold data/test_gold.json
```

(You can only run this on `dev` locally, using dev gold; the test gold is
server-side.) The script prints an EvalAI-style result envelope whose
`joint_accuracy` is the ranking metric.

## Policy

- Standard track: exactly one model call per item, no tools, no test-tuning.
- Submission limits (per day / total) are enforced on the server to curb
  test-set overfitting.
- Closed models must record `model_version` and `evaluation_date`.
- Full model/prompt/decoding details belong on the project page; the hidden gold
  is never published.
