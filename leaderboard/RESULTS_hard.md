# Open-model results on the hard set (`hard_v2`, sampled)

Per-prompt accuracy by difficulty level. JOINT is ~0 for open models
here (they never get a whole program right), so this shows the
per-reading detail: **skeptical (gold B)** is the discriminating reading;
credulous (A) and WFS (C) are often reachable by defaulting.
Sample: 126 prompts (combo axis, cred/skept/wfs, 3 programs/level).

## Qwen2.5-Coder 32B

| level | stable models | overall | cred (A) | skept (B) | WFS (C) |
|---|---|---|---|---|---|
| disj_n2 | 4 | 89% | 100% | 67% | 100% |
| disj_n3 | 8 | 67% | 100% | 0% | 100% |
| disj_n4 | 16 | 89% | 100% | 67% | 100% |
| disj_n5 | 32 | 67% | 100% | 0% | 100% |
| disj_n6 | 64 | 89% | 100% | 67% | 100% |
| conj_n2 | 4 | 67% | 100% | 33% | 67% |
| conj_n3 | 8 | 89% | 100% | 67% | 100% |
| conj_n4 | 16 | 67% | 33% | 67% | 100% |
| conj_n5 | 32 | 67% | 67% | 33% | 100% |
| conj_n6 | 64 | 67% | 67% | 33% | 100% |
| coupled_n2 | 3 | 67% | 100% | 33% | 67% |
| coupled_n3 | 4 | 67% | 100% | 33% | 67% |
| coupled_n4 | 5 | 67% | 67% | 67% | 67% |
| coupled_n5 | 6 | 44% | 67% | 0% | 67% |

## Llama3 8B

| level | stable models | overall | cred (A) | skept (B) | WFS (C) |
|---|---|---|---|---|---|
| disj_n2 | 4 | 78% | 100% | 33% | 100% |
| disj_n3 | 8 | 67% | 100% | 33% | 67% |
| disj_n4 | 16 | 44% | 67% | 0% | 67% |
| disj_n5 | 32 | 22% | 67% | 0% | 0% |
| disj_n6 | 64 | 44% | 100% | 0% | 33% |
| conj_n2 | 4 | 56% | 67% | 67% | 33% |
| conj_n3 | 8 | 67% | 100% | 33% | 67% |
| conj_n4 | 16 | 44% | 100% | 0% | 33% |
| conj_n5 | 32 | 89% | 100% | 67% | 100% |
| conj_n6 | 64 | 89% | 100% | 67% | 100% |
| coupled_n2 | 3 | 89% | 100% | 67% | 100% |
| coupled_n3 | 4 | 67% | 67% | 33% | 100% |
| coupled_n4 | 5 | 67% | 100% | 33% | 67% |
| coupled_n5 | 6 | 56% | 100% | 0% | 67% |

## DeepSeek-R1 32B

| level | stable models | overall | cred (A) | skept (B) | WFS (C) |
|---|---|---|---|---|---|
| disj_n2 | 4 | 33% | 33% | 33% | 33% |
| disj_n3 | 8 | 67% | 33% | 67% | 100% |
| disj_n4 | 16 | 67% | 100% | 33% | 67% |
| disj_n5 | 32 | 67% | 33% | 67% | 100% |
| disj_n6 | 64 | 67% | 67% | 67% | 67% |
| conj_n2 | 4 | 67% | 67% | 67% | 67% |
| conj_n3 | 8 | 56% | 100% | 33% | 33% |
| conj_n4 | 16 | 56% | 67% | 33% | 67% |
| conj_n5 | 32 | 44% | 67% | 33% | 33% |
| conj_n6 | 64 | 44% | 33% | 0% | 100% |
| coupled_n2 | 3 | 67% | 67% | 67% | 67% |
| coupled_n3 | 4 | 11% | 0% | 33% | 0% |
| coupled_n4 | 5 | 33% | 33% | 67% | 0% |
| coupled_n5 | 6 | 56% | 67% | 100% | 0% |

