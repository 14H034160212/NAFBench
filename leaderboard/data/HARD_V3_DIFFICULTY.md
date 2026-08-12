# Where the difficulty lives in `hard_v3`

`hard_v3` exists to **de-saturate the frontier**: on the base set the top two
frontier models score 100% JOINT and o4-mini 80%, but on `hard_v3` o4-mini drops
to **54.5%**. This note shows *why*, with real instances from the set.

Recall the four specified readings a program is scored on (JOINT credits a
program only if **all four** are correct):

| reading | question | on a cycle-through-negation |
|---|---|---|
| `closed_world` (SLDNF) | does the goal succeed by SLD + negation-as-failure? | **loops / non-terminates → C** |
| `cred` (stable, ∃) | true in **at least one** answer set? | requires finding an answer set |
| `skept` (stable, ∀) | true in **every** answer set? | if there are **no** answer sets → **vacuously A** |
| `wfs` (well-founded) | true / false / undefined in the well-founded model? | **undefined → C** |

`A` = definitely yes, `B` = definitely no, `C` = cannot be determined.

---

## 1. The gold is **not guessable from the condition** (this is what v2 got wrong)

In the retired v2, every program shared one signature, so the gold was a pure
function of the condition name and a constant-guesser scored 100%. In v3 the gold
**varies across programs within the same reading**. Measured on the `decided`
family (30 programs), the definite answer splits:

```
cred reading, decided family:  A = 15 programs,  B = 15 programs
```

A program-blind constant guess therefore scores **50%**, not 100%. You have to
read the program.

**Worked example — `decided_d1-i0`** (small, but the answer turns on one
negation):

```
Rules:
  a1 is true if a0 is not true.       a0 is true.
  s0 is true.  s1 is true.  s2 is true.  etrue is true.
  wide is true if s0 and s1 and s2.
  q    is true if a1 and wide and etrue.
Question: is q true?
```

Two of q's three conditions (`wide`, `etrue`) are plainly true, so a careless
reader leans **A**. But `a1 :- not a0` with `a0` a **stated fact** makes `a1`
**false**, so `q` is **false → B**. All four readings agree here (signature
`FFFF`), and the whole answer flips on correctly discharging a single
negation-as-failure. `decided` is where "reading the program" pays off — and the
family every model does best on (o4-mini and Qwen3.5 both 30/30).

---

## 2. JOINT is unforgiving: the four readings usually **disagree**

```
programs whose four readings are NOT all equal:  69 / 99
```

For two-thirds of programs you must apply a **different** semantics per reading
and get **all four** right. Answer-only, per-reading accuracy looks much kinder
than JOINT (o4-mini: 85.1% per-prompt vs 54.5% JOINT) precisely because JOINT
strips coincidences.

---

## 3. The search family `cnf`: `cred` genuinely requires solving 3-SAT

This is the family that actually crushes the frontier (o4-mini **2/33**, every
open model **0/33**). Each instance is a 3-SAT formula encoded as a logic
program:

- each variable `x_i` becomes a `v_i / w_i` pair — `v_i :- not w_i`,
  `w_i :- not v_i` — a 2-cycle, so a stable model picks one side (the truth
  assignment);
- each clause becomes a constraint via an **odd loop through negation**:

```
  bad is true if w2 and w1 and w6 and (bad is not true).
  bad is true if w6 and v3 and v4 and (bad is not true).
  ... one such rule per clause ...
```

`bad :- <clause-witness>, not bad` has **no stable model** whenever its body
holds, so any assignment that violates a clause is ruled out. Hence:

> **a stable (answer) set exists  ⇔  the CNF is satisfiable.**

So `cred` ("true in ≥1 answer set?") is exactly a **3-SAT search**, and solver
effort grows with size — clingo conflicts climb from **6** at `n8` to **15** at
`n22`. Two real instances, showing all four readings diverge and the signature
changes with satisfiability:

```
cnf_n8-i0   (UNSAT, 0 answer sets)   gold = (cw:C, cred:B, skept:A, wfs:C)   ~7,000 chars
cnf_n22-i0  (SAT, 32 answer sets)    gold = (cw:C, cred:A, skept:B, wfs:C)   ~16,700 chars
```

To answer one `cnf` program correctly a model must, on the *same* prompt:
recognise the odd loop makes SLDNF **loop → C**; **solve / refute 3-SAT** for
`cred`; handle **all** answer sets for `skept`; and see WFS is **undefined → C**.
That is four different, correct semantic treatments over a genuine search
instance — no amount of pattern-matching substitutes for it.

---

## 4. The vacuous-truth trap (why answer-only scoring over-credits)

When an instance has an **odd cycle and no answer set** (e.g. `cnf_n8-i0`,
`n_stable = 0`), the skeptical answer is **vacuously "yes" (A)** — "true in every
answer set" over zero sets. A model that never notices the cycle and just
forward-chains can land on **A for the wrong reason**. The coincidence
disappears under `cred` (where "no answer set" makes the answer **B**), so a
model credited on skeptical odd-cycle items but failing the *same* programs
under credulous is revealed. JOINT, needing both, closes this loophole.

---

## 5. `loopy`: same reading, gold flips by program

Cycle-through-negation programs where the reading is fixed but the answer depends
on the actual cycle:

```
loopy_d1-i0 (skept)  gold = A   signature TTTloop   (cycle resolves true)
loopy_d1-i1 (skept)  gold = B   signature FFFloop   (cycle resolves false)
```

`closed_world` is `C` for both (SLDNF loops), but `cred`/`skept`/`wfs` flip A↔B
with the program — you cannot answer from the condition, only from resolving the
loop. This is the family where the **open models beat o4-mini** (V4-Flash 19/20,
Gemma4 16/20 vs o4-mini 11/20).

---

## Summary: what each family stresses

| family | what it stresses | o4-mini JOINT |
|---|---|---|
| `decided` | read the program; discharge negation; gold varies A/B | 30/30 |
| `loopy` | resolve a negation cycle to a definite value | 11/20 |
| `parity` / `coupled` | combinatorial bookkeeping / entanglement | 4/6, 4/4 |
| `cnf` | **genuine 3-SAT search** (cred) + 4-reading divergence | **2/33** |
| `control` | propagation-decidable baseline (many models) | 3/6 |

**Bottom line.** o4-mini's 54.5 = it still aces "read the program" (`decided`
30/30) but is crushed where the problem demands **search** (`cnf` 2/33) or
**cycle resolution** (`loopy` 11/20). Those two families are 53 of the 99
programs, and JOINT's all-four requirement turns per-reading slips into whole
zeros. That gap — search and cycles, not surface reading — is exactly what v3 was
built to expose.

*(Open question: only o4-mini has been run on `hard_v3` at the frontier. Whether
Claude Sonnet 5 / GPT-5.6 Sol also drop here — or stay near 100 — is the decisive
test of whether v3 de-saturates the true frontier, and is the next frontier run
to make.)*
