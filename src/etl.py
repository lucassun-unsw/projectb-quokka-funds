"""Station 1 - ETL: load, clean, and quality-check the structured and text data.

Ported from the verified z5594806_projectA/src/etl.py (Part A Phase 1), unchanged.
Load raw data through ``src.data_access`` (see ``context/DATA_GUIDE.md``). Every
function here is importable and testable and returns a value - none of them write
to ``results/``. The orchestrator ``scripts/run_part_b.py`` calls these and saves
the exhibits.

Station 1 scope (descriptive only - no returns-across-merge, no sentiment scoring):
  1. load + cap the sample at 2023-12-31
  2. missing-date audit (per ticker, against the right calendar)
  3. duplicate audit (prices unique on ticker-date; news on ticker+date+title)
  4. OHLC internal-consistency screen
  5. outlier / extreme-return screen + keep-and-explain triage
  6. timezone-normalise the news dates before any merge
  7. clean schema + provenance
"""
from __future__ import annotations

import pandas as pd

from src import data_access

# Cap the usable sample here. Crypto carries 10 stray rows dated 2024-01-01; the
# other panels already end in 2023. Keep as a Timestamp for clean comparisons.
SAMPLE_END = pd.Timestamp("2023-12-31")

PRICE_COLS = ["open", "high", "low", "close", "adjClose"]


# --------------------------------------------------------------------------- #
# 1. Load + cap
# --------------------------------------------------------------------------- #
def _cap_sample(df: pd.DataFrame, end: pd.Timestamp = SAMPLE_END) -> pd.DataFrame:
    """Drop rows after ``end`` and sort. Dates must already be tz-naive."""
    return df[df["date"] <= end].sort_values(["ticker", "date"]).reset_index(drop=True)


def load_clean_equities() -> pd.DataFrame:
    """Equity prices, capped at 2023-12-31 and sorted by ticker then date."""
    return _cap_sample(data_access.load_equity_prices())


def load_clean_crypto() -> pd.DataFrame:
    """Crypto prices, capped at 2023-12-31 (drops the 10 stray 2024-01-01 rows)."""
    return _cap_sample(data_access.load_crypto_prices())


def load_clean_news() -> pd.DataFrame:
    """News headlines: tz-normalised to naive dates, capped, and deduplicated.

    The raw ``date`` is tz-aware UTC; price dates are tz-naive. Normalise here so a
    later merge/``merge_asof`` does not error. Dedupe on ticker+date+title (never
    ticker-date alone - many headlines per ticker-date is normal). Raw title text
    is preserved (VADER needs stopwords/casing in Part B).
    """
    df = data_access.load_news_headlines().copy()
    df["date"] = normalise_news_dates(df["date"])
    df = df[df["date"] <= SAMPLE_END]
    df = df.drop_duplicates(subset=["ticker", "date", "title"])
    return df.sort_values(["ticker", "date"]).reset_index(drop=True)


def normalise_news_dates(s: pd.Series) -> pd.Series:
    """Convert tz-aware UTC timestamps to tz-naive calendar dates (midnight)."""
    return s.dt.tz_convert("UTC").dt.tz_localize(None).dt.normalize()


# --------------------------------------------------------------------------- #
# 2. Missing-date audit
# --------------------------------------------------------------------------- #
def equity_trading_calendar(equities: pd.DataFrame) -> pd.DatetimeIndex:
    """Observed equity trading days = the union of dates any equity trades."""
    return pd.DatetimeIndex(sorted(equities["date"].unique()))


def missing_date_audit(prices: pd.DataFrame, calendar: pd.DatetimeIndex | None = None) -> pd.DataFrame:
    """Per-ticker missing-date count against the expected calendar.

    ``calendar`` given (equities): expected = trading days within the ticker's own
    [first, last] span. ``calendar=None`` (crypto, 365-day): expected = every
    calendar day in that span. Returns one row per ticker, worst gaps first.
    """
    rows = []
    for tkr, g in prices.groupby("ticker"):
        dates = pd.DatetimeIndex(sorted(g["date"].unique()))
        first, last = dates.min(), dates.max()
        if calendar is not None:
            expected = calendar[(calendar >= first) & (calendar <= last)]
        else:
            expected = pd.date_range(first, last, freq="D")
        n_missing = len(expected.difference(dates))
        rows.append({
            "ticker": tkr,
            "first": first.date(),
            "last": last.date(),
            "n_obs": len(dates),
            "n_expected": len(expected),
            "n_missing": n_missing,
            "pct_missing": round(100 * n_missing / len(expected), 3) if len(expected) else 0.0,
        })
    return pd.DataFrame(rows).sort_values("n_missing", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 3. Duplicate audit
# --------------------------------------------------------------------------- #
def duplicate_report_prices(prices: pd.DataFrame, label: str) -> dict:
    """Prices must be unique on ticker-date. Report any exact duplicates."""
    n_dup = int(prices.duplicated(subset=["ticker", "date"]).sum())
    return {"dataset": label, "key": "ticker+date", "n_rows": len(prices),
            "n_duplicate_rows": n_dup, "unique_ok": n_dup == 0}


def duplicate_report_news(raw_news: pd.DataFrame) -> pd.DataFrame:
    """Contrast the correct news key with the trap key.

    Exact-duplicate headlines are keyed on ticker+date+title (~2,847). Keying on
    ticker-date alone flags most rows because many headlines share a ticker-date -
    that is not duplication, so the row documents why the naive key is wrong.
    """
    news = raw_news.copy()
    news["date"] = normalise_news_dates(news["date"])
    exact = int(news.duplicated(subset=["ticker", "date", "title"]).sum())
    naive = int(news.duplicated(subset=["ticker", "date"]).sum())
    return pd.DataFrame([
        {"key": "ticker+date+title", "n_flagged": exact,
         "interpretation": "exact duplicate headlines - removed"},
        {"key": "ticker+date", "n_flagged": naive,
         "interpretation": "NOT duplicates - many headlines per ticker-day is normal"},
    ])


# --------------------------------------------------------------------------- #
# 4. OHLC internal-consistency screen
# --------------------------------------------------------------------------- #
def ohlc_consistency(prices: pd.DataFrame) -> pd.DataFrame:
    """Boolean violation flags per row; ``ohlc_ok`` is True when the bar is sound.

    Sound bar: high >= max(open, close, low), low <= min(open, close, high),
    all prices > 0, volume >= 0.
    """
    v = pd.DataFrame(index=prices.index)
    v["high_lt_low"] = prices["high"] < prices["low"]
    v["high_lt_open"] = prices["high"] < prices["open"]
    v["high_lt_close"] = prices["high"] < prices["close"]
    v["low_gt_open"] = prices["low"] > prices["open"]
    v["low_gt_close"] = prices["low"] > prices["close"]
    v["nonpos_price"] = prices[PRICE_COLS].le(0).any(axis=1)
    v["neg_volume"] = prices["volume"] < 0
    v["ohlc_ok"] = ~v.any(axis=1)
    return v


# --------------------------------------------------------------------------- #
# 5. Outlier / extreme-return screen + keep-and-explain triage
# --------------------------------------------------------------------------- #
def _simple_returns(prices: pd.DataFrame) -> pd.Series:
    """Per-ticker daily adjClose returns (screen-only; the canonical panel-merge
    returns live in Station 2 / features.py). First row per ticker is NaN."""
    return prices.groupby("ticker")["adjClose"].pct_change()


def outlier_triage(prices: pd.DataFrame, news: pd.DataFrame | None = None,
                   modz_thresh: float = 8.0, abs_floor: float = 0.20) -> pd.DataFrame:
    """Flag extreme daily returns and assign a keep-and-explain verdict.

    A row is flagged when its return is extreme by either rule:
      - robust modified z-score |0.6745*(r - median)/MAD| >= ``modz_thresh`` (per
        ticker), or
      - absolute one-day move |r| >= ``abs_floor`` (default 20%).
    Verdict: an OHLC-inconsistent bar is ``suspect-data``; an internally consistent
    extreme is a ``real-event`` (kept, not deleted, per the brief). Volume ratio and
    same-day headline count are recorded as corroborating evidence, not filters.
    """
    df = prices.sort_values(["ticker", "date"]).copy()
    df["ret"] = _simple_returns(df)

    # Robust per-ticker location/scale for the modified z-score.
    med = df.groupby("ticker")["ret"].transform("median")
    mad = df.groupby("ticker")["ret"].transform(lambda x: (x - x.median()).abs().median())
    df["modz"] = 0.6745 * (df["ret"] - med) / mad.replace(0, pd.NA)

    # Volume relative to the ticker's own median (a spike corroborates a real event).
    tkr_med_vol = df.groupby("ticker")["volume"].transform("median")
    df["volume_ratio"] = (df["volume"] / tkr_med_vol.replace(0, pd.NA)).round(2)

    flagged = df[(df["modz"].abs() >= modz_thresh) | (df["ret"].abs() >= abs_floor)].copy()

    ohlc = ohlc_consistency(flagged)
    flagged["ohlc_ok"] = ohlc["ohlc_ok"]

    # Same-day headline count (equities only; crypto carries no news).
    if news is not None and len(flagged):
        counts = (news.groupby(["ticker", "date"]).size()
                       .rename("n_headlines").reset_index())
        flagged = flagged.merge(counts, on=["ticker", "date"], how="left")
        flagged["n_headlines"] = flagged["n_headlines"].fillna(0).astype(int)
    else:
        flagged["n_headlines"] = 0

    flagged["verdict"] = flagged["ohlc_ok"].map({True: "real-event", False: "suspect-data"})

    cols = ["ticker", "date", "ret", "modz", "volume_ratio", "n_headlines",
            "ohlc_ok", "verdict"]
    return (flagged[cols].sort_values("ret", key=lambda s: s.abs(), ascending=False)
                        .reset_index(drop=True))


# --------------------------------------------------------------------------- #
# 6. Clean schema + provenance
# --------------------------------------------------------------------------- #
def dataset_inventory(equities: pd.DataFrame, crypto: pd.DataFrame,
                      news: pd.DataFrame) -> pd.DataFrame:
    """Dataset-inventory table: rows, date span, frequency, and coverage per dataset."""
    def span(df):
        return f"{df['date'].min().date()} to {df['date'].max().date()}"
    return pd.DataFrame([
        {"dataset": "equity_prices", "rows": len(equities),
         "date_span": span(equities), "frequency": "daily (trading days)",
         "coverage": f"{equities['ticker'].nunique()} equities, "
                     f"{equities['sector'].nunique()} sectors"},
        {"dataset": "crypto_prices", "rows": len(crypto),
         "date_span": span(crypto), "frequency": "daily (7 days/week)",
         "coverage": f"{crypto['ticker'].nunique()} cryptocurrencies, no sector"},
        {"dataset": "news_headlines", "rows": len(news),
         "date_span": span(news), "frequency": "event (many per ticker-day)",
         "coverage": f"{news['ticker'].nunique()} equities, "
                     f"{news['sector'].nunique()} sectors"},
    ])


def integrity_summary(*, audit_eq: pd.DataFrame, audit_cr: pd.DataFrame,
                      dup_eq: dict, dup_cr: dict, dup_news: pd.DataFrame,
                      ohlc_eq: pd.DataFrame, ohlc_cr: pd.DataFrame,
                      triage_eq: pd.DataFrame, triage_cr: pd.DataFrame,
                      n_stray_crypto: int) -> pd.DataFrame:
    """One row per Station 1 check: what was checked, found, and resolved.

    Assembles the individual check outputs into an integrity-summary exhibit -
    issues quantified AND resolved, with the row-level detail left in
    ``outlier_triage.csv``.
    """
    def _verdicts(triage: pd.DataFrame) -> str:
        if not len(triage):
            return "0 flagged"
        counts = triage["verdict"].value_counts().to_dict()
        parts = [f"{n} {v}" for v, n in sorted(counts.items())]
        return f"{len(triage)} flagged ({', '.join(parts)})"

    exact = int(dup_news.loc[dup_news["key"] == "ticker+date+title",
                             "n_flagged"].iloc[0])
    naive = int(dup_news.loc[dup_news["key"] == "ticker+date",
                             "n_flagged"].iloc[0])
    rows = [
        {"dataset": "crypto_prices", "check": "sample cap at 2023-12-31",
         "found": f"{n_stray_crypto} stray 2024-01-01 rows",
         "resolution": "dropped; all panels end 2023-12-31"},
        {"dataset": "equity_prices", "check": "missing-date audit (trading calendar)",
         "found": f"{int(audit_eq['n_missing'].sum())} missing days across "
                  f"{int((audit_eq['n_missing'] > 0).sum())} of {len(audit_eq)} tickers",
         "resolution": "documented; returns computed per ticker on observed dates"},
        {"dataset": "crypto_prices", "check": "missing-date audit (365-day calendar)",
         "found": f"{int(audit_cr['n_missing'].sum())} missing days across "
                  f"{int((audit_cr['n_missing'] > 0).sum())} of {len(audit_cr)} tickers",
         "resolution": "complete calendar - no gaps to handle"
         if int(audit_cr["n_missing"].sum()) == 0 else
         "documented; returns computed on observed dates"},
        {"dataset": "equity_prices", "check": "duplicate rows (ticker+date)",
         "found": f"{dup_eq['n_duplicate_rows']} duplicates",
         "resolution": "unique key confirmed" if dup_eq["unique_ok"]
         else "duplicates dropped"},
        {"dataset": "crypto_prices", "check": "duplicate rows (ticker+date)",
         "found": f"{dup_cr['n_duplicate_rows']} duplicates",
         "resolution": "unique key confirmed" if dup_cr["unique_ok"]
         else "duplicates dropped"},
        {"dataset": "news_headlines", "check": "duplicate headlines (ticker+date+title)",
         "found": f"{exact} exact duplicates",
         "resolution": "removed; ticker+date alone flags "
                       f"{naive} rows but many headlines per ticker-day is normal"},
        {"dataset": "equity_prices", "check": "OHLC internal consistency",
         "found": f"{int((~ohlc_eq['ohlc_ok']).sum())} inconsistent bars",
         "resolution": "all bars internally consistent"
         if bool(ohlc_eq["ohlc_ok"].all()) else "flagged in outlier triage"},
        {"dataset": "crypto_prices", "check": "OHLC internal consistency",
         "found": f"{int((~ohlc_cr['ohlc_ok']).sum())} inconsistent bars",
         "resolution": "all bars internally consistent"
         if bool(ohlc_cr["ohlc_ok"].all()) else "flagged in outlier triage"},
        {"dataset": "equity_prices", "check": "extreme-return screen (|modz|>=8 or |r|>=20%)",
         "found": _verdicts(triage_eq),
         "resolution": "kept and explained - real events, not errors "
                       "(see outlier_triage.csv)"},
        {"dataset": "crypto_prices", "check": "extreme-return screen (|modz|>=8 or |r|>=20%)",
         "found": _verdicts(triage_cr),
         "resolution": "kept and explained - real events, not errors "
                       "(see outlier_triage.csv)"},
        {"dataset": "news_headlines", "check": "timezone/dtype vs price dates",
         "found": "dates tz-aware UTC; price dates tz-naive",
         "resolution": "normalised to tz-naive calendar dates before any merge"},
    ]
    return pd.DataFrame(rows, columns=["dataset", "check", "found", "resolution"])


def clean_schema(equities: pd.DataFrame, crypto: pd.DataFrame,
                 news: pd.DataFrame) -> pd.DataFrame:
    """One row per clean dataset: shape, span, frequency, key, and provenance."""
    def span(df):
        return f"{df['date'].min().date()} to {df['date'].max().date()}"
    return pd.DataFrame([
        {"dataset": "equity_prices", "n_rows": len(equities),
         "n_tickers": equities["ticker"].nunique(), "date_span": span(equities),
         "frequency": "trading days (~252/yr)", "key": "ticker+date",
         "source": "data_access.load_equity_prices (hosted ZIP)",
         "provenance": "raw OHLCV+adjClose+sector; capped at 2023-12-31, sorted"},
        {"dataset": "crypto_prices", "n_rows": len(crypto),
         "n_tickers": crypto["ticker"].nunique(), "date_span": span(crypto),
         "frequency": "calendar days (~365/yr)", "key": "ticker+date",
         "source": "data_access.load_crypto_prices (hosted ZIP)",
         "provenance": "raw OHLCV+adjClose; dropped 10 stray 2024-01-01 rows, sorted"},
        {"dataset": "news_headlines", "n_rows": len(news),
         "n_tickers": news["ticker"].nunique(), "date_span": span(news),
         "frequency": "event (many per ticker-day)", "key": "ticker+date+title",
         "source": "data_access.load_news_headlines (hosted ZIP)",
         "provenance": "UTC->tz-naive dates; deduped on ticker+date+title; raw title kept"},
    ])
