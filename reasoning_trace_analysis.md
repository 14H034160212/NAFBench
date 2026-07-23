# Reasoning-trace analysis — production run (`data/production_answers/run1`)

Analysis of the reasoning traces (`*.raw.json`) accompanying the answers for the
600-instance `production_set.json`, across the three models for which traces were
captured: **claude-sonnet-5**, **gpt-5.6-sol**, **o4-mini**.
(deepseek-r1_32b, llama3_8b, qwen2.5-coder_32b have answer files only — no traces.)

The set crosses **5 prompt conditions** (`cond`) with **4 divergence bins**:

| cond | semantics specified in prompt | maps to label |
|---|---|---|
| `none` | none ("ordinary commonsense reasoning") — probes the model default | — (`gold=None`) |
| `closed_world` | SLDNF / negation-as-failure | `sldnf` |
| `cred` | stable models, credulous (true in *some* model) | `cred` |
| `skept` | stable models, skeptical (true in *all*; no model ⇒ vacuously true) | `skept` |
| `wfs` | well-founded, 3-valued | `wfs` |

Label→answer: `T→A` (definitely yes), `F→B` (definitely no), `u`/`loop→C` (cannot be
determined). Divergence bins: `control` (all four semantics agree), and three families
of negative cycles — `even_one_sided`, `odd`, `even_both_sided` — engineered to make the
semantics disagree.

All quantitative claims below were produced by scripts over the full files; the
qualitative claims come from full reads of ~55 traces across the three models, with
several derivations re-verified against the programs with clingo.

---

## 0. Headline

- **claude-sonnet-5 and gpt-5.6-sol answer 480/480 (100%) on every specified-semantics
  condition, including all divergent cycles.** o4-mini scores **455/480 (94.8%)**.
- **The traces behind the correct answers are genuinely sound**, not lucky
  pattern-matching. Both perfect models *switch reasoning framework to match the named
  semantics* (backward SLDNF simulation for closed-world; stable-model
  construction/enumeration for cred/skept; 3-valued fixpoint for WFS).
- **o4-mini's errors are almost entirely one failure mode** (23 of 25): under WFS it
  **correctly identifies every negation cycle as undefined, then collapses that
  `undefined` to `false`** at the first positive rule that reads a cycle atom, and
  propagates a spurious "definitely no."
- The decisive distinction the paper asks for — *default-semantics leakage* vs
  *misapplication of the specified semantics* — resolves cleanly: o4-mini's WFS failures
  are **misapplication of the specified 3-valued propagation**, locally contaminated by
  the 2-valued negation-as-failure reflex ("unprovable ⇒ false"). It is **not** wholesale
  reversion to its own default — on those very instances its *default* (`none`) reasoning
  would have scored the gold.

---

## 1. Accuracy

Specified-semantics conditions (120 instances each, 480 total):

| model | closed_world | cred | skept | wfs | **all** |
|---|---|---|---|---|---|
| claude-sonnet-5 | 100% | 100% | 100% | 100% | **100%** |
| gpt-5.6-sol | 100% | 100% | 100% | 100% | **100%** |
| o4-mini | 100% | 100% | 98.3% | **80.8%** | **94.8%** |

o4-mini errors by divergence bin (specified conds): control 100%, `even_one_sided`
90.8%, `odd` 95.0%, `even_both_sided` 93.3%. Confusion is one-directional:
on WFS it produces `C→B:23` (undefined answered as "definitely no"); on skept `B→A:1`,
`B→C:1`.

---

## 2. Are the reasoning traces correct? (including behind correct answers)

### claude-sonnet-5 — sound, with two conceptual caveats
- Of the substantive traces read, **all had valid derivations; zero flawed-reasoning-
  but-correct-answer, zero "too complex / not enough info" hand-waves.** Corpus scan:
  **every one of the 180 C-answers under `wfs`/`closed_world` contains explicit
  cycle/loop/undefined vocabulary**; hand-wave phrases ("too complex", "insufficient
  information", "cannot tell") appear **0 times** across all 600.
- **29 traces are answer-only** (`ANSWER: A`, no text) — **all** on `control` instances
  with gold A. It never skips justification on a divergent/cycle case.
- Caveat (a): it frequently justifies WFS-undefinedness via **stable-model multiplicity**
  ("two competing stable models ⇒ undefined") rather than the well-founded
  unfounded-set construction. Valid on these instances (the loop atoms genuinely are
  WFS-undefined), but not a theorem in general.
- Caveat (b): its **default (`none`) semantics is a 3-valued stable-consensus**, distinct
  from strict WFS (see §4).

### gpt-5.6-sol — terse but sound
- Traces are short (median 354 chars) yet, with one exception, **complete**: 29/29
  substantive traces read were sound; clingo-verified derivations matched exactly.
- **5 of 600 traces are answer-only** (~9 chars). Three are trivial `control-cred`
  cases; **two are genuinely hard divergent skeptical cases answered with zero visible
  reasoning** (`prod-even_one_sided-i14-skept`, `prod-even_both_sided-i25-skept`) — the
  only "unverifiable but correct" outputs in the corpus (candidate limitation to note).
- Trace length tracks difficulty: median grows control 306 → odd 341 → even_one_sided
  363 → even_both_sided 388.

### o4-mini — sound on control, systematically broken on WFS undefinedness
- Correct on all control/closed_world/cred, and on **67/90 WFS undefined cases it
  reasons correctly** ("body is undefined ⇒ cq = undefined", propagated to C).
- On the **23 WFS failures the reasoning is internally coherent but semantically wrong**
  at exactly one step (§3).
- Its two skeptical errors are of two further distinct kinds (§3).

---

## 3. Reasoning strategies and failure modes

### 3.1 Strategies (both perfect models select strategy by named semantics)

| condition | strategy observed | signature |
|---|---|---|
| positive part (all conds) | forward chaining from facts | "g… true → s0..s3 → p → wide → t7,t6" |
| `closed_world` | **backward / goal-directed SLDNF simulation** | "evaluate x0 → … → x0 again → infinite recursion; neither finite success nor finite failure; flounders/loops" |
| `cred` | **stable-model construction** (one witness) | "candidate x0=T,x1=F,x2=T,x3=F … valid self-consistent model … holds in at least one answer set" |
| `skept` | **stable-model enumeration + intersection**; for odd cycles, **reduct check over all assignments** + vacuous-truth convention | "two stable models … q false in Model B … not skeptically true" |
| `wfs` | **3-valued / unfounded-set fixpoint**, undefined propagated through conjunction | "not a valid unfounded set … leaves x0..x3 undefined … true ∧ undefined = undefined" |

A keyword scan over gpt-5.6-sol's 600 traces shows near-zero vocabulary leakage:
"answer set/stable" appears 102/118 times in cred/skept and **0** in wfs/closed_world;
"undefined" appears 90 times in wfs and **0** elsewhere; SLDNF terms ("terminate/finite
fail/flounder") 93 times in closed_world and **0** elsewhere. The models are not running
one fixed procedure and relabelling it — they change procedure.

### 3.2 o4-mini's dominant failure — the `undefined → false` collapse (WFS)

The 23 WFS failures share one mechanism. o4-mini correctly derives the deterministic
part, **correctly identifies the even/odd cycle and labels x0…xn undefined** (23/23
detect the cycle), then hits `cq :- x0` with x0 undefined and writes, verbatim:

> "x0 is undefined ⇒ the only rule for cq is inapplicable ⇒ **cq is false**."
> (`prod-even_one_sided-i7-wfs`)

**22/23** failing traces contain this explicit `cq is false` step. `false` then
propagates down the entire t-chain and q comes out "definitely no" (B) instead of
"undefined" (C). The correct WFS rule — which the prompt states explicitly ("A statement
is 'undefined' if it … depends … on other undefined statements") — is that
`cq :- x0` with x0 undefined makes **cq undefined**.

Crucially, **o4-mini applies the correct rule on 67 other WFS instances of identical
structure**:

> "cq ← x0 ⇒ body is undefined ⇒ **cq = undefined** … t5 … q = undefined. ANSWER: C"
> (`prod-even_one_sided-i0-wfs`, correct)

So this is not failure to detect the cycle, and not a fixed structural trigger — it is an
**inconsistent, mid-derivation reversion to two-valued negation-as-failure** ("can't
prove it true ⇒ false"). The model has internalised both the correct 3-valued
propagation and the classical NAF collapse, and applies them unstably.

### 3.3 Diagnosis: default leakage vs misapplication of the specified semantics

The paper's key question. Two facts settle it:

1. **The wrong answer (B) is not what o4-mini's own default produces.** Its `none`
   distribution is C-heavy (74 C / 43 A / 3 B); on these one-sided/odd instances the
   default answer is **C**, matching WFS gold. So the failure is *not* the model ignoring
   the prompt and running its default semantics.
2. **The specified WFS instruction actively lowered accuracy** on the cycle families
   where the query path is conjunctive. Comparing, per instance, o4-mini's `none` answer
   against the WFS gold vs its WFS-instructed answer:

   | bin | default (`none`) vs WFS gold | WFS-instructed vs WFS gold |
   |---|---|---|
   | even_one_sided | **97%** | 70% |
   | odd | **90%** | 80% |
   | even_both_sided | 0% | **73%** |
   | control | 40% | **100%** |

   On even_one_sided/odd the model **would have done markedly better using its own
   untutored reasoning** than when told to use WFS — the explicit WFS frame is what
   triggers the `undefined→false` collapse. (On even_both_sided the reverse holds,
   because there `cq` is a *disjunction* over all cycle atoms, so the default classical
   enumerator forces `cq` true → A, missing the WFS undefined → C; the instruction helps
   there.)

**Conclusion:** o4-mini's WFS failures are **misapplication of the specified 3-valued
semantics**, not global default leakage — but the specific error is a *local* intrusion
of the 2-valued negation-as-failure reflex into an otherwise-correct WFS derivation.
This is a sharper and more interesting finding than "it fell back on its default": being
instructed to use WFS is what *induces* the mistake.

### 3.4 o4-mini's two skeptical errors — two further misapplication types

- **`prod-even_one_sided-i28-skept`** (gold B, pred A): a **hand-waved, false model
  claim** — "After computing the two stable models … one finds in both models that q is
  derived. Hence q is in every answer set. ANSWER: A." It never actually traces q's
  dependence on x0; q in fact fails in the `{x1,x3}` model. Failure = *asserting* a
  stable-model computation it did not perform.
- **`prod-even_one_sided-i29-skept`** (gold B, pred C): the model **enumerates the two
  stable models correctly** and finds "q true in M1 … q false in M2", then answers **C**
  ("true in one and false in another") instead of applying the skeptical rule the prompt
  gave ("Definitely no if there is at least one answer set in which the statement does
  not hold" → B). Failure = correct models, **wrong final quantifier** — collapsing
  model-divergence to "cannot be determined."

Both are misapplications of the *specified* decision rule, in opposite places (the model
search vs the quantifier).

---

## 4. What each model does by *default* (`none` condition)

The `none` prompt names no semantics. Distribution of answers (120 each):

- **claude-sonnet-5** and **gpt-5.6-sol**: **60 A / 60 C, never B.** Alignment with each
  semantics' gold letter: **WFS 75%, SLDNF 75%, credulous 50%, skeptical 50%.**
- **o4-mini**: 74 C / 43 A / 3 B; 18 match no semantics' label.

The two perfect models' default is a **3-valued "stable-consensus" reasoner**: assert a
definite truth value only when it is *invariant across every consistent resolution of the
cycle*, otherwise answer C. This is close to WFS/SLDNF but **demonstrably distinct from
strict WFS on multi-support cycles**: on `even_both_sided` (`cq` supported by all four
cycle atoms), both models answer **A** (cq true in every resolution) where strict WFS
says undefined→C. Neither model ever converts cycle ambiguity into "definitely no", so
neither default is skeptical-stable either. Notably, in the *default* setting they treat
odd-cycle "no stable model" as **C**, not as the vacuous-truth **A** — they only apply the
vacuous convention when the prompt explicitly names stable-model semantics.

o4-mini's default is different again: a **classical two-valued SAT enumerator** — it
solves the cycle for Boolean models ("two solutions" for even, "no consistent solution"
for odd), answers C when q varies across solutions or the system is unsatisfiable, and A
when q is forced; it occasionally invokes the closed-world assumption by name. This is why
its default is C-heavy and why it diverges most from WFS on `even_both_sided`.

---

## 5. Proposed case studies for the Appendix

A balanced, paper-ready set (verbatim excerpts below; full traces reproducible with
`data/production_answers/run1/*.raw.json`). Grouped by what each demonstrates.

### Group A — Correct reasoning, strategy adapts to the named semantics

**CS-A1 (flagship): credulous vs skeptical on one program.**
`claude-sonnet-5`, `prod-even_one_sided-i0` — `cred` (gold A) and `skept` (gold B),
identical program. Cred *constructs a witness*; skept *enumerates both models and
applies the cautious quantifier*.
> cred: "Testing candidate: x0=T, x1=F, x2=T, x3=F … a valid, self-consistent stable
> model … credulous/brave reasoning only requires q to hold in at least one answer set.
> ANSWER: A"
> skept: "exactly two stable models … In Model B: x0 false → cq not derivable … q false
> … Since there exists at least one answer set where q does not hold, skeptical/cautious
> reasoning requires answering 'Definitely no.' ANSWER: B"

**CS-A2: odd-cycle vacuous-truth, split by quantifier.**
`claude-sonnet-5`, `prod-odd-i0` — `skept` (gold A) vs `cred` (gold B). Exhaustive reduct
check over all 8 assignments, then the no-model convention applied both ways.
> skept: "Every possible assignment leads to a contradiction … has no answer sets … if
> the program has no answer sets, every statement vacuously holds … 'q is true' vacuously
> holds. ANSWER: A"
> cred: "no answer sets at all … this applies to every query … ANSWER: B"

**CS-A3: genuine well-founded (unfounded-set) reasoning.**
`claude-sonnet-5`, `prod-even_both_sided-i0-wfs` (gold C). Correct 3-valued propagation.
> "if we assume all of {x0,x1,x2,x3} are false, then each 'not' condition becomes true,
> which would actually derive each atom as true — a contradiction. So the set … is not a
> valid unfounded set … well-founded semantics leaves x0,x1,x2,x3 all undefined … t5 =
> t6 ∧ cq = true ∧ undefined = undefined … q = undefined. ANSWER: C"

**CS-A4: SLDNF floundering/loop (operational vocabulary).**
`claude-sonnet-5`, `prod-even_one_sided-i0-closed_world` (gold C).
> "To evaluate x0 … must evaluate x1 … must evaluate x0 again. This returns to the
> original goal x0, creating infinite recursion. In Prolog-style SLDNF resolution, this
> does not terminate — neither a finite success nor a finite failure … the goal
> flounders/loops indefinitely. ANSWER: C"

**CS-A5: terse-but-sound (compression without loss).**
`gpt-5.6-sol`, `prod-odd-i11-wfs` (gold C), 356 chars; and the cred/skept pair
`prod-even_one_sided-i7` (A / B). Shows a very short trace still names the exact cycle and
switches quantifier.
> wfs: "x0, x1, and x2 form an unresolved cycle through default negation … Thus x0 is
> undefined, making cq undefined. Consequently … q … undefined. ANSWER: C"
> skept: "{x0,x2}: … q is true. {x1,x3}: … q is false. Since q is false in at least one
> answer set, it is not skeptically true. ANSWER: B"

### Group B — Failure case studies (o4-mini)

**CS-B1 (flagship failure): the `undefined → false` collapse, with its own contrast.**
`o4-mini`, `prod-even_one_sided-i7-wfs` (gold C, **pred B, wrong**) beside
`prod-even_one_sided-i0-wfs` (gold C, **pred C, correct**) — same model, same structure,
opposite treatment of the identical `cq :- x0` step.
> wrong: "This even negation cycle yields all xi undefined … cq ← x0. x0 is undefined ⇒
> the only rule for cq is inapplicable ⇒ **cq is false** … q is definitely false. ANSWER: B"
> correct: "cq ← x0 ⇒ body is undefined ⇒ **cq = undefined** … q = undefined. ANSWER: C"

**CS-B2: skeptical reasoning by assertion (bogus model claim).**
`o4-mini`, `prod-even_one_sided-i28-skept` (gold B, pred A).
> "After computing the two stable models … one finds in both models that q is derived.
> Hence q is in every answer set. ANSWER: A"
> (In fact q fails in the `{x1,x3}` model — the claimed computation was never done.)

**CS-B3: right models, wrong quantifier.**
`o4-mini`, `prod-even_one_sided-i29-skept` (gold B, pred C).
> "M1={x0,x2,…} and M2={x1,x3,…}. – In M1: x0 true, hence q true. – In M2: x0 false,
> hence q false. Since q is true in one answer set and false in another, it is not true
> in every … and not false in every … ANSWER: C"
> (Skeptical rule → B: q fails in some model.)

### Group C — Default-semantics diagnostics (`none`)

**CS-C1: the default is a 3-valued consensus, not strict WFS.**
`claude-sonnet-5`, `prod-even_both_sided-i0-none` (→ A) vs `prod-even_one_sided-i0-none`
(→ C), same t/cq scaffold, differing only in `cq`'s support.
> even_both_sided: "In every consistent resolution of the cycle, cq is true … q is true
> in every consistent scenario … ANSWER: A" — where strict WFS makes cq undefined → C.
> even_one_sided: "x0 (and hence cq, and hence q) cannot be resolved to a definite truth
> value … ANSWER: C"

**CS-C2: o4-mini's default is a classical SAT enumerator + "varies ⇒ C".**
`o4-mini`, `prod-odd-i1-none` and `prod-even_one_sided-i1-none`.
> odd: "This system has no consistent Boolean solution … x0 can neither be determined
> true nor false … ANSWER: C"
> even_one_sided: "q can end up true or false depending on which consistent assignment
> one picks … cannot be determined … ANSWER: C" (also names "the usual closed-world
> assumption").

### Group D — Limitation note (optional)

**CS-D1: unverifiable-but-correct terse output.**
`gpt-5.6-sol`, `prod-even_one_sided-i14-skept` (gold B): the entire trace is `ANSWER: B`.
Correct, but a hard divergent case with no auditable reasoning — the only such gap in the
perfect models. Useful to acknowledge as a scoring caveat.

---

## 6. Suggested framing for the paper

1. **Frontier models solve the semantics-selection task, and do so for the right
   reasons.** The traces are not post-hoc: strategy vocabulary is cleanly partitioned by
   condition, and derivations verify against clingo. This supports a claim stronger than
   accuracy alone — the models represent the *procedure* each semantics prescribes.
2. **The remaining hard edge is the third truth value.** o4-mini's failures localise to a
   single, nameable error: collapsing WFS `undefined` to `false` (2-valued NAF intrusion),
   applied inconsistently even within one model. This is a crisp, quotable phenomenon.
3. **"Being told the semantics" can hurt.** The `none`-vs-`wfs` comparison for o4-mini
   (97%→70% on even_one_sided) is a compact result: an explicit WFS instruction *induced*
   the collapse that the model's own default avoided.
4. **The default negation semantics of frontier models is a 3-valued stable-consensus,
   not any single textbook semantics** — closest to WFS/SLDNF (75%) but distinct from all
   four labels on multi-support cycles, and never skeptical (never answers B by default).

---
---

# Part II — Open-source models (deepseek-r1_32b, llama3_8b, qwen2.5-coder_32b)

Traces were later added for the three open-source models. Analysis method identical to
Part I (full-corpus scripts + close reads of ~30–40 traces per model, several derivations
re-verified with clingo).

## 7. File format / script compatibility

**Format is unchanged.** Answers are still `{task_id: letter}`; raw traces still
`{task_id: string}`, keyed by the full 600 task-id set. deepseek is a *reasoning* model —
its traces carry `<think>…</think>` blocks and its answer file has an extra
`rescued_with: "parse_answer_reasoning"` key (the letter was extracted from free-form
prose). No structural script change was needed; two additions only:

- **`None` answers** (parse failures / non-committal outputs) must be counted separately:
  deepseek 53, llama3 25, qwen 9 on the specified conditions. "Accuracy of parsed answers"
  below uses the non-null denominator; strict accuracy (null = wrong) is also given.
- deepseek's `<think>` blocks are stripped for the "visible conclusion" but kept for the
  reasoning-content scans.

The frontier answer files were re-saved during this update but their answers and raw
traces are **byte-identical** to Part I (re-verified: 480/480, 480/480, 455/480). Part I
stands unchanged.

## 8. Accuracy (all six models)

Accuracy of **parsed** answers on the specified-semantics conditions (non-null
denominator), with null counts:

| model | closed_world | cred | skept | wfs | all-parsed | null | strict (null=wrong) |
|---|---|---|---|---|---|---|---|
| claude-sonnet-5 | 100% | 100% | 100% | 100% | **100%** | 0 | 100% |
| gpt-5.6-sol | 100% | 100% | 100% | 100% | **100%** | 0 | 100% |
| o4-mini | 100% | 100% | 98% | 81% | **94.8%** | 0 | 94.8% |
| qwen2.5-coder_32b | 59% | 72% | 61% | 74% | **66.5%** | 8 | 65.4% |
| deepseek-r1_32b | 43% | 72% | 64% | 31% | **52.5%** | 53 | 46.7% |
| llama3_8b | 31% | 62% | 67% | 36% | **49.2%** | 25 | 46.7% |

By divergence bin (parsed), the open-source models all hold up on `control` (no negative
cycle) and collapse on the cycle bins — the failure is specifically about negation cycles:

| model | control | even_one_sided | odd | even_both_sided |
|---|---|---|---|---|
| qwen | 65% | 67% | 62% | 72% |
| deepseek | 81% | 38% | 52% | 35% |
| llama3 | 78% | 30% | 37% | 51% |

(qwen is the exception — roughly flat across bins, i.e. it actually engages the cycles;
see §10. Its lower control number comes from an unrelated closure gap, also §10.)

## 9. Does the model engage the specified semantics? (unified vocabulary scan)

Fraction of traces per condition whose text uses the vocabulary of each semantics, plus
whether it *detects the cycle at all* (the load-bearing column):

| model | cw→SLDNF | cred/skept→"answer set" | wfs→"undefined" | **detects cycle** (avg over conds) |
|---|---|---|---|---|
| claude-sonnet-5 | 115/120 | 117 / 114 | 105/120 | ~102/120 |
| gpt-5.6-sol | 93/120 | 100 / 118 | 90/120 | ~88/120 |
| o4-mini | 112/120 | 116 / 119 | 104/120 | ~93/120 |
| qwen2.5-coder_32b | 24/120 | 119 / 117 | 105/120 | ~66/120 |
| deepseek-r1_32b | 29/120 | 59 / 63 | 118/120 | ~84/120 |
| llama3_8b | 7/120 | 35 / 81 | 35/120 | **~2–23/120** |

Reading: the three frontier models cleanly re-tool per preamble AND detect the cycle
almost always. qwen instantiates the stable-model and WFS apparatus strongly (but not
SLDNF). deepseek reaches for WFS vocabulary heavily (118/120) yet — see §10 — miscomputes
it. **llama3 barely perceives the cycles at all** (2–23/120), which is the root of its
behavior. Engagement is necessary but not sufficient: deepseek is the counterexample
(high WFS vocabulary, lowest WFS accuracy).

## 10. Per-model findings

### qwen2.5-coder_32b — the one OSS model whose instruction-following works

- **Reasoning is genuinely analytical** (forward-chains the full positive graph
  correctly; errors localize to negation), and it **reads the preamble and instantiates
  the named apparatus** — which is *why the instruction helps it* and not the others
  (per-bin default→instructed jumps, e.g. WFS even_one_sided 9/30→27/30, cred control
  10→29). Of ~40 traces read: ~14 sound, ~3 correct-letter-by-shortcut, ~33 wrong, 8 null.
- **WFS success is sound undefined-propagation, not "cycle→C" reflex.** It isolates the
  cycle, marks it undefined, and propagates undefined up the *specific* chain to q
  (CS-E1). Confirmed by the fact that it still answers A when q does not route through the
  cycle.
- **Two dominant failure modes:**
  1. **Cycle-resolution-by-model-picking (~53% of errors).** It resolves a negation cycle
     to *one* optimistic 2-valued assignment that makes q derivable, then forward-chains
     to A. This produces the whole `B→A` pattern and most `C→A`. Split by parity: for
     **skept-even** it builds a *real* stable model where q holds but stops at one and
     over-applies "every" (**incomplete search**, CS-E2); for **cred-odd** it fabricates
     an assignment for a program with *no* stable model and never runs the stability check
     (**default-leak in ASP clothing**, CS-E3 — verbatim: *"since we are using credulous
     reasoning … we assume the most favorable conditions that allow for q to be true"*).
  2. **Negation-as-failure closure gap (~24%).** For `cq :- not blocked` with `blocked`
     undefined-by-a-rule, it refuses to close the world and answers C ("no information …
     cannot determine") where CWA gives A. Fixed by *procedural* NAF phrasing
     (cred/skept/cw control 10→29/21/20) but not by WFS's abstract wording (10→8).
- **Default (`none`):** positive-only reasoning; "unknown atom → cannot determine";
  "cycle → guess a model → yes". Every preamble that supplies a negation rule therefore
  adds capability qwen lacks by default — hence instruction helps.

### deepseek-r1_32b — reads the preamble; loses it at the commitment step

- **It is not applying a fixed default:** the same program gets up to 4 distinct letters
  across the 5 preambles, and its letter differs from its own `none` default in 56–70% of
  groups. WFS vocabulary fires in 118/120.
- **The signature phenomenon is a large reasoning-vs-answer gap.** Among the 90 WFS
  gold=C instances, **80% (72/90) of traces contain undefined-language somewhere, but only
  23 commit to "C".** The other 49 divide into:
  - **undefined reached, mis-committed / mis-parsed → B or null** (e.g. "cannot be
    *uniquely* determined … either true or false" → scored B; boxed "None of the
    conclusions can be drawn" → null). Extraction/verbalization tax.
  - **undefined mentioned, then self-overridden by model-picking → A** (16 of the 30
    `C→A`): it notes the cycle is undefined in `<think>`, then picks x0=true and
    forward-chains.
  - **genuine undefined→false collapse → B** ("t5 is undefined, *effectively false*").
- **So deepseek's WFS confusion `C→A:30 / C→B:27 / C→C:23` is NOT a clean 3-way semantic
  split** (contrast o4-mini): `C→C` correct; `C→B` a mix of genuine collapse and
  mis-committed-undefined; `C→A` genuine model-picking. Crediting *reached-undefined*
  reasoning would raise effective WFS competence to ~80%, but ~30 model-picking cases
  remain true errors.
- **Other misapplications:** credulous "∃-model → yes" almost never fired even when both
  models were enumerated ("both solutions valid … q could be either true or false" — a
  credulous YES scored B); skeptical vacuous-truth convention ignored (finds "no stable
  models" then answers "No"); and **closed_world run with stable-model machinery** rather
  than SLDNF (loop→C reasoning is rare; it "solves" the cycle to a model instead).
- **Nulls (53):** 12 truncated at the 8192-token cap (over-deliberation on the hardest
  cycles), 41 finished `</think>` but emitted no parseable letter (undefined stated as
  prose, or degenerate output). One trace **derailed into an unrelated puzzle** entirely
  (raining/shining). Nulls are generation/commitment failures, not abstentions.
- **Default (`none`):** a latent 3-valued instinct already present (reaches "cannot be
  determined" on cycles with no preamble); the WFS preamble *reinforces* it, while
  cred/skept/cw must *override* it — which is where the quantifier/convention errors enter.

### llama3_8b — largely ignores the negation cycle (and the preamble)

- **The preamble mostly does not change the method**, only surface vocabulary. On the
  identical-program comparison the letter is unchanged from the `none` default in 57–67%
  of groups, and the largest instructed movement is the *wrong* direction `C→A`. Its
  cred/skept traces say "answer set" (35/81 of 120) but **never enumerate models**; its
  closed_world traces produce essentially no SLDNF vocabulary (7/120).
- **Dominant failure: negation-cycle-ignored (~55–60% of errors)** — it forward-chains
  `q←t0←…←cq←x0` and asserts x0 true without ever processing the x-rules (in `C→A`
  errors the cycle is *named* in only ~1–7% of traces). Secondary: hallucinated
  justification to close a negation (~20%), cycle-detected-but-mishandled (~10%),
  and rare and/or-arithmetic slips.
- **It is heavily "yes"-biased** (overall A:457 / C:95 / B:23; default A:89/C:29/B:2). It
  reaches C almost only via a *grounding gap* ("no rule connects t6 to anything") or an
  unknown `not blocked`, and reaches B almost only via cycle-as-contradiction (its single
  sound B route, CS-G4).
- **Nulls (25) are degenerate generation, not abstention:** median 9.3k chars, runaway
  repetition, or hallucinated atoms (`t8 … t53`); 24/25 have no `ANSWER:` line.
- **Control 78% vs cycle bins 30–51%** confirms the model is competent at plain
  conjunction/derivation and fails specifically at the negation cycles every preamble is
  trying to steer.

## 11. Cross-model failure-mode synthesis (default-leak vs misapplication)

Placing every model on the paper's axis:

| model | primary failure | default-leak or misapplication? |
|---|---|---|
| o4-mini | WFS undefined→false collapse | **misapplication** of specified WFS (local 2-valued NAF intrusion); the instruction *induces* it |
| qwen | cycle→pick-one-model→yes; NAF closure gap | **both**: incomplete search (skept-even) vs default-leak dressed as ASP (cred-odd) |
| deepseek | reasoning-vs-answer gap; model-picking; convention errors | **misapplication + a verbalization/extraction layer**; not a fixed default (preamble clearly steers it) |
| llama3 | negation cycle ignored; yes-bias | **default-leak**: the preamble rarely changes the method; it runs its positive-chaining default regardless |

The clean gradient: **claude/gpt** represent the procedure correctly; **o4-mini** applies
the right procedure with one unstable step; **qwen** engages the procedure but searches
incompletely; **deepseek** conceives the procedure but cannot commit its own conclusion;
**llama3** mostly never leaves its positive-chaining default. Cycle-detection rate (§9)
predicts this ordering.

## 12. Data-quality findings (recommend fixing before publication)

Two extraction issues surfaced; both are in `nafbench/answer.py`. The frontier answer
files were re-parsed with the current code and are clean; the **open-source answer
`.json` files predate the fix** (dated 2026-07-15 vs the raw traces 2026-07-22).

1. **llama3: 5 stale mis-parses (`ANSWER`-word bug).** The pre-fix regex captured the "A"
   of the word "ANSWER" when a lowercase "answer:" appeared in prose just before the real
   `ANSWER: X` line. Affected (all recorded A, real letter differs): `prod-odd-i2-cred`
   (→C), `prod-odd-i5-skept` (→B), `prod-odd-i14-closed_world` (→B),
   `prod-even_both_sided-i16-skept` (→B), `prod-even_both_sided-i18-skept` (→C). **3 of 5
   change correctness.** The current `ANSWER_RE` (with the `(?![A-Za-z])` guard,
   `answer.py:9`) already fixes this — **just re-parse the OSS files**. Affects only
   llama3; other models are clean under re-extraction.
2. **deepseek: keyword extraction under-credits "undefined" conclusions.**
   `parse_answer_reasoning` (`answer.py:59–90`) maps free-form prose to A/B/C via keyword
   lists (`_C_KEYS`/`_B_KEYS`). Real deepseek conclusions such as "cannot be *uniquely*
   determined", "either true or false", boxed "None of the conclusions…", or boxed "1"
   are not caught by `_C_KEYS` and fall through to B or null. This inflates deepseek's `B`
   and `None` counts and understates its WFS competence (§10). This is inherent to
   keyword extraction on reasoning-model prose. Recommendation: either report deepseek's
   reasoning-vs-answer gap explicitly in the paper, or extend `_C_KEYS`
   ("cannot be uniquely determined", "either true or false", "underdetermined",
   "no unique") — and note that any such change should be applied uniformly and
   re-validated, since "either true or false" is genuinely ambiguous between C (undefined)
   and a hedge.

## 13. Open-source case studies for the appendix

**CS-E1 (qwen WFS-success, sound undefined-propagation).**
`qwen2.5-coder_32b`, `prod-even_one_sided-i2-wfs` (gold C, pred C).
> "This creates a cycle: x0 depends on x1 … depends back on x0 … the truth value of cq is
> undefined. Since t5 requires both t6 and cq to be true, and cq is undefined, t5 is also
> undefined. Consequently, t4, t3, t2, t1, and t0 are all undefined … q is also undefined.
> ANSWER: C"

**CS-E2 (qwen skeptical B→A, incomplete model search).**
`qwen2.5-coder_32b`, `prod-even_one_sided-i0-skept` (gold B, pred A). clingo: two models
`{x0,x2}` (q true) and `{x1,x3}` (q false); qwen builds only the first.
> "the simplest consistent scenario would be where x0 and x2 are true … there's no
> contradiction that would make q false in any answer set, the statement holds in every
> answer set. ANSWER: A"

**CS-E3 (qwen credulous B→A, default-leak as ASP).**
`qwen2.5-coder_32b`, `prod-odd-i2-cred` (gold B — odd cycle, 0 stable models, pred A).
> "since we are using credulous reasoning (brave reasoning), we assume the most favorable
> conditions that allow for q to be true. We can assume x1 is false, which makes x2 false,
> making x0 true … ANSWER: A"  (no answer-set-existence check)

**CS-F1 (deepseek reasoning-vs-answer gap — the flagship OSS exhibit).**
`deepseek-r1_32b`, `prod-even_one_sided-i0-wfs` (gold C, scored B).
> "\(q\) does not have a uniquely determined truth value … underdetermined and can be
> either true or false … **Final Answer**: the truth value of q cannot be uniquely
> determined; it depends on the assignment of x0."  → extractor scores **B**.

**CS-F2 (deepseek undefined→false collapse, stated in one line).**
`deepseek-r1_32b`, `prod-even_one_sided-i18-wfs` (gold C, scored B).
> "In Well-Founded semantics, this makes t5 undefined … Since t5 is undefined
> (**effectively false**) … remains false."

**CS-F3 (deepseek instruction-sensitivity, one program × five preambles).**
`deepseek-r1_32b`, `prod-even_one_sided-i0-{none,closed_world,cred,skept,wfs}` → letters
C / A / A / B / B. Shows the preamble genuinely steers the model (cred & skept both
correct via model enumeration), while closed_world picks a model instead of loop→C and
wfs reaches "underdetermined" but is scored B.

**CS-G1 (llama3 canonical failure — cycle ignored).**
`llama3_8b`, `prod-even_one_sided-i0-wfs` (gold C, pred A). The x0–x3 cycle that makes q
undefined is never mentioned:
> "proposition t6 is true, which means t5 is also true … t4 … t1 … t0 is also true.
> ANSWER: A"

**CS-G4 (llama3 sole sound B — cycle-as-contradiction).**
`llama3_8b`, `prod-odd-i22-cred` (gold B, pred B). clingo: 0 answer sets.
> "we have a loop: x0 implies ¬x0, and ¬x0 implies x0. This is a contradiction … there are
> no answer sets … q is false in all possible worlds. ANSWER: B"

**CS-G5 (llama3 null = degenerate generation, not abstention).**
`llama3_8b`, `prod-control-i29-cred` (null): hallucinates non-existent atoms t8…t53 and
never emits an `ANSWER:` line.

## 14. Updated framing for the paper

- **The benchmark cleanly separates six models along one axis — how they handle negation
  cycles** — while all remain competent on the acyclic control programs. Control accuracy
  is 65–100% for every model; the spread opens only on the cycle bins.
- **Frontier vs open-source is a difference in kind, not degree, at the third truth value
  and the model-quantifier.** claude/gpt/o4-mini re-tool per semantics and detect the
  cycle ~always; only o4-mini stumbles, and only on WFS-undefined. The OSS models fail
  earlier and more variously.
- **Instruction-following is itself a finding.** It *helps* qwen (which reads and
  instantiates the preamble), is *mixed* for deepseek (reads it, mis-commits), *hurts*
  o4-mini on one-sided WFS (induces the collapse), and is *near-inert* for llama3 (runs
  its default regardless). "Name the semantics in the prompt" is not uniformly beneficial.
- **Reasoning-model caveat:** deepseek shows that answer *accuracy* can badly understate
  reasoning *competence* when the model cannot render its own conclusion as a clean label
  — an argument for scoring reasoning traces (as done here), not just final letters.
- **Fix the two extraction issues (§12) before reporting OSS numbers**; llama3's is a
  one-line re-parse, deepseek's warrants an explicit reasoning-vs-answer treatment.
