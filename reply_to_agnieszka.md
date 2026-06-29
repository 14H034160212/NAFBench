Subject: Re: NAF-Bench — multiple cycles added + dataset upgrades + results

Hi Agnieszka,

Both of your suggestions are implemented and run. Code/data on GitHub:
https://github.com/14H034160212/NAFBench

Multiple cycles (extended cycle parametrization).
I added both structures exactly as you wrote them and swept the number of cycles:
  - independent: n separate even 2-cycles, q :- x1 ; q :- y1 ; ...
  - interdependent: coupled chain x:-not y / y:-not x,not z / z:-not w / w:-not z
    / q:-x, generalized to n coupled cycles.
All certify to (credulous T, skeptical F, WFS u, SLDNF loop) — so cred/skept/WFS
gold = A/B/C — and the new knob is the number of cycles (= number of stable
models): independent gives 2/4/8/16 models for n=1..4, interdependent 2/3/4/5.

Results (over cred/skept/WFS):
  - Frontier is immune: GPT-4.1 and GPT-5 are 100% across all cycle counts and
    both structures.
  - Weak models drop once there's more than one cycle, and coupling matters more
    than count: e.g. GPT-4o-mini is 100% on independent at every n, but
    100/33/67/33% on interdependent (n=1..4); Llama/Qwen sit ~67% on independent
    for n>=2. So, as you anticipated, multiple cycles is a real knob that mainly
    bites the less-capable models, with interdependent harder than independent.

Dataset upgrades (both done).
  - Each instance record now stores n_stable_models (from clingo) and the full
    underlying logic program (prog.pretty()), so you can double-check the
    certified labels directly. I also added a transparent rule-by-rule
    verbalizer ("Proposition X is true if proposition Y is not true.") for the
    multi-cycle structures, which is easy to read against the program.

I agree on not pushing depth/width past 32 for the frontier — in the extended run
the curves were flat to 32 and the divergence bin kept dominating, so chasing
orders-of-magnitude size isn't worth it. The productive axes look like: the
divergence type (incl. now multi-cycle / coupling) and the default-reversion
behaviour. On that: the proposal's signature metric is now computed — when the
specified semantics conflicts with a model's no-instruction default, reversion
rate is 50% (Llama), ~32% (GPT-4o-mini / Qwen / GPT-4.1); every model's default
is credulous/classical, so reverting = failing to take the cautious WFS/closed-
world view. And a single few-shot exemplar is a strong fix for capable-enough
models (GPT-4o-mini 33%->89%, Qwen 22%->67%).

Happy to send the credulous/skeptical instruction wording for your review next.

Best,
Qiming
