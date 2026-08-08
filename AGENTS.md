# AGENTS.md — z5594806, Part B

I work on this project with Claude Code, so my full agent instructions,
conventions, and correctness rules live in **`CLAUDE.md`** in this folder. Any
assistant that reads `AGENTS.md` (Codex, etc.) should follow that same file,
and also read `report/OUTLINE.md` (the build plan, which also carries the frozen
facts from Part A) before making changes.

Short version of the rules that matter most:

- Part B is DFF Stations 3-4: out-of-sample fund optimisation (four methods —
  max-Sharpe, min-variance, risk parity, min-CVaR — across combined /
  equity-only / crypto-only asset families), a finVADER sector sentiment
  index, a sentiment-fusion tilt, and a deployed Streamlit app. Reuse my
  verified Part A foundation (`src/etl.py`, `features.py`, `text_panel.py`) —
  it is frozen and ported unchanged; do not re-derive it.
- No look-ahead anywhere: fund weights and the sentiment signal come only
  from data strictly before the date they act on. Sentiment lags ≥1 trading
  day. EWMA covariance recomputed at each rebalance from past data only.
- 252-day vs 365-day annualisation depends on the actual fund family's
  trading calendar, never assumed from the family name.
- Required outputs: `results/data/fund_returns.csv`,
  `results/data/fund_weights.csv`, `results/data/sector_sentiment_index.csv`,
  `results/tables/performance_metrics.csv`.
- The deployed app reads only precomputed `results/` — never imports `nltk`,
  never recomputes a backtest.
- Never invent citations, numbers, or dataset facts (check tickers/sectors
  against `context/DATA_GUIDE.md`); show your working; do not write the
  economic interpretation I submit as my own.

See `CLAUDE.md` for the full version.
