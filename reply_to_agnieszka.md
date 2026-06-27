Subject: Re: NAF-Bench — parametrization (implemented + validated)

Hi Agnieszka,

Thank you — this is exactly the structure the benchmark needed, and I've gone
ahead and implemented all of it. The code is on GitHub and I've added
**CaptainPirx** and **kostas-stathis** as collaborators:

  https://github.com/14H034160212/NAFBench

A short summary of what's now in place, all certified by the solvers.

**1. Four label dimensions.** The certifier (`nafbench/solvers.py::certify_full`)
now reports the four you specified, with your zero-model conventions:

  - SLDNF:           {T, F, loop}
  - WFS:             {T, F, u}
  - Stable, credulous:  {T, F}   — `any([]) = F`  (no stable model ⇒ F)
  - Stable, skeptical:  {T, F}   — `all([]) = T`  (no stable model ⇒ T, vacuous)

These fall out of Python's `any`/`all` on the empty model set, so the vacuous
cases are handled correctly without special-casing.

**2. The four divergence bins reproduce your predicted signatures exactly.**
`validate_v2.py` builds every bin at several depths/widths and checks the
certified four-tuple `(cred, skept, WFS, SLDNF)`; all pass:

  | bin                              | (cred, skept, WFS, SLDNF) | distinct |
  |----------------------------------|---------------------------|----------|
  | control                          | (T, T, T, T)              | 1        |
  | even-cycle, one-sided (q:-x)     | (T, F, u, loop)           | 4        |
  | odd-cycle (no stable model)      | (F, T, u, loop)           | 4        |
  | even-cycle, both-sided (q:-x;q:-y)| (T, T, u, loop)          | 3        |

One small adjustment worth flagging: in your message the "odd-cycle" snippet was
written as `x :- not y. y :- not x.`, which is actually a length-2 (even) cycle —
the (F, T(vacuous), u, loop) signature needs a genuinely *odd* cycle so that no
stable model exists, so I implemented the odd bin with an odd-length cycle
(default length 3). `cycle_len` is a parameter, fixed per bin for now exactly as
you suggested (even bins = 2, odd = 3), and trivial to sweep later.

**3. Depth × width generator.** `G(depth, width, divergence_bin)` is implemented
in `nafbench/instances.py`. Width uses your shared-subgoal gadget
(`a :- h1..hk`, `b :- h1..hk`, the `h_i` grounded in independent facts), so the
reasoner must hold `k` atoms simultaneously. The depth chain and the width block
are both certified *true*, which means they scale the instance **without**
changing the divergence signature — I verified this on an 80-instance grid
(`data/nafbench_v2.jsonl`: 20 control / 40 all-four-differ / 20 three-differ).
This gives us clean, orthogonal knobs.

**4. Per-instance solver hardness.** Each instance now records **Prolog
inferences** (`statistics/2`) and **clingo conflicts/choices** as a measure of
how hard the instance actually is for the solver. Inferences already scale with
both knobs (control bin: width 0→16 ⇒ 7→73 inferences; depth 0→16 ⇒ 7→23). Plot:
`data/v2_hardness.png`.

I fully agree with your hypothesis that **width may be the stronger moderator**:
a linear chain is "apply k rules in sequence", whereas width forces simultaneous
tracking, which is where I'd expect models to drop back to their default
semantics. The natural next experiment is to regress model default-reversion on
`(depth, width, divergence_bin)` and on the solver-hardness metrics — with width
and depth as separate predictors so we can test exactly that.

For context on whether the phenomenon is even there to study: in the v1 runs the
divergence cases are already hard for current models. On a held-out
well-founded set, per-item correctness across nine models (Claude / OpenAI incl.
GPT-5 / open-source) is in `data/model_heatmap.png`; the conjunction-cycle item
fools 7 of 9, including GPT-5, which revert to classical "A∧B is impossible →
false" instead of `undefined ∧ undefined`. Solver-certified LoRA SFT then lifts
small open models substantially (e.g. 41%→89%). So the signal is real, and the
v2 grid is what we need to map *where* it breaks.

A few questions to align before I run the LLM evaluation on the v2 grid:

  1. Ranges — what depth/width grid would you like for the first run (I'm
     thinking depth ∈ {0,2,4,8,16}, width ∈ {0,2,4,8,16}), and a cycle-length
     sweep (3,4,5,…) or fixed for now?
  2. Prompt conditions — we now have up to five "specified semantics" to test
     the model against (credulous, skeptical, WFS, SLDNF/closed-world, plus a
     no-instruction default). Do you want all five, or a core subset?
  3. Verbalization — credulous vs skeptical are subtle to phrase in natural
     language ("could hold in some consistent scenario" vs "must hold in every
     consistent scenario"). Happy to draft both and have you sanity-check the
     wording.

Thanks again — this sharpened the design a lot. Everything above is reproducible
from the repo (`python validate_v2.py`, `python build_v2.py`).

Best,
Qiming
