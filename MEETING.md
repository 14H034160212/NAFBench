# NAF-Bench — progress for today's meeting

**What it is.** A *solver-certified* benchmark testing whether an LLM will **follow a specified negation semantics** (a "rulebook" for what *not* / *unknown* mean) instead of reverting to its own default. Every item's gold answer is computed by a real solver (clingo / well-founded fixpoint / SWI-Prolog), never by us.

---

## 1. Progress since the last meeting

- **Independent audit (Fable) — all findings addressed.** Two correctness bugs fixed (a conjunction rendered "only if" instead of "if"; a Prolog loop-detection race that could mis-certify a cycle as "false"), plus statistics/design fixes (see §5).
- **Everything regenerated and re-run on the corrected code** — gold labels verified unchanged (zero drift), all models re-run, every LoRA adapter retrained. Every experiment now logs completion tokens.
- **Reverted "width" to shared-subgoals-only** (cycle length decoupled), per Agnieszka. Re-ran the depth×width grid with the local models: **conclusion unchanged** — accuracy is flat in depth and width; the *divergence bin* (which kind of cycle) dominates.
- **Adopted Agnieszka's revised, detail-matched semantics prompts** (§3) and smoke-tested them (§4).
- **Related work positioned**, incl. ASPBench (arXiv:2507.19749). All pushed to `main`.

---

## 2. The one example that shows the whole point

Same rules, rendered in plain English (this is what a model sees):

> Reviewer 0 signs off **if and only if** Reviewer 1 does **not**. Reviewer 1 signs off **if and only if** Reviewer 0 does **not**. The case is ESCALATED if Reviewer 0 signs off.
>
> **Question: Is the case ESCALATED?**

The two reviewers prop each other up in a loop, so the four rulebooks legitimately **disagree** — and the certified answer flips accordingly:

| Rulebook (semantics) | Certified answer | Why |
|---|---|---|
| **credulous** (brave) | **Definitely yes (A)** | two consistent scenarios {R0} and {R1}; escalated in the R0 scenario → holds in *at least one* |
| **skeptical** (cautious) | **Definitely no (B)** | in the R1 scenario it is *not* escalated → *not* in every scenario |
| **well-founded** | **Cannot be determined (C)** | the loop is ungrounded → *undefined* |
| **closed-world / SLDNF** | **Cannot be determined (C)** | the operational proof does not terminate |

One set of rules, four different correct answers depending on the rulebook you were told to use. A model that "reverts to default" will give the same answer regardless — that failure is exactly what NAF-Bench measures.

---

## 3. The four prompts (Agnieszka's revised, detail-matched set)

Each prompt is a **self-contained operational definition**, so we test whether a model can *follow* the semantics, not whether it already knows the name. Below: the prompt, a one-line gloss, and its answer on the example above.

### closed-world / SLDNF → C on the example
> Use the CLOSED-WORLD ASSUMPTION with NEGATION-AS-FAILURE, interpreted operationally as in Prolog-style reasoning. A positive goal is 'true' if it can be derived by a terminating proof from the rules… `not G` is 'true' if G finitely fails… If evaluating the goal does not terminate, flounders, or otherwise cannot produce a definite success or finite failure, answer 'Cannot be determined.'

*Gloss:* run it like a Prolog engine; if it loops or gets stuck, it's undetermined.

### well-founded → C on the example
> Use WELL-FOUNDED semantics, with three truth values: 'true', 'false', 'undefined'. A statement is 'true' if it has *founded* support… 'false' if all rules that could derive it are defeated or depend only on unfounded circular support… 'undefined' if its truth depends on an unresolved cycle through default negation. … For `not G`, use the well-founded value of G.

*Gloss:* only count truth that's ultimately grounded in facts; circular-through-negation → undefined.

### credulous / brave → A on the example
> Use STABLE-MODEL (ANSWER-SET) semantics with CREDULOUS (BRAVE) reasoning. An answer set is a self-consistent set of atoms closed under the rules and containing exactly the atoms justified by them… Answer 'Definitely yes' if the statement holds in AT LEAST ONE answer set; 'Definitely no' if in none. If there are no answer sets, answer 'Definitely no.'

*Gloss:* true if it holds in *some* valid scenario.

### skeptical / cautious → B on the example
> Use STABLE-MODEL (ANSWER-SET) semantics with SKEPTICAL (CAUTIOUS) reasoning. Consider all answer sets… Answer 'Definitely yes' only if the statement holds in EVERY answer set; 'Definitely no' if there is at least one where it does not hold. If there are no answer sets, it vacuously holds in every set; answer 'Definitely yes.'

*Gloss:* true only if it holds in *every* valid scenario (and vacuously true when there are none).

**Design point (agreed with Agnieszka):** all four are now matched in level of detail, and phrased to test *following the specified semantics*, not prior familiarity — WFS is the hardest to write at parity without leaking the answer.

---

## 4. Small-sample smoke test of the revised prompts (fresh today)

45-prompt headline set, T=0, per condition (correct / 9):

| model | overall | closed-world | credulous | skeptical | WFS |
|---|---|---|---|---|---|
| gpt-4o-mini | 19/36 (53%) | 6/9 | 3/9 | 3/9 | 7/9 |
| Qwen2.5-coder 32B | 18/36 (50%) | 3/9 | 3/9 | 3/9 | 9/9 |

- The prompts **work end-to-end** (models parse and follow them; ~2× longer, no trouble).
- Overall accuracy comparable to the earlier prompts; qualitative pattern holds: **credulous/skeptical hardest, WFS/closed-world easier**.
- *Caveat:* tiny single run — a smoke test, not a measurement. The production sample fixes this.

---

## 5. Headline findings (from the full PoC)

- **Frontier follows the rulebook; weak models lock into one answer.** On well-founded (gold = *undefined*): Claude Opus 12/12, GPT-5 11/12, down to Llama3 6/12 (= the trivial "always-C" baseline).
- **Difficulty is the *semantics × cycle type*, not size.** Depth and width are statistically flat to range 32 (bootstrap CI on the difference includes 0); the divergence bin dominates ~20–80×. (This survived reverting width to shared-subgoals-only.)
- **Default-reversion (the proposal's key metric):** frontier reverts far less (GPT-4.1 ~21%) than open models (Llama3 ~59%).
- **Mitigations that work:** translate-then-solve (model translates, our solver applies the semantics) → ~100% for strong translators; one few-shot example lifts weak models double digits; solver-certified LoRA fine-tune 41% → 91% (in-distribution). Cross-verbalization SFT transfers to a held-out *narrative* surface but not to an *abstract* one (honest holdout).

---

## 6. Decided vs open

**Locked:** four divergence bins; solver-certified gold under all four rulebooks; plain width + separate cycle length; English/Chinese cross-lingual axis; token logging; clustered CIs.

**Open (waiting on the UK side):**
- Final sign-off on the four prompts (Agnieszka + Kostas) — smoke test looks good.
- Then the **production run**: fixed depth/width, one verbalization, **30 instances per cell**, clustered CIs; the depth×width grid with local models (already stable); other experiments at the same fixed size.

Everything up to the production run is finished and pushed.
