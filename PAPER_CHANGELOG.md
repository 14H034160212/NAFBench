# Paper revision log

The submission source (`negbench_paper/*.tex`) is gitignored for anonymity, so
this file is the tracked record of paper-side revisions. Data/scripts backing each
change are committed under `data/` and the repo root.

## 2026-07-23 — trace analysis + collaborator review round

**Reasoning-trace analysis (Agnieszka / Opus-4.8 audit).**
- §12 parser artifact fixed: re-parsed llama3 production answers with the fixed
  `ANSWER_RE`; 5 items change (3 spuriously-correct → wrong), llama3 strict 47→46%.
  Table 1 (skept 67→64, rev 69→68), Table 2 (odd 37→36, even-2 51→50) updated.
- DeepSeek reasoning-vs-answer gap reported, not re-scored (80% of WFS-undefined
  traces reach "undefined", only 26% render "C"); added as an E5 caveat.
- New `Supplement2027.tex`: strategy table, "instruction can hurt" table
  (o4-mini none-vs-WFS 97→70 / 0→73 / 40→100), per-model synthesis, DeepSeek gap,
  parsing notes, both mitigation prompts verbatim, case studies.

**≥30-sample mitigations (44 diverse WFS programs; replaces the 12-item probe).**
- Table 7 (T2S): direct vs +solver, 59/95, 49/74, 62/89 (parsed %).
- Mitigation 3 (verify): every open model improves (59→82, 62→69, 49→62).
- Harnesses: `make_wfs_big_verify.py`, `translate_solve_set.py`,
  `run_wfs_big_all.sh`; answers in `data/{wfs_big,wfs_big_verify,t2s_big}_answers`.

**Presentation / consistency.**
- All tables report % with denominators stated; per-bin (30 programs × 4 semantics)
  and per-cell counts added. Silver Blaze epigraph added. Body = 7 full pages,
  references on 8–9.

**Collaborator results-section questions (resolved).**
- SFT transfer numbers (40/44=91% narrative, 28/44=64% abstract) documented in a
  supplement table; the earlier "+22 points" corrected to +22 *items*
  (18/44→40/44). Table 8 reconciled to the current eval: gemma 41/91,
  qwen2.5-7b 59/93/93 (+SFT = mean of 3 seeds; DPO neutral).
- E3 clarified: the OLS is fit over the 360-prompt all-bin set
  (4 bins × depths {2,8,16} × widths {0,4,8}); Table 3 is the even-one-sided
  size-marginal view.
- Added missing citation `kirichenko2025` (AbstentionBench) to `references.bib`
  (metadata pending collaborator confirmation); fixed a cross-document `\ref` in
  the supplement.
