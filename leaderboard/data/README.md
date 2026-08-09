# Leaderboard data

All items are solver-certified. Each line is JSON. Fields: `id`, `prompt`,
`cond` (one of `none`/`closed_world`/`cred`/`skept`/`wfs`), `divergence_bin`,
`gold` (`A`/`B`/`C`, or `null` for the no-instruction `none` condition),
`rec_id` (groups the readings of one program), and difficulty metadata.

`gold` maps as: `A` = definitely yes, `B` = definitely no, `C` = cannot be
determined. The **JOINT** metric credits a program only if all four specified
readings (`closed_world`/`cred`/`skept`/`wfs`) are answered correctly.

| file | what | gold | status |
|---|---|---|---|
| `dev.jsonl` | public dev split (the paper's production set: 120 programs) | included | active |
| `hard_v3.jsonl` | **current hard set.** Mixed certified signatures (gold not guessable from the condition) + a real search family. Families: `cnf` (3-SAT near the phase transition — genuine search), `parity` (bookkeeping), `coupled` (entanglement), `decided` (stratified, gives A/B on closed-world/wfs), `loopy`, `control` | included | **active** |
| `hard_ladder.jsonl` | early difficulty ladder — cycle length + independent/interdependent cycles | included | superseded |
| `hard_v2.jsonl` | combinatorial tier (n up to 6) | included | **superseded — see below** |

Regenerate with the scripts one level up (`make_hard_v3.py`, `make_leaderboard.py`, …).

**Why v2 was superseded (found by running it).** Every hard_v2 program certifies
to the *same* signature `(cred=T, skept=F, wfs=u, sldnf=loop)`, so its gold is a
pure function of the condition name (`cred`→A, `skept`→B, `wfs`/`cw`→C). A
program-blind constant guesser therefore scores 100% JOINT, and o4-mini's 83.3%
was *below* that baseline — v2 did not test reading the program. Its
"combinatorial" axis (2ⁿ stable models) is also decided by propagation, not
search (clingo solves it with 0–1 conflicts), so it never stressed the frontier.

**hard_v3 fixes both:** it mixes certified signatures across families so the gold
varies within each condition (you must read the program), and adds `cnf` — 3-SAT
instances near the phase transition, a genuine search problem where solver
conflicts grow with size. On v3 o4-mini drops to 54.5% JOINT (cnf ≈ 0–1/11),
i.e. it finally discriminates at the frontier. Note: clingo conflicts and LLM
effort are *not* the same axis (conflict-free `coupled`/`parity` still cost the
most effort), so the difficulty filter is applied per family.

*(The paper's production set is unaffected: its four bins have different
signatures, so gold varies within each condition there — only v2 collapsed.)*

**Note.** The gold is recoverable by running a solver on the prompt, so these
files are for research / difficulty study and for driving the frontier
de-saturation experiment. The **competition** hidden test set
(`test_gold.json` / `test_public.jsonl`) is generated fresh and kept off the
public repo (regenerate with `make_leaderboard.py`).
