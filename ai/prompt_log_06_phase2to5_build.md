# Prompt log — building Phases 2-5: portfolios, sentiment, fusion, lexicon

## What I wanted
Turn the fully-audited plan into code: `src/portfolios.py` (Phase 2),
`src/sentiment.py` (Phase 3), `src/fusion.py` (Phase 4), `src/lexicon.py`
(Phase 5) — with the claim ledger in `report/OUTLINE.md` acting as the
correctness oracle: any divergence from the recorded numbers is a bug in the
new code, not a new finding.

## Prompt(s)
- "do phase 2, 3"
- "help me to continue to finish Phase 3 and do a full check for phase 2 and 3"
- "do phase 4 and 5"
- "write the ai log then do phase 6"

## What the assistant produced
- The four modules, each parameter carrying its evidence in the docstring
  (why manual EWMA, why the family-specific cap, why the lag lives inside
  `fusion_signal`, why the bootstrap must not be used on minima).
- A 52-check verification run for Phases 2-3: all 12 funds reproduce every
  claim-ledger number exactly (Sharpes, vols, drawdowns, bootstrap CIs,
  growth of $1); the no-look-ahead scramble test passes at 0.00e+00 for all
  four optimisers; the fusion signal is lag-exact against a hand-built
  reconstruction; the sector index matches a hand-computed two-step mean AND
  differs from the rejected flat mean on a concentration day.
- Fusion k-grid and before/after across all four Combined funds, gross and
  net of costs; the lexicon AI-rater pipeline with a human-review CSV.

## What was wrong or risky
- **The previous session's "verified" cache-location decision failed the first
  time the cache actually existed.** The plan had locked project-root `cache/`
  after checking the `.gitignore` `!results/**` trap — but only the git side.
  `scripts/check_handin.py` scans the FILESYSTEM (`ROOT.rglob`) for any
  `.parquet`/`.csv` outside `results/` and `[FAIL]`ed the hand-in on the
  perfectly-gitignored cache. A "verified" claim had covered half the
  constraint set. Lesson recorded: verification that checks one enforcement
  mechanism does not transfer to the other; the artifact had to exist for the
  gap to show. Fix: cache moved outside the project entirely
  (`~/.cache/fins3645_z5594806_projectB/`), migrated without rescoring.
- **The plan's multi-word install step was built on the wrong package's
  internals.** The locked Phase 5 note carried week 8's SPECIAL_CASES/
  BOOSTER_DICT two-step install for multi-word phrases. Runtime inspection
  (`inspect.getmodule`) showed finvader vendors **nltk's** VADER class, not
  vaderSentiment's — nltk exposes no such module-level dicts. The install
  mechanism was revised to single-token lexicon updates; multi-word ideas
  became hyphenated tokens (matching hyphenated usage only, stated openly).
- **finvader's own convenience function is unusable at scale** — it re-loads
  both lexicons and constructs a fresh analyser on every call. Discovered by
  reading its source via `inspect` (not by benchmarking after the fact);
  `sentiment.build_finvader` replicates the package's exact both-lexicons
  recipe once (verified: 13,324 merged terms) behind an `lru_cache`.
- **An old plan note had the wrong neutral value.** The no-headline-day rule
  said neutral-fill at "0.5 / 50" — that is a 0-100 fear-greed convention;
  VADER compound is on [-1, +1] with neutral 0.0. Caught while writing
  `sentiment.py`; `NEUTRAL_SCORE = 0.0` with the discrepancy documented, and
  the OUTLINE row corrected.
- **My own test script produced the only red herring of the session** — a
  numpy broadcast error while verifying the fusion lag, caused by comparing a
  1005-row lagged frame against a 1006-row raw frame. The module was right;
  the check was sloppy. Worth recording so a future session doesn't mistake
  the pattern for a module bug.

## What I changed and why
- Everything parameter-shaped comes from the locked decisions; nothing was
  re-derived. Where the build contradicted the plan (cache location, install
  mechanism, neutral value), the OUTLINE was updated in the same session with
  the reason, per the "OUTLINE wins, flag drift" rule — and `CLAUDE.md` rule 7
  still describes the old cache plan, flagged for reconciliation.
- `check_cap_feasible` hard-errors on the exact 10-asset/10%-cap degeneracy
  the earlier verification sweep caught — the bug is now structurally
  unrepeatable, not just remembered.
- The transaction-cost grid went into `oos_backtest` from the first line, and
  the co-crash bootstrap into `portfolios.py` with its docstring stating the
  minima limitation — both were retrofit risks the plan explicitly named.
- The fusion result is recorded the honest way round: negligible gross
  (+0.005 Sharpe at best), zero-to-negative net of 20 bps on every fund, with
  the k-grid showing the conclusion is not sensitive to k. No post-hoc k
  tuning to manufacture a win.
- The lexicon pipeline installs nothing without my review: `extend_terms()`
  default mode requires `human_decision == "keep"`; the `ai_only` mode is
  labelled provisional in its output. The four deliberately-planted
  ambiguous/neutral candidates (margin, margins, short-squeeze, stress-test)
  were all caught by the SD/mean filters — a designed test of the filters,
  which passed.

## Verification I did myself
- The claim-ledger discipline worked as designed: nine Phase 2 metrics
  reproduced to 4 decimal places on first run, which is what "treat
  divergence as a bug" looks like when there is no divergence.
- The genuinely new (non-ledger) results were spot-checked by hand: the
  two-step Tech 2020-03-12 sector mean recomputed manually (+0.0627, vs the
  flat mean's +0.0881); three fixed false-neutral headlines read in full
  ("US Bancorp is Oversold" 0.00 → +0.25, etc.); event validation re-run
  after the extension (all three crash events still recognised, OXY
  percentile sharpened 0.074 → 0.055).
- Confirmed `results/` contains only the intended review CSV and
  `check_handin.py` passes (17 checks) after the build.

## Still open — resolved later the same session
- **Lexicon review: done.** I reviewed the AI-rated candidate list as
  presented in-session (all 32 terms with ratings, rationales, and the four
  filter-rejections shown twice) and approved all 28 filter-passing terms;
  the assistant recorded keep/drop into
  `results/tables/lexicon_candidates.csv` at my direction. The division of
  labour stands: the AI proposed and rated, the filters screened, I decided —
  my decision happened to be "agree with all 28", which is a review outcome,
  not a skipped review. The before/after now runs in human-reviewed mode.
- **k = 0.10 confirmed** as the headline tilt strength (grid still reported).
- Reconcile `CLAUDE.md` rule 7 (old cache location) — still pending.
- Phases 6-10 — Phase 6 built immediately after this log; see prompt_log_07
  if logged separately, else the session summary.
