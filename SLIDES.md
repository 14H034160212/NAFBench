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

## Data recipe (auto-generated, 100% solver-certified)
1. **Generator** `G(depth, width, cycle-type)` builds a tiny logic program.
2. **Solvers** compute the gold answer under each rulebook (4 labels: credulous /
   skeptical / well-founded / closed-world).
3. **Templated verbalization** → natural-language prompt (4 domains, EN + 中文).
4. **Knobs:** depth · effective-width (cycle counted in) · #cycles
   (independent / coupled) · cycle length. Each record saves the program + #models.

## Headline results  (95% CI, 3 sampling runs)
- **Strong models obey; weak models lock into one answer.**
  GPT-4.1 / GPT-5 ≈ 100% on credulous/skeptical/WFS; Llama3 almost always says "yes".
- **Hard even for the best:** closed-world / non-termination → GPT-4.1 only **30%**.
- **Default-reversion** (proposal's key metric): when told a rulebook that clashes
  with its default, GPT-4.1 reverts **18%**, Llama3 **68%** (CIs don't overlap).
- **What drives difficulty = the *cycle type*, not size.** depth/width barely
  matter (flat to 32); padding proves **length is inert, structure isn't**.
- **Fixes that work:** translate-then-solve → ~100%; **one few-shot example
  33%→89%**; solver-certified LoRA fine-tune **41%→89%**.

## Next (from today's meeting)
- **Generalization test set:** different verbalization for train vs test (avoid
  memorization; check the failure transfers across phrasings).
- Save **tokens *used*** (model output), not just the answer.
- Clarify credulous / skeptical / brave-cautious labels; note **which differs
  from clingo's default (brave/cautious stable-model reasoning)**.
- Related work to position against: arXiv 2502.01100, 2506.06941.
