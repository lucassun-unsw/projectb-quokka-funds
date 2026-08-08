# Prompt log — Phase 7 (the app) and Phase 8 (the verification sweep)

## What I wanted
Finish the build: the Station 4 Streamlit app implementing the brief's investor
journey against the precomputed `results/`, then the Phase 8 sweep my plan
committed to before any report prose — the phase Part A skipped having
explicitly and paid for in late report-writing fixes.

## Prompt(s)
- "check through all the figures that some of the axis are collapes, make sure
  all the figures are good to use. also, do a full check, like if the OUTLINE
  is fully satisfy to the project brief? if the coding of Phase 2-6 is fully
  satisfy to the OUTLINE and the project brief? check everything"
- "so like the OUTLINE is fully satisfy to the project brief and all the coding
  and result are good?" (I asked for a straight answer on where things stand)
- "do phase 7" / "do phase 8"

## What the assistant produced
- The five-tab app (compare with a cost slider driving the precomputed net
  columns; fact sheet with the co-crash panel; allocation blend; sentiment
  analytics; about/data with a graceful fallback if the data host is down),
  tested two ways: a headless server smoke test and full-script execution via
  `streamlit.testing.v1.AppTest` (0 exceptions, including after switching the
  fact sheet to a Crypto-Only fund).
- The full audit and then the seven-item Phase 8 sweep, including the
  isolation re-test: the folder copied to a location with no `projectA`
  anywhere, scanned for cross-folder references, and run cold — all 14 output
  CSVs bit-identical to the project run.

## What was wrong or risky
- **The audit I asked for found four defects none of the automated checks had
  caught.** Two were only visible by literally opening the PNGs (a truncated
  co-crash subtitle; a stacked-weights figure whose repeated colours made the
  legend ambiguous — GILD, MMM and "other" were all the same maroon). Two came
  from reading the brief and the plan against the file inventory: the fund
  names in every CSV used method slugs (`Combined max_sharpe`) where the
  plan's locked convention is display names (`Combined Max-Sharpe`) that the
  fact sheets and app key off; and the fact-sheet "current holdings" bullet
  had no artifact at all. All four fixed and re-verified; the ledger numbers
  were unchanged by the renaming, as they should be.
- **A figure title was drafted before its claim was checked.** The
  cost-sensitivity title asserted the Sharpe podium "never reorders" across
  the cost grid — written into the code before the numbers had been read. I
  had it verified against the table before the figure was rendered, and the
  claim held (Risk Parity > Min-CVaR > Min-Variance > Max-Sharpe at every
  level, with Min-Variance and Max-Sharpe converging to 0.427 vs 0.424 at
  50 bps) — but the pattern is title-first, evidence-second, and it only
  worked out because the check happened. Recording the near-miss.
- **The hand-in checker flagged the app for "referencing nltk" — a false
  positive worth understanding.** `check_handin.py` greps the app file for the
  literal string; the app never imports the library, but its own docstring
  *saying so* ("never imports nltk") tripped the check. Reworded the prose.
  Same checker behaviour that forced the scoring cache out of the project in
  prompt_log_06 — it scans text and filesystems, not imports and git.
- **The Phase 8 sweep caught a wrong-object quote staged for the report.** My
  notes for the report cited the sentiment event-validation percentiles from
  the *post-lexicon-extension* index (OXY 0.055) where the saved CSV the
  report will cite holds the *base-index* values (0.074, with BCH 0.183 and
  the COVID week 0.235). Two numbers describing different objects — exactly
  the figure-vs-table mismatch class from Part A, caught this time before a
  word of prose existed. Fixed: base values with the Section 3 material, the
  0.074→0.055 sharpening moved to the lexicon discussion where it belongs.
- **One honest caveat on the isolation test**: the cold run reused the
  deterministic scoring cache in `~/.cache/` (outside any project folder, so
  the independence claim is fully verified), meaning the scoring loop itself
  did not re-execute cold. It ran fresh earlier the same day and VADER is
  deterministic, so a clean machine regenerates identical scores — slowly.
  Stated in the plan rather than glossed.

## What I changed and why
- App hygiene rules are enforced by construction and now also by wording: the
  deployed app reads only `results/` plus the hosted prices, does display
  arithmetic only (cumprod, running max, weighted sums — the allocation
  blend's crash-day mean is exact because a mean is linear in weights), and
  the recommendation is a highlighted default with the Sharpe-vs-crash-day
  trade-off stated, not a restriction.
- The sweep recomputed every fund's metrics independently from
  `fund_returns.csv` and matched `performance_metrics.csv` to 6.3e-15, and
  matched `current_holdings.csv` to the final weights row exactly — the
  single-object wiring rule is now a measured property, not a design
  intention.
- Every named ticker, sector, and quoted headline in my report notes was
  checked against the data (including recomputing OXY's −52.0% on 2020-03-09
  from prices); 40+ numbers staged for quoting were checked against their
  literal CSV values. One error found (above); the rest held.

## Verification I did myself
- Read all nine figures as images, twice where they changed — the only method
  that caught the axis and palette defects.
- Asked for the honest gap list rather than accepting "all good": the straight
  answer was that built ≠ submitted — the report prose, the deployment, and
  (at that point) the isolation re-test were still open, and the isolation
  test was then run rather than assumed.

## Still open
- Phase 9: the report itself (`report.docx` does not exist yet) — my words.
- Phase 10: deploy from a public repo with my logins; delete the private
  planning files per their own headers; clear `__pycache__`; zip.
- Verify the four convention citations (RiskMetrics, Basel FRTB, UCITS,
  Ledoit–Wolf) before citing; reconcile `CLAUDE.md` rule 7 (old cache note).
