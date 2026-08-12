# NAF-Bench Leaderboard — hard set (v3)

Primary metric: **JOINT accuracy** on `hard_v3` (mixed certified signatures,
so the answer key is not guessable from the condition; includes a real search
family `cnf` = 3-SAT near the phase transition). o4-mini is Agnieszka's
frontier run; the open models are local (ollama).

Decoding: temperature 0 (greedy) for all models, with a token budget large
enough for each model to conclude (verbose reasoning models get up to 16k).
`Qwen3.6`* is the sole exception, run at its recommended temp 0.6 — see note.

| Model | open | JOINT % | per-prompt % |
|---|---|---|---|
| o4-mini | — | **54.5** | 85.1 |
| DeepSeek-V4-Flash | ✓ | **48.5** | 73.7 |
| Gemma4 31B | ✓ | **45.5** | 65.4 |
| Qwen3.5 35B | ✓ | **42.4** | 58.6 |
| Qwen2.5-Coder 32B | ✓ | **30.3** | 62.1 |
| DeepSeek-R1 32B | ✓ | **26.3** | 55.6 |
| Qwen3.6 | ✓ | **1.0** | 22.5 |
| Llama3 8B | ✓ | **1.0** | 41.4 |

JOINT by family (solved / total):

| Model | cnf | parity | coupled | loopy | decided | easy_pad |
|---|---|---|---|---|---|---|
| o4-mini | 2/33 | 4/6 | 4/4 | 11/20 | 30/30 | 3/6 |
| DeepSeek-V4-Flash | 0/33 | 0/6 | 0/4 | 19/20 | 29/30 | 0/6 |
| Qwen2.5-Coder 32B | 1/33 | 1/6 | 1/4 | 0/20 | 27/30 | 0/6 |
| DeepSeek-R1 32B | 0/33 | 0/6 | 0/4 | 0/20 | 26/30 | 0/6 |
| Qwen3.6 | 0/33 | 0/6 | 0/4 | 0/20 | 1/30 | 0/6 |
| Qwen3.5 35B | 0/33 | 1/6 | 2/4 | 9/20 | 30/30 | 0/6 |
| Gemma4 31B | 0/33 | 0/6 | 0/4 | 16/20 | 29/30 | 0/6 |
| Llama3 8B | 0/33 | 0/6 | 0/4 | 0/20 | 0/30 | 1/6 |

**Read of the board.** v3 gives a genuine spread with a *tight frontier
gap*: o4-mini leads (54.5) but three open models cluster right behind —
DeepSeek-V4-Flash 48.5, Gemma4 45.5, Qwen3.5 42.4 — far closer than on
easier sets.

Per family: `cnf` (3-SAT search) defeats every open model (0/33); only
o4-mini cracks it (2/33). The combinatorial families `parity`/`coupled`
are also almost exclusively o4-mini's (4/6, 4/4), with **Qwen3.5 the only
open model to score there** (1/6, 2/4). On `loopy`, open models actually
*win*: **V4-Flash (19/20) and Gemma4 (16/20) beat o4-mini's 11/20**.
`decided` (stratified, answer varies by program) is where most models
earn their score — reading the program pays off there.

\* **Qwen3.6 (1.0) is a non-termination result, not a reasoning score.**
It is extraordinarily verbose: even at its recommended temp 0.6 with a
16k-token budget, ~50% of readings never finish, so the all-four JOINT
metric collapses (per-reading it concludes ~49%). Reported for
completeness with this caveat rather than as a capability estimate.
