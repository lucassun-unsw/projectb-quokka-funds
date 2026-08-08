# CLAUDE.md — working rules for this project (z5594806, Part B)

These are my instructions to Claude Code for FINS3645 Project Part B. Read this,
then `PROJECT_BRIEF.md`, `context/`, and my own planning doc —
`report/OUTLINE.md` (the build plan, the report structure, and the frozen Part A
facts and decisions carried from my finished, verified Part A) — before you
touch code. When this file and the brief disagree, tell me — do not silently
pick one. When this file and `report/OUTLINE.md` disagree (the plan evolves
faster than this file), `report/OUTLINE.md` wins — flag the drift so I can
reconcile this file.

## What this project is

Part B is the funds, sentiment, and app build (DFF Stations 3-4) on top of my
own verified Part A foundation. I reuse Part A's cleaned data, returns, and
text panel unchanged, then build: out-of-sample fund optimisation (four
methods — max-Sharpe, min-variance, risk parity, min-CVaR — across combined /
equity-only / crypto-only asset families), a finVADER sector sentiment index,
a sentiment-fusion tilt, and a deployed Streamlit app.

**Hard scope boundary:** Part A's cleaning/returns/text-panel logic in
`src/etl.py`, `src/features.py`, `src/text_panel.py` is FROZEN — ported
verbatim from Part A, verified to reproduce Part A's exact frozen numbers
(equity 50,300×9, crypto 14,610 post-cap, combined panel 60,360 rows). Do not
re-derive or re-argue these; if a Part B task seems to require changing them,
stop and flag it to me first.

## My own plan — read before big changes

- `report/OUTLINE.md` is the living build plan: locked decisions (the four
  fund methods, EWMA covariance, min-CVaR + co-crash panel as the innovation
  anchor, sentiment/fusion rules, what was considered and explicitly
  rejected — EVT, ARIMA, GARCH-conditional-EVT — and why), the coding-style
  reference carried from weeks 7-9, the verification checkpoints (lessons
  from Part A's own late-caught mistakes), and the full report section plan.
- The frozen Part A facts (data sizes, return stats, calendar rules) and the
  innovation bridges live in this file's "Hard scope boundary" above and in
  `OUTLINE.md`'s Locked decisions.
- If I ask for something that contradicts a locked decision in `OUTLINE.md`,
  point it out rather than silently building the new version — I may be
  changing my mind, or I may have forgotten what I already decided.

## Data — how to load it

- Load only through `src/data_access.py` (identical to Part A's, provided,
  untouched). Never hardcode a path to a parquet/CSV, never re-download, never
  commit any data file.
- Reference for schema, tickers, and sectors: `context/DATA_GUIDE.md`.

## Non-negotiable correctness rules (Part B traps)

These are the mistakes the brief explicitly penalises, plus the ones specific
to funds/sentiment/fusion. Follow them exactly and name which one a given
change touches.

1. **No look-ahead, anywhere.** Fund weights are formed only from data
   strictly before each rebalance date (walk-forward, expanding window,
   ~252-day burn-in). Sentiment is lagged **≥1 trading day** before it can
   affect any rebalance. If a function needs "today's" data to decide
   "today's" weights or tilt, that is a bug.
2. **Three fund families, two possible calendars.** Combined and equity-only
   funds annualise with `sqrt(252)`; a crypto-only fund (365-day calendar)
   uses `sqrt(365)`. Never assume the factor from the family name — check the
   actual trading-day count. `performance_metrics.csv` carries an explicit
   `calendar` column per row so this is checkable, not assumed.
3. **EWMA covariance, recomputed only from past data**, feeds every fund
   method (not a static full-window sample covariance) — the time-series
   anchor. Recompute at each rebalance from data strictly before that date.
4. **Rockafellar–Uryasev min-CVaR** is a linear program
   (`scipy.optimize.linprog`), not a variance objective — do not silently
   substitute a variance-based approximation.
5. **Sentiment scoring uses finVADER** (VADER + SentiBigNomics + Henry
   lists), not bare VADER — port `week9/fear_greed_index/fear_greed_tools.py`'s
   pattern. Never strip casing/punctuation/stopwords before scoring; VADER
   needs them. Cache distinct-headline scores (~150k headlines) outside
   `results/` — see the `.gitignore` note below.
6. **No-headline-day rule**: leave a sector-day undefined in the sentiment
   index when there are no headlines that day (do not fabricate neutral);
   forward-fill up to 5 trading days for fusion's per-day signal requirement,
   then neutral beyond that gap. Both choices stated and justified in the
   report, not just implemented.
7. **Two artifact traps, both verified the hard way**: `.gitignore`'s
   `!results/**` re-includes everything under `results/` (overriding the
   blanket `*.parquet`/`*.csv` ignores), AND `scripts/check_handin.py` scans
   the *filesystem* for any `.parquet`/`.csv` outside `results/` — it never
   consults git, so even a correctly gitignored in-project cache fails the
   hand-in check. The scoring cache therefore lives OUTSIDE the project at
   `~/.cache/fins3645_z5594806_projectB/` (`sentiment.CACHE_PATH`); it
   regenerates deterministically on a clean machine. The checker also greps
   literal strings — no "nltk" text in `streamlit_app.py`, even in prose.
8. **The deployed app reads only precomputed `results/`** — never imports
   `nltk`, never recomputes a backtest. The free tier cannot run either.
9. **Transaction costs are modelled, not assumed away.** The brief allows zero
   costs if stated, and counts a turnover/cost model as an innovation — so
   `oos_backtest` charges cost on two-way turnover at each rebalance over a
   0/10/20/50 bps grid, with the first rebalance charged as a full entry from
   cash. The headline fund numbers are still the gross (0 bps) ones, and the
   report must say so *with* the measured consequences rather than as a bare
   caveat: the Sharpe podium never reorders across the grid, and the
   EWMA-vs-static choice breaks even near 20 bps. Never quote a net number
   without its cost level.
10. **Fund naming**: each (asset family, method) pair is one named fund
    (e.g. "Combined Min-CVaR", "Equity-Only Risk Parity") — this naming is
    what `fund_returns.csv`/`fund_weights.csv`/the app's fund picker key off.

## Required outputs (exact filenames — the app and markers grep for these)

- `results/data/fund_returns.csv`, `results/data/fund_weights.csv`,
  `results/data/sector_sentiment_index.csv`,
  `results/tables/performance_metrics.csv`.
- Figures in `results/figures/` (any clear name), other tables in
  `results/tables/`. Never commit raw data.

Everything must be reproducible from `python scripts/run_part_b.py` on a clean
checkout, then `streamlit run streamlit_app.py` locally, then
`python scripts/check_handin.py` with no `[FAIL]`.

## Code conventions

- Real logic lives in `src/` (`etl.py`/`features.py`/`text_panel.py` =
  ported Part A foundation, frozen; `dependence.py` = ported Part A tail-
  dependence machinery, reused for the co-crash panel; `portfolios.py` =
  Station 3 funds/backtest; `sentiment.py` = Station 3 sentiment;
  `fusion.py` = the sentiment tilt). `scripts/run_part_b.py` orchestrates and
  writes to `results/` — it must pass the *same* computed objects into every
  CSV/figure/app call site, never re-derive a slightly-different version at
  each site (this is exactly what went wrong late in Part A — see
  `OUTLINE.md`'s "Verification checkpoints").
- Carry the week 7/8/9 house style for new code (`sentiment.py` especially):
  small testable functions, docstrings that state the *why* not just the
  *what*, print-driven diagnostics at every stage, FT figure helpers
  (`apply_ft_style`/`ft_header`/`save_ft` from `src/ft_style.py`) copied in
  rather than re-derived.
- Use the repo interpreter: `../../.venv/bin/python` (macOS). Packages in
  `requirements.txt` (deployed app, kept slim) / `requirements-dev.txt`
  (build-only, e.g. `nltk`) — add to the right file first, tell me.
- Own the judgement-call parameters explicitly rather than silently
  defaulting them: the min-CVaR confidence level, the fusion tilt strength
  `k`, the forward-fill cap, the EWMA span, the burn-in length. Lay out the
  trade-off and hand the choice back to me; state my decision plainly when I
  make it.

## How you must behave (verification & honesty)

Read `context/verify_ai_output.md` — treat every output as a draft to be
checked.
- **Never invent** a citation, a statistic, a ticker/sector example, or a
  dataset fact. Check named examples against `context/DATA_GUIDE.md` or an
  actual output CSV — Part A once cited tickers that don't exist in this data.
- **Show your working** for any number you produce, so I can re-run it. Any
  percentage that ends up in the report (fusion before/after, co-crash gap,
  lexicon coverage) must exist as a literal number in a saved CSV, not
  hand-computed in prose.
- Tell me plainly if a planned result doesn't survive the data (e.g. the
  min-CVaR fund doesn't actually protect on crash days) — rewrite the
  narrative around what the numbers show, the way Part A's copula finding
  pivoted from "tail dependence" to "empirical asymmetry."
- Do not claim something runs unless you actually ran it and saw the output.

## What you must NOT write for me

Per the course AI policy, **the report's economic interpretation and written
analysis must be my own words.** You may draft code, docstrings, figure
helpers, and report *structure*/notes — not the interpretive prose I submit.

## AI logging (this is graded — 20%)

I keep prompt logs in `ai/`. After a non-trivial task, remind me to log: the
prompt, what you produced, what was wrong or risky, and what I changed and
why. Honest "the AI got this wrong and here's my fix" entries are worth the
most — see `ai/AI_NOTES.md` for the running log and `ai/prompt_log_*.md` for
per-task detail, same discipline as Part A.
