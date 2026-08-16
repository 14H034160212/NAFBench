# NAF-Bench Leaderboard — hard set (v3)

Primary metric: **JOINT accuracy** on `hard_v3` (mixed certified signatures,
so the answer key is not guessable from the condition; includes a bounded
search family `cnf_n8` = 8-variable 3-SAT). The prohibitively-large 3-SAT
tiers `cnf_n14`/`cnf_n22` (2^14/2^22 search spaces) are excluded as
uninformative. o4-mini is Agnieszka's frontier run; the open models are local
(ollama).

Decoding: temperature 0 (greedy) for all models, with a token budget large
enough for each model to conclude (verbose reasoning models get up to 16k).
`Qwen3.6`* is the sole exception, run at its recommended temp 0.6 — see note.

| Model | open | JOINT % |
|---|---|---|
| o4-mini | — | **68.8** |
| DeepSeek-V4-Flash | ✓ | **62.3** |
| Gemma4 31B | ✓ | **58.4** |
| Qwen3.5 35B | ✓ | **54.5** |
| Qwen2.5-Coder 32B | ✓ | **39.0** |
| DeepSeek-R1 32B | ✓ | **33.8** |
| Qwen3.6 | ✓ | **1.3** |
| Llama3 8B | ✓ | **1.3** |

JOINT by family (solved / total):

| Model | cnf | parity | coupled | loopy | decided | easy_pad |
|---|---|---|---|---|---|---|
| o4-mini | 1/11 | 4/6 | 4/4 | 11/20 | 30/30 | 3/6 |
| DeepSeek-V4-Flash | 0/11 | 0/6 | 0/4 | 19/20 | 29/30 | 0/6 |
| Qwen2.5-Coder 32B | 1/11 | 1/6 | 1/4 | 0/20 | 27/30 | 0/6 |
| DeepSeek-R1 32B | 0/11 | 0/6 | 0/4 | 0/20 | 26/30 | 0/6 |
| Qwen3.6 | 0/11 | 0/6 | 0/4 | 0/20 | 1/30 | 0/6 |
| Qwen3.5 35B | 0/11 | 1/6 | 2/4 | 9/20 | 30/30 | 0/6 |
| Gemma4 31B | 0/11 | 0/6 | 0/4 | 16/20 | 29/30 | 0/6 |
| Llama3 8B | 0/11 | 0/6 | 0/4 | 0/20 | 0/30 | 1/6 |

**Read of the board.** The hard set gives a genuine spread with a *tight
frontier gap*: o4-mini leads (68.8) but three open models cluster right
behind — DeepSeek-V4-Flash 62.3, Gemma4 58.4, Qwen3.5 54.5 — far closer
than on easier sets.

Per family: even the bounded `cnf_n8` (3-SAT search) defeats almost every
open model (0/11; Qwen2.5-Coder scrapes 1/11), and o4-mini manages only
1/11 — search stays the hardest family. The combinatorial families
`parity`/`coupled` are almost exclusively o4-mini's (4/6, 4/4), with
**Qwen3.5 the only open model to score there** (1/6, 2/4). On `loopy`,
open models actually *win*: **V4-Flash (19/20) and Gemma4 (16/20) beat
o4-mini's 11/20**. `decided` (stratified, answer varies by program) is
where most models earn their score — reading the program pays off there.

\* **Qwen3.6 (1.0) is a non-termination result, not a reasoning score.**
It is extraordinarily verbose: even at its recommended temp 0.6 with a
16k-token budget, ~50% of readings never finish, so the all-four JOINT
metric collapses (per-reading it concludes ~49%). Reported for
completeness with this caveat rather than as a capability estimate.
