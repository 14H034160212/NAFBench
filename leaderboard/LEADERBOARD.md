# NAF-Bench Leaderboard

Primary metric: **JOINT accuracy** (a program counts only if all four
specified readings are correct). Scored server-side against a hidden test
set (`hard`: 385 prompts; the prohibitively-large 3-SAT instances
`cnf_n14`/`cnf_n22` are excluded as uninformative).

## Results

| # | team | JOINT % | trace-sound %ᵃᵘˣ | per-prompt % | sldnf | cred | skept | wfs |
|---|---|---|---|---|---|---|---|---|
| 1 | claude-sonnet-5 | **89.6** | – | 96.8 | 100.0 | 94.8 | 92.2 | 100.0 |
| 2 | gemma4-31b | **75.3** | 84.9 | 90.6 | 100.0 | 85.7 | 77.9 | 98.7 |
| 3 | o4-mini | **74.0** | – | 91.9 | 100.0 | 89.6 | 88.3 | 89.6 |
| 4 | deepseek-r1-32b | **41.6** | 72.2 | 67.9 | 85.7 | 62.3 | 58.4 | 64.9 |
| 5 | qwen2.5-coder-32b | **31.2** | 41.8 | 65.3 | 74.0 | 59.7 | 59.7 | 67.5 |
| 6 | constant-baseline | **22.1** | – | 53.6 | 61.0 | 57.1 | 61.0 | 35.1 |
| 7 | llama3-8b | **2.6** | 24.6 | 43.5 | 35.1 | 51.9 | 42.9 | 44.2 |

> Ranking is by **JOINT %** only.

> **trace-sound %ᵃᵘˣ** is *auxiliary information, not a ranking criterion.* Of the programs a model got right *and* submitted a reasoning `trace` for, the share whose trace commits to the certified query verdict (and, on odd cycles, registers that there is no stable model). The check is **regex-based and imperfect — a rough approximation of soundness**, not a verified proof audit. `–` = answer-only submission.

