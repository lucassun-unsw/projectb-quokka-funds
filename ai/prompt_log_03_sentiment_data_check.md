# Prompt log — sentiment construction: checking the brief's exact wording against real data before coding

## What I wanted
Before writing `src/sentiment.py`, confirm I actually understood the brief's
sentiment-index construction requirement precisely (not just the gist), check
whether our plan's cited week 9 pattern actually implements it, and check the
real headline data for coverage gaps that would make the no-headline-day
decision arbitrary rather than evidence-based.

## Prompt(s)
- Pasted the brief's Station 3 sentiment paragraph verbatim and asked: "make
  sure you understand this and how this model affect our four [fund] model?
  and check the data that if our model are fits? before doing any actual
  coding."

## What the assistant produced
- A breakdown of the paragraph into five separate requirements, flagging one
  precise phrase — "average ticker-day sentiment within each sector
  (equal-weight the tickers)" — as a specific two-step construction, not a
  single groupby.
- A live data check (real hosted data, via the ported `etl`/`text_panel`):
  ticker-day headline coverage (75.5% covered / 24.5% zero across the full
  50-ticker x 1,006-trading-day grid), per-sector coverage confirming and
  quantifying `DATA_GUIDE.md`'s "thin sectors" warning (Materials 53.1%,
  Real Estate 55.6%, Utilities 59.3% vs Consumer 93.9%), whole-sector
  blackout rate (rare, 0-6.6% even in the worst sectors), within-sector
  headline concentration across tickers (median busiest-ticker share 44%; one
  ticker holds >=70% of a sector-day's headlines 9.9% of the time), and a
  concrete alignment/lag check against the brief's own Saturday/Monday example
  using a real date.

## What was wrong or risky
- **The plan's Phase 3 note said "equal-weight mean of ticker-day scores...
  (`daily_index` pattern from week 9)" — but those two things are not the
  same function.** Week 9's `daily_index(scores, ["date","sector"])` flat-
  averages every headline in a sector-day directly; it does not compute a
  ticker-day score first and then equal-weight across tickers. The prose in
  last session's plan stated the correct brief wording but pointed at code
  that doesn't implement it — I would have ported the wrong function if I'd
  gone straight to coding from that note.
- This wasn't hypothetical: the concentration check showed one ticker holds
  >=70% of a sector-day's headlines on 9.9% of days, so the two aggregation
  orders would have produced visibly different index values, not a rounding
  difference.

## What I changed and why
- Rewrote `sector_sentiment_index()`'s spec in `report/OUTLINE.md` as an
  explicit two-step function (`ticker_day_score` then equal-weight across
  tickers), with a direct instruction not to port week 9's `daily_index`
  pattern for this step.
- Split the no-headline-day rule into three explicit levels instead of one
  blended "sector/ticker" statement: ticker-day (drop from that day's sector
  average — justified because even the worst sector still averages ~2.84 of 5
  tickers active on a news day, so dropping one silent ticker isn't dropping
  most of the evidence), sector-day (leave undefined, rare and now quantified
  per sector), and fusion's separate per-ticker forward-fill requirement
  (fusion needs a signal every trading day; the standalone index does not).
- Added the thin-sector noisiness finding as a named Section 6 limitation,
  since it's now a data-verified caveat rather than a generic disclaimer.

## Verification I did myself
- Ran every number above against the real hosted data through the already-
  isolation-tested `etl`/`text_panel` port, not from memory or a guess at
  typical news-coverage patterns.
- Checked the brief's own Saturday/Monday lag example against a real date in
  the data (2020-01-18, a Saturday) and found the alignment logic actually
  generalises the example correctly: it forward-mapped to Tuesday 2020-01-21,
  not Monday, because Monday 2020-01-20 was a US market holiday (MLK Day) —
  confirmed the trading-day alignment handles holidays, not just weekends, and
  that a plain `.shift(1)` in trading-day-index space correctly implements the
  "≥1 trading day" lag including that edge case.
