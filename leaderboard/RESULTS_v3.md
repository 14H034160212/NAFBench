# NAF-Bench Leaderboard — hard set (v3)

Primary metric: **JOINT accuracy** on `hard_v3` (mixed certified signatures,
so the answer key is not guessable from the condition; includes a real search
family `cnf` = 3-SAT near the phase transition). o4-mini is Agnieszka's
frontier run; the open models are local (ollama).

| Model | open | JOINT % | per-prompt % |
|---|---|---|---|
| o4-mini | — | **54.5** | 85.1 |
| Qwen2.5-Coder 32B | ✓ | **30.3** | 62.1 |
| Llama3 8B | ✓ | **1.0** | 41.4 |
| DeepSeek-R1 32B | ✓ | — | — |

JOINT by family (solved / total):

| Model | cnf | parity | coupled | loopy | decided | easy_pad |
|---|---|---|---|---|---|---|
| o4-mini | 2/33 | 4/6 | 4/4 | 11/20 | 30/30 | 3/6 |
| Qwen2.5-Coder 32B | 1/33 | 1/6 | 1/4 | 0/20 | 27/30 | 0/6 |
| DeepSeek-R1 32B (pending) | — | — | — | — | — | — |
| Llama3 8B | 0/33 | 0/6 | 0/4 | 0/20 | 0/30 | 1/6 |

`cnf` (search) and `loopy` crush every model; `decided` (stratified,
answer varies by program) is where reading the program actually pays off
— note Qwen's JOINT is almost entirely `decided`. v3 gives a real spread
(o4-mini > Qwen > Llama3), unlike v2 whose answer key was guessable.
