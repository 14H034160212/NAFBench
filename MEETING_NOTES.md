# NAF-Bench — meeting notes & next steps (2026-07-08)

The discussion circled three things: (1) **framing** — what the benchmark is and how narrative vs. formal the language should be; (2) **motivation** — why an *artificial* language is defensible and how to ground it in real domains; (3) **next experiments** — launch the large-scale run, and add a rule-**reordering** axis. Your steer: **start the large-scale run, add reordering, and strengthen the motivation.**

---

## A. Framing — what the benchmark actually is

- We test whether an LLM will **follow a *specified* negation semantics**, not whether it can *detect / understand* negation in a sentence (that's the existing negation-NLP line — see §D). The program is fixed; the model is told which rulebook to apply; we measure adherence.
- **Underlying structure = a normal logic program** (ASP-style, negation allowed inside loops). The *same* program is rendered for all four semantics; gold comes from solvers (clingo / WFS fixpoint / Prolog). This mirrors how ProofWriter-style benchmarks generate facts+rules — worth **double-checking our program structure** matches that convention.
- The language is **controlled / "semi-FOL"** — a structured subset of English: facts, rules with `if` / `iff` (if-and-only-if), conjunction, disjunction. Open question: **how narrative vs. how FOL-like** should it be? (Options floated: logical English / controlled natural language; "node1/node2" reading as variables.)
- **Scope of this paper:** *no double negation*; the negation form is the cycle `a :- not b. b :- not a.` (two "sides"). Note for later: negation in the head, richer connectives = out of scope here.

---

## B. Motivation — needs strengthening (priority)

**The pull:** which negation semantics you apply genuinely changes the answer in **rule-based real domains** — law, regulation, medical reasoning, welfare/benefits, fault diagnosis. Skeptical vs. credulous vs. well-founded is the difference between "provably guilty in every scenario" vs. "guilty in some scenario" vs. "the regulation leaves it undefined."

**Motivating examples raised (all are our cycle gadget in disguise):**
- **Fault diagnosis** — `sensor_fault :- not actuator_fault.` `actuator_fault :- not sensor_fault.`
- **Legal / guilt** — `account_a :- not account_b.` `account_b :- not account_a.` `guilty :- account_a.`
- **Welfare / benefits** — `housing_support :- not income_support.` `income_support :- not housing_support.` `payment :- housing_support.` `payment :- income_support.` (this is exactly our `even_both_sided` bin — payment reachable from either side.)

**The tension to address head-on:** our instances are *artificial / synthetic*. Why is that a feature?
- controls confounds (isolates the negation-semantics variable), and
- **prevents data-leakage / contamination** — a model can't have memorized the answer.
- Real regulatory/legal text is *ecologically valid* but confounded and leak-prone → **future work / journal extension** (apply the prompts to real regulatory text as a teaser).

**Action:** write one well-motivated running example (welfare or legal), state the "artificial-but-motivated + real-data-is-future-work" argument explicitly, and cite a real rule-based domain.

---

## C. Next experiments

### C1. Large-scale / production run — *start it* (priority)
- Fixed depth/width, one verbalization, **30 instances per cell**, all models, clustered CIs.
- depth×width grid with local models (already confirmed stable under plain width).
- **Gate:** Agnieszka's final sign-off on the four prompts. Smoke test is done and clean; I sent the results and asked her to confirm. Script is ready to launch the moment she says the wording is final.

### C2. Rule **reordering** axis — *add it* (priority)
- **Claim to test:** rule order does **not** change the semantics (gold is invariant), but it may change (a) LLM accuracy and (b) solver hardness. A benchmark should show the model is order-robust — or quantify that it isn't.
- **Design:** for each instance, emit K random permutations of the rule order (and/or a few canonical orders: as-written / reversed / cycle-last); score accuracy variance across permutations per model; log solver hardness (Prolog inferences, clingo conflicts) per order. Report as a robustness axis alongside verbalization.
- Small, self-contained; I can implement a `--reorder` knob in the verbalizer + a `make_reorder.py` set and run it locally first (cheap).

### C3. Other ideas (park for later)
- **Improvement arm:** fine-tuning and **auto-formalization**; use the benchmark to evaluate whether fine-tuning *helps formalization* (we already have SFT + translate-then-solve; auto-formalization is the natural extension).
- **Failure diagnosis**, connections to **argumentation** and **abductive reasoning**.

---

## D. Related work / references (identified)

| ref | what it is | how we differ |
|---|---|---|
| **xNot360** — Nguyen, Goebel, Toni, **Stathis**, Satoh, 2023 (arXiv:2306.16638) | GPTs at **detecting** negation in sentences (Kostas's own prior work) | we test *applying a specified negation semantics*, not detection |
| **Thunder-NUBench** — So et al., EACL 2026 Findings (2026.findings-eacl.250) | benchmark for LLM **sentence-level negation understanding** (vs. contradiction/paraphrase) | sentence-level understanding vs. our rule-level *semantics-following* |
| **ASPBench** — Ren et al. (arXiv:2507.19749) | LLMs on ASP tasks (entailment/verify/**compute** answer sets) | they measure ASP task-solving; we hold the program fixed and test following a *chosen* semantics |
| Argument & Computation (10.3233/AAC-190477) | argumentation semantics *(to confirm exact title)* | link to argumentation framing |
| AIJ 1994, S0004-3702(94)00041-X | foundational logic-program semantics *(to confirm)* | our solver-certification basis |
| (already cited) ZebraLogic; Illusion of Thinking | size-driven reasoning collapse | ours is *semantics*-driven |

**One-line positioning:** existing negation-NLP benchmarks test **detecting/understanding** negation in sentences; NAF-Bench tests whether a model will **apply a specified formal negation semantics** over structured rules, with every answer solver-certified.

---

## E. Open questions to close

- How **narrative vs. FOL-like** should the language be? (controlled NL / logical English — pick a point on the spectrum and justify it.)
- **Double-check the program structure** vs. ProofWriter-style generation (facts/rules; any negation-in-head cases?).
- Clarify "wall of contradiction" and scope of the "full revision."

---

## Immediate action items

1. **Reordering experiment** — implement `--reorder` + `make_reorder.py`, run locally, report order-robustness. *(I can start now.)*
2. **Motivation section** — draft the "artificial-but-motivated + real-data-as-future-work" argument with a welfare/legal running example; add to README/paper. *(I can start now.)*
3. **Related work** — add xNot360 + Thunder-NUBench, with the detect/understand-vs-follow-semantics distinction. *(I can start now.)*
4. **Production run** — launch once Agnieszka confirms the prompts are final. *(Script ready; gated on her.)*
