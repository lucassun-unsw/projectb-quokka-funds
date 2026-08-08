# Quokka — downside-aware multi-asset funds with news-sentiment analytics

FINS3645 Financial Market Data Design & Analysis · Project Part B (Stations 3–4)
Lucas Sun · z5594806 · UNSW

**Live app:** https://projectb-quokka-funds-ihndbhpfsgr2aqfwey6ees.streamlit.app
**Repository:** https://github.com/lucassun-unsw/projectb-quokka-funds

> University coursework, **not investment advice**. Every fund here is a
> walk-forward backtest over a fixed 2020–2023 teaching dataset. None is a
> tradeable product, past backtested performance is not a forecast, and nothing in
> this repository is a recommendation to buy or sell any security.

---

## What this is

Quokka offers twelve systematically managed funds built from 50 US large-caps and
10 cryptocurrencies, and judges them on the days that actually hurt rather than on
average. Each **(asset family × method)** pair is one named fund:

| | Max-Sharpe | Min-Variance | Risk Parity | Min-CVaR |
|---|---|---|---|---|
| **Combined** (60 assets) | ✓ | ✓ | ✓ | ✓ |
| **Equity-Only** (50) | ✓ | ✓ | ✓ | ✓ |
| **Crypto-Only** (10) | ✓ | ✓ | ✓ | ✓ |

Alongside the funds, a standalone news-sentiment index across the ten equity
sectors, scored from ~105k distinct headlines with a finance-tuned VADER lexicon.

**Recommended fund: Combined Min-CVaR.** Not the top Sharpe — Combined Risk Parity
wins that at 0.84 — but the fund that holds up when equities and crypto fall
together. That trade-off is the point of the project, and the app shows both sides.

## What goes beyond the course baseline

- **A minimum-CVaR fund** solved as a Rockafellar–Uryasev linear program on
  historical scenarios (β = 0.95) — a genuine tail objective, not a variance proxy.
- **A co-crash stress panel with a paired bootstrap** (2,000 draws) over days when
  both asset classes were in their own worst *q*%. It changes the recommendation a
  Sharpe ranking would give: the protective pair beats the exposed pair by
  0.94–2.22pp per crash day, every interval excluding zero.
- **A transaction-cost model built into the backtest**, charged on two-way turnover
  at every rebalance across a 0/10/20/50 bps grid.
- **A finance-lexicon extension**: 28 human-reviewed terms on top of finVADER,
  found by looking for inflection gaps ("downgrade" is covered, "downgrades" is
  not — VADER does no stemming).
- **A sentiment-fusion tilt** on the equity sleeve, reported honestly: negligible
  gross, and roughly zero-to-negative net of 20 bps. A naive extension that did not
  pay, explained rather than tuned until it flattered.
- **Two deliberate design registers.** The report exhibits use a cream
  Financial-Times style; the app is a dark trading-terminal surface where hue
  encodes method and dash pattern encodes asset family, giving twelve funds twelve
  distinct, test-pinned pairs.

## How to run it

Python 3.13. From this folder:

```bash
pip install -r requirements.txt -r requirements-dev.txt   # dev adds nltk + finvader
python scripts/run_part_b.py        # reproduces every artifact into results/
streamlit run streamlit_app.py      # the app, reading only precomputed results/
python scripts/check_handin.py      # pre-submission checks
python -m pytest tests/ -q          # 26 tests
```

`run_part_b.py` takes a few minutes on a first run — it scores ~105k distinct
headlines and solves 520 portfolio optimisations. Headline scores are cached outside
the project at `~/.cache/fins3645_z5594806_projectB/`, so later runs are fast. The
deployed app does none of this: it reads the committed CSVs in `results/`.

Raw data loads through the provided helper (`src/data_access.py`) from the hosted
course bundle and is **never committed**.

## Layout

```
streamlit_app.py        the app (entrypoint, repo root)
src/
  data_access.py        provided helper, unmodified
  etl.py features.py text_panel.py    frozen Part A foundation
  dependence.py         Part A tail-dependence machinery, reused for co-crash
  portfolios.py         four optimisers, EWMA covariance, walk-forward backtest
  sentiment.py          finVADER scoring, two-step sector index, lagged signal
  fusion.py             the sentiment tilt
  lexicon.py            AI-proposed / human-reviewed lexicon extension
  ft_style.py           report figure style       app_theme.py  app surface
scripts/
  run_part_b.py         one command, every artifact
  check_handin.py       pre-submission checks
results/
  data/                 3 app-readable CSVs (the brief's required names)
  tables/               15 result tables       figures/  8 FT-style figures
report/                 report.docx → report.pdf, plus OUTLINE.md
tests/                  26 tests
ai/                     prompt logs + AI_NOTES.md (the graded AI workflow)
context/                provided data guide and project context
```

## Correctness rules this code enforces

These are the traps the brief names, and where each one is held:

- **No look-ahead.** Weights come only from `returns.iloc[:start]` — strictly
  before each rebalance. Tested by scrambling every future observation and
  requiring bit-identical past weights.
- **Sentiment lags ≥ 1 trading day**, enforced inside `sentiment.fusion_signal`,
  which rejects `lag=0`. Verified exact: `signal[t] == raw[t−1]` to 0.0.
- **√252 for Combined and Equity-Only, √365 for Crypto-Only**, never blended, with
  a `calendar` column on every metrics row so a wrong factor shows up as a wrong
  column instead of a silent error.
- **Weight caps are family-specific** — 10%, but 25% for Crypto-Only, because
  10 assets × 10% saturates exactly and collapses all four methods into the same
  equal-weight fund. `check_cap_feasible` blocks it.
- **The deployed app recomputes nothing** and never imports the scoring stack.

Each of these has a test that was shown to fail when the rule is broken — the tests
were checked by injecting the defects, not by reading them.

## Reproducibility

`run_part_b.py` is deterministic (seeded bootstrap, deterministic solvers) and has
been re-run and checksummed repeatedly: a full rebuild leaves every artifact
bit-identical apart from ones deliberately changed. `ruff check .` passes with no
flags, using the project-local `ruff.toml`.

## Deploying (Part B hand-in)

This folder is its own GitHub repository, independent of `fins-agent`, with
`streamlit_app.py` at the root. See `docs/STUDENT_DEPLOY.md` and
`PROJECT_BRIEF.md` Appendix D. Commit the precomputed `results/` artifacts — the app
reads them and the free tier cannot rebuild them. Make the repo **public** at
hand-in, confirm the live app loads, and submit the URL and repo link alongside the
zip.
