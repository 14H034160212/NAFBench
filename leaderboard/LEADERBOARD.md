# NAF-Bench Leaderboard

Primary metric: **JOINT accuracy** (a program counts only if all four
specified readings are correct). Scored server-side against a hidden test
set. Three subtasks by context budget: `8k-lite` ⊂ `16k` ⊂ `full`.

## Subtask: `8k-lite`

| # | team | JOINT % | reasoned soundly % | per-prompt % | sldnf | cred | skept | wfs |
|---|---|---|---|---|---|---|---|---|
| 1 | deepseek-r1-32b | **41.6** | 72.2 | 67.9 | 85.7 | 62.3 | 58.4 | 64.9 |
| 2 | qwen2.5-coder-32b | **31.2** | 41.8 | 65.3 | 74.0 | 59.7 | 59.7 | 67.5 |
| 3 | constant-baseline | **22.1** | – | 53.6 | 61.0 | 57.1 | 61.0 | 35.1 |
| 4 | llama3-8b | **2.6** | 24.6 | 43.5 | 35.1 | 51.9 | 42.9 | 44.2 |

## Subtask: `16k`

| # | team | JOINT % | reasoned soundly % | per-prompt % | sldnf | cred | skept | wfs |
|---|---|---|---|---|---|---|---|---|
| 1 | deepseek-r1-32b | **36.4** | 69.7 | 64.8 | 85.2 | 58.0 | 53.4 | 62.5 |
| 2 | qwen2.5-coder-32b | **29.5** | 40.1 | 65.9 | 77.3 | 59.1 | 55.7 | 71.6 |
| 3 | constant-baseline | **20.5** | – | 55.7 | 65.9 | 55.7 | 58.0 | 43.2 |
| 4 | llama3-8b | **3.4** | 24.7 | 44.9 | 33.0 | 52.3 | 45.5 | 48.9 |

## Subtask: `full`

| # | team | JOINT % | reasoned soundly % | per-prompt % | sldnf | cred | skept | wfs |
|---|---|---|---|---|---|---|---|---|
| 1 | deepseek-r1-32b | **32.3** | 69.3 | 63.4 | 85.9 | 54.5 | 49.5 | 63.6 |
| 2 | qwen2.5-coder-32b | **27.3** | 38.4 | 66.4 | 79.8 | 58.6 | 52.5 | 74.7 |
| 3 | constant-baseline | **19.2** | – | 57.3 | 69.7 | 54.5 | 55.6 | 49.5 |
| 4 | llama3-8b | **3.0** | 22.6 | 44.7 | 35.4 | 49.5 | 45.5 | 48.5 |

> **reasoned soundly %** (v1): of the programs a model got right *and* submitted a reasoning `trace` for, the share whose trace commits to the certified query verdict (and, on odd cycles, registers that there is no stable model). `–` = answer-only submission. Audits the query verdict + odd-cycle recognition against the private certification; the fuller per-atom audit is a follow-up.

