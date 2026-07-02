# NAF-Bench — progress (1 page)

## The question
Give an LLM some rules **and tell it which "rulebook for *not*" to use**.
Does it obey the rulebook — or fall back to its own default?

## One example (same rules → 3 different correct answers)
> Alice attends **iff** Bob does not. Bob attends **iff** Alice does not.
> The meeting is held if either attends. **Is the meeting held?**

| rulebook (semantics) | answer |
|---|---|
| **credulous** (holds in *some* consistent scenario) | **Yes** |
| **skeptical** (holds in *every* scenario) | **No** |
| **well-founded** (is it grounded, or circular?) | **Cannot determine** |

Every answer is machine-checked by real solvers (clingo / well-founded / Prolog).
*(Labels: **brave = credulous** (∃ answer set) · **cautious = skeptical** (∀ answer
sets) — these two are clingo's two modes; well-founded & closed-world are separate
engines. No-stable-model case: skeptical = yes (vacuous), credulous = no.)*

## Data recipe (auto-generated, 100% solver-certified)
1. **Generator** `G(depth, width, cycle-type)` builds a tiny logic program.
2. **Solvers** compute the gold answer under each rulebook (4 labels: credulous /
   skeptical / well-founded / closed-world).
3. **Templated verbalization** → natural-language prompt (4 domains, EN + 中文).
4. **Knobs:** depth · effective-width (cycle counted in) · #cycles
   (independent / coupled) · cycle length. Each record saves the program + #models.

## Headline results  (95% CI clustered by program, 3 sampling runs)
- **Strong models obey; weak models lock into one answer.**
  GPT-4.1 / GPT-5 ≈ 100% on credulous/skeptical/WFS; Llama3 far lower.
- **Hard even for the best:** closed-world / non-termination is the worst condition.
- **Default-reversion** (proposal's key metric): when told a rulebook that clashes
  with its default, GPT-4.1 reverts **21%**, Llama3 **59%** (frontier reverts less).
- **What drives difficulty = the *cycle type*, not size.** depth vs width is **not
  significant** (bootstrap CI includes 0); the divergence bin dominates ~10–20×.
  Padding proves **length is inert, structure isn't**.
- **Fixes that work:** translate-then-solve → ~100%; **one few-shot example lifts
  weak models double-digits**; solver-certified LoRA fine-tune **41%→91%** (in-dist).

## Done since the meeting
- ✅ **Independent audit** (Fable): fixed a conj "only if"→"if" prompt bug + a
  Prolog loop-detection race; **regenerated all data (gold unchanged), re-ran all
  models, retrained all adapters**; CIs now clustered by program.
- ✅ **Generalization / transfer (honest holdout):** frontier verbalization-robust;
  multi-verbalization LoRA transfers to a held-out *narrative* surface (beats base
  & single-framing) but **collapses on a held-out *abstract* framing** — the
  earlier "transfer solved" reading was an artifact of the test framing being in
  training.
- ✅ Adopted your **symmetric credulous/skeptical** prompt wording.
- ✅ **Tokens *used*** now logged (not just the answer); labels clarified
  (brave=credulous, cautious=skeptical); related work positioned vs ZebraLogic /
  Illusion of Thinking (size-driven) — ours is semantics-driven.

## Open
- Broaden training framings to span the representational range (narrative **and**
  abstract), not just more narrative themes.
- Final wording sign-off + scale of the production run.
