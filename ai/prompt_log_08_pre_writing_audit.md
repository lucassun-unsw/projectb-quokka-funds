# Prompt log — Phase 8b, the pre-writing audit

## What I wanted
One last full check of Part B before I start writing `report.docx`. Not "does it
run" — Phase 8 already established that — but "is every number I am about to
quote actually true, and does it come from a file I can point a marker at."

## Prompt(s)
- "do a full check through for project B, like everything make sure are all good
  before I start to write the report"
- "fix all of them, and re-run to save the RP-vs-CVaR bootstrap, no need to
  concern about page limit and also do 7 like help me to verify or just delete it
  since like it is not neccesary"
- "why to 263? if we discuss that we use 256?" (I did not accept the changed
  number until it was justified)

## What the assistant produced
- A re-verification of ~45 claim-ledger numbers against the saved CSVs, an
  independent recomputation of the whole co-crash result from raw data plus
  `fund_returns.csv`, visual checks of four figures, and the tests / hand-in
  checker / `AppTest` run.
- Then the fixes: a static-covariance option in `oos_backtest`, two extra
  bootstrap pairings, three new tables, four new columns, a retitled figure, a
  rewritten `CLAUDE.md` rule 9, and the corrected numbers in `OUTLINE.md`.

## What was wrong or risky
- **The centrepiece number of Section 4 was not in any file.** My plan said a
  Sharpe-shopper picking Risk Parity loses ~1pp per crash day "CI [+0.73, +1.16]",
  but `co_crash_bootstrap.csv` only ever contained comparisons against
  Min-Variance. Recomputing it showed the interval belonged to the Risk Parity
  **vs Min-CVaR** pairing — the one my recommendation actually needs, since the
  recommended fund is Min-CVaR — and that the quoted lower bound was wrong too
  (0.71, not 0.73). I would have written a confident CI into the argument that
  carries the 30% band, from a number nothing could reproduce.
- **The assistant's own audit finding was itself a wrong-object error — the same
  class of mistake it was reporting.** It flagged "1,106 headlines" as a
  transcription slip because `lexicon_before_after.csv` says 1,097, and told me
  to change it. Re-running the pipeline showed both numbers are real and
  different: 1,106 headlines *contain* an installed term, 1,097 of them actually
  *changed score*, and the 9-headline gap is genuine. The audit was right that
  something was wrong (a containment count sitting in a sentence that cited a
  file holding a change count) and wrong about what. Running the code settled it;
  reasoning about it did not. This is the third wrong-object catch in this
  project, after the event percentiles and the two 252s.
- **A figure title asserted something the figure below it contradicted.**
  `fusion_before_after.png` was titled "free lunch gross - and no lunch net",
  but the gross Sharpe delta is *negative* for Min-Variance (−0.0107) and that is
  the largest of the four bars in its own right panel. My own locked verdict says
  "negligible gross". Exactly the title-first pattern I recorded as a near-miss
  in prompt_log_07 — that one happened to check out, this one did not.
- **`CLAUDE.md` rule 9 still said "zero transaction costs"** long after I built
  the turnover/cost model that is one of my innovation strands. My own file says
  `OUTLINE.md` wins on drift and to flag it; nothing flagged it for eight phases.
  It is also a graded artifact — a marker reading my instruction file would have
  seen it contradict my Section 4.
- **Numbers that lived only in a session transcript.** The EWMA-vs-alternatives
  evidence for Section 1, the method-separation numbers, and the lexicon's
  index-level impact were all quoted from exploratory runs recorded in
  prompt_log_04 and prompt_log_06, not from `results/` — against my own rule that
  every percentage in prose must be a literal value in a saved CSV. Four of them
  changed once they were reproduced under the final locked parameters: static
  volatility 12.78→12.79%, EWMA/static turnover 256/29→263/30%, the closest
  method pair 0.066–0.107→0.076–0.150, and "48 solves"→520.

## What I changed and why
- I did not take 263% on the assistant's word. I asked why it differed from the
  256% we had been discussing, and the answer that convinced me was not the
  re-run — it was that `performance_metrics.csv` has held
  `turnover_ann = 2.625142` for Combined Min-Variance all along, identical to the
  parameter study's EWMA row to 0.00e+00. The EWMA fund in my headline
  performance table *is* the 263% fund, so quoting 256% in Section 6 would have
  contradicted my own Section 2 table. The old number came from a run that
  predates the locked parameters and only ever survived as a ratio ("~9×") in the
  log; 8.8× is consistent with it.
- Made the two bootstrap pairings I actually argue from into saved rows rather
  than a remembered result. `co_crash_bootstrap.csv` now has 10 rows and the
  Section 4 claim is **Risk Parity −0.94pp, CI [−1.16, −0.71]** at q=10%.
- Put the transcript-only numbers into `results/`: `parameter_study.csv` (rival
  covariance estimates with by-year splits), `method_separation.csv`,
  `lexicon_event_validation.csv`, plus `index_corr_with_base` and the
  growth-of-$1 columns. Where I could not reproduce a number — the pre-filter
  range and the two-step worked example — I did not quietly keep it; both are now
  flagged as prompt-log diagnostics in my report plan (`OUTLINE.md`),
  to cite as such or drop.
- Kept both lexicon counts under their own names in the CSV
  (`n_headlines_containing_term` and `n_scores_changed`) instead of picking one,
  so the distinction cannot be lost again, and wrote the difference into the
  writing guide.
- **Dropped the four convention citations rather than verifying them.** They had
  been an open loose end since Phase 2. Nothing in my argument rests on a
  source's authority — only on numbers from my own data — so each is now stated
  as an unattributed convention justified by its evidence ("a 97.5% level leaves
  only 6.3 tail scenarios at T = 252"). Deleting an unverifiable citation is
  honest; keeping an unverified one is not.
- Rewrote `CLAUDE.md` rule 9 to describe the cost model that exists, including
  the rule that a net number is never quoted without its cost level.

## The second pass over the new code
I asked for the changes to be reviewed again rather than trusting that a passing
re-run meant they were sound, and that pass found one interpretation trap the
numbers alone would not have shown:
- **`method_separation.csv` saturates.** Three of the six method pairs in every
  family come out at *exactly* the family cap (0.100, or 0.250 for crypto),
  because whenever one method pins an asset at the cap and the other holds none
  of it the maximum difference simply *is* the cap. Reported as-is, "max|Δw| =
  0.100" reads like a measured distance when it actually means "the metric hit
  its ceiling". The table now carries `family_cap` and `at_family_cap` so the
  artifact says this itself, and the guide tells me to quote the closest
  *unsaturated* pair (0.078 / 0.076 / 0.150) — the conservative number, and the
  one that actually answers the stalled-optimiser question.
- Also confirmed by construction rather than assumption: `sample_covariance`
  matches `np.cov(bias=True)` to 1.3e-15 and equals `ewma_covariance` at a huge
  span to 3e-08, so the static benchmark really is "EWMA with the decay switched
  off" and the comparison isolates the weighting rather than an estimator
  convention; the default optimiser path is bit-identical to the explicit EWMA
  path (0.00e+00); and the whole-word matcher does *not* match "downgraded" on
  "downgrade", which is the inflection gap the lexicon strand is about.
- I also noted the parameter study speaks for the three covariance-based methods
  and not for Min-CVaR, which never forms a covariance. That limit is now stated
  in the writing guide instead of being left for a marker to notice.

## The full re-verification afterwards (Phase 8c)
Having changed code, I did not assume the earlier verification still held. I had
everything re-checked from scratch — 94 assertions across the foundation, the
backtest frame, the claim ledger, co-crash, sentiment, fusion, lexicon, the app
rules and the brief's required exhibits. Two things came out of it:
- **A no-look-ahead test appeared to FAIL, and the diagnosis mattered more than
  the fix.** Scrambling the future moved pre-cut min-variance weights by 1.8e-04
  instead of zero. It is not look-ahead: the window handed to the optimiser was
  provably bit-identical. The scramble had been written with a pandas `.loc`
  assignment, which changes the frame's memory layout, which changes the BLAS
  reduction order inside the covariance, which perturbs it by ~1e-18 — and
  min-variance here is flat enough (condition number ~1.3e3) to turn that into
  1.8e-04 of weight while the portfolio variance moves 2.4e-07 relative. With the
  layout held fixed, all four methods return **exactly 0.00e+00**. I kept the
  finding rather than just fixing the test: it is a real numerical-robustness
  point, it is a second argument for shrinkage next to the condition-number
  result, and it is now a permanent test.
- **The retracted-claim note in my writing guide justified itself incorrectly.**
  It said both claims were "disproved by the bootstrap". That is true of the
  second one (the gap straddles zero) but false of the first: the bootstrap is
  *invalid* on a minimum, so the worst-day claim was never tested at all. Worse,
  min-CVaR beats min-variance on the worst-day point estimate in **6 of 6**
  family × threshold combinations — the claim looks true, which is exactly why it
  is dangerous. Had I written "the bootstrap disproved it", I would have misstated
  my own method in a way a marker recomputing the panel could catch. Rewritten to
  give each retraction its own, correct reason.

## Verification I did myself
- Required the wholesale re-run rather than patched outputs, then a diff against
  a pre-run backup: `fund_returns.csv`, `fund_weights.csv`,
  `sector_sentiment_index.csv` and `performance_metrics.csv` came back
  **bit-identical**, which is the evidence that the additions were additive and
  the determinism claim still holds.
- The co-crash result was recomputed independently — crash dates rebuilt from the
  raw panel, funds read from the saved CSV — and reproduced the saved bootstrap
  exactly, before any of it was changed.
- 19 assertions re-run against the regenerated CSVs after the edits, all passing,
  plus a grep for every superseded value across the docs (two stale copies of
  256%/29% were still hiding in the Section 6 recommendation and were fixed).
- Tests 2/2, `check_handin.py` 21/21 with only the expected `__pycache__` and
  `report.pdf` reminders, `AppTest` 0 exceptions, and the retitled figure re-read
  as an image.
- Re-checked the brief's required exhibits against the file inventory myself:
  all seven present, all four exact filenames present, and
  `performance_metrics.csv` carries annualised return, volatility, Sharpe and max
  drawdown.

## Still open
- Phase 9: the report itself — my words, from my report plan (`OUTLINE.md`).
- Phase 10: deploy from a public repo with my logins, paste the URL and repo link
  in, delete the private planning files, clear `__pycache__`, zip.
