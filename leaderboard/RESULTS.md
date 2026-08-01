# NAF-Bench Leaderboard — diagnostic board (v1)

Primary metric: **JOINT accuracy** — a program counts only if the model
answers all four readings (SLDNF / WFS / credulous / skeptical) correctly.
Scored on the paper's evaluation set (120 programs). The frontier is jointly
saturated by design; a harder hidden tier is in preparation.

| # | Model | Open | JOINT % | per-prompt % | cred | skept | WFS | SLDNF | fmt-valid |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Claude Sonnet 5 | — | **100.0** | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| 2 | GPT-5.6 Sol | — | **100.0** | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| 3 | o4-mini | — | **80.0** | 94.8 | 100.0 | 98.3 | 80.8 | 100.0 | 100.0 |
| 4 | Qwen2.5-Coder 32B | ✓ | **12.5** | 65.4 | 70.8 | 60.8 | 71.7 | 58.3 | 100.0 |
| 5 | Llama3 8B | ✓ | **8.3** | 46.0 | 59.2 | 61.7 | 35.0 | 28.3 | 100.0 |
| 6 | DeepSeek-R1 32B | ✓ | **5.8** | 46.7 | 63.3 | 56.7 | 28.3 | 38.3 | 100.0 |

JOINT by divergence bin (control / even-1 / odd / even-2):

| Model | control | even-1 | odd | even-2 |
|---|---|---|---|---|
| Claude Sonnet 5 | 100.0 | 100.0 | 100.0 | 100.0 |
| GPT-5.6 Sol | 100.0 | 100.0 | 100.0 | 100.0 |
| o4-mini | 100.0 | 66.7 | 80.0 | 73.3 |
| Qwen2.5-Coder 32B | 16.7 | 6.7 | 3.3 | 23.3 |
| Llama3 8B | 30.0 | 0.0 | 0.0 | 3.3 |
| DeepSeek-R1 32B | 23.3 | 0.0 | 0.0 | 0.0 |
