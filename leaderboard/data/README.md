# Leaderboard data

All items are solver-certified. Each line is JSON. Fields: `id`, `prompt`,
`cond` (one of `none`/`closed_world`/`cred`/`skept`/`wfs`), `divergence_bin`,
`gold` (`A`/`B`/`C`, or `null` for the no-instruction `none` condition),
`rec_id` (groups the readings of one program), and difficulty metadata.

`gold` maps as: `A` = definitely yes, `B` = definitely no, `C` = cannot be
determined. The **JOINT** metric credits a program only if all four specified
readings (`closed_world`/`cred`/`skept`/`wfs`) are answered correctly.

| file | what | gold |
|---|---|---|
| `dev.jsonl` | public dev split (the paper's production set: 120 programs) | included |
| `hard_ladder.jsonl` | difficulty ladder — cycle length {4,6,8,10} + independent/interdependent cycles n=2..4 | included |
| `hard_v2.jsonl` | harder tier — combinatorial axis pushed to n=6 (2⁶=64 stable models); disjunctive (skeptical-hard), conjunctive (credulous-hard), interdependent, + cycle-length control | included |

Regenerate any of these with the scripts one level up
(`make_leaderboard.py`, `make_hard_tier.py`, `make_hard_v2.py`).

**Difficulty design.** A negation cycle is a "coin" with two stable states; the
query's answer under skeptical/credulous semantics requires reasoning over all
2ⁿ stable models of n independent cycles. The **combinatorial axis (number of
cycles)** is the intended hardening lever — skeptical must find the single world
in 2ⁿ where the query fails, which is where models are expected to drop as n
grows. **Cycle length** (a longer single loop, still 2 models) is a control.

**Note.** The gold is recoverable by running a solver on the prompt, so these
files are for research / difficulty study and for driving the frontier
de-saturation experiment. The **competition** hidden test set
(`test_gold.json` / `test_public.jsonl`) is generated fresh and kept off the
public repo (regenerate with `make_leaderboard.py`).
