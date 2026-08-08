"""Station 2 - return features: daily returns, the combined panel, and stats.

Ported from the verified z5594806_projectA/src/features.py, unchanged. Two rules
from the brief are load-bearing and enforced here:

  1. Returns BEFORE merge. Compute each ticker's daily returns on its own calendar
     first, then left-merge crypto returns onto the equity trading calendar. Never
     merge price levels across the two calendars and difference after - that
     manufactures spurious weekend returns.
  2. Calendar mismatch. Equities trade ~252 days/yr, crypto ~365. Any annualised
     figure uses sqrt(252) for equities and sqrt(365) for crypto - never one
     blanket factor across both.

Every function is importable and returns a value; none write to ``results/`` (that
is the orchestrator's job). The headline text panel is Station 2 as well but lives
in ``src/text_panel.py``; this module is prices only. The Part B fund optimisers
(``src/portfolios.py``) build on ``build_combined_panel``/``asset_class_aggregate``
but must never treat this module's naive equal-weight aggregate as a fund.
"""
from __future__ import annotations

import pandas as pd

# Trading-days-per-year by asset class. Equities settle on the exchange calendar
# (~252); crypto trades every calendar day (~365). Used for annualisation only.
ANN_DAYS = {"equity": 252, "crypto": 365}

# Fixed asset-class order so exhibits read equity-then-crypto, not alphabetical.
_CLASS_ORDER = ["equity", "crypto"]


# --------------------------------------------------------------------------- #
# 1. Daily returns (within each panel, on its own calendar)
# --------------------------------------------------------------------------- #
def daily_returns(prices: pd.DataFrame, price_col: str = "adjClose") -> pd.DataFrame:
    """Add a per-ticker daily simple-return column ``ret`` using ``adjClose``.

    Returns the input sorted by ticker then date with one extra column. Returns are
    ``pct_change()`` within each ticker on its own calendar, so the first row per
    ticker is NaN (expected - there is no prior close to difference against). Use
    ``adjClose`` (dividend/split-adjusted), never ``close``, and never ``.diff()``.
    """
    out = prices.sort_values(["ticker", "date"]).copy()
    out["ret"] = out.groupby("ticker")[price_col].pct_change()
    return out.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 2. Combined panel (returns first, THEN left-merge onto the equity calendar)
# --------------------------------------------------------------------------- #
def _returns_panel(equities: pd.DataFrame, crypto: pd.DataFrame,
                   crypto_on_equity_days: bool) -> pd.DataFrame:
    """Shared construction: per-class returns, optionally filtered to equity days."""
    eq = daily_returns(equities)
    eq["asset_class"] = "equity"

    cr = daily_returns(crypto)
    cr["asset_class"] = "crypto"
    cr["sector"] = "Crypto"

    if crypto_on_equity_days:
        trading_days = pd.DatetimeIndex(sorted(equities["date"].unique()))
        cr = cr[cr["date"].isin(trading_days)]

    cols = ["date", "ticker", "asset_class", "sector", "ret"]
    panel = pd.concat([eq[cols], cr[cols]], ignore_index=True)
    return panel.sort_values(["asset_class", "ticker", "date"]).reset_index(drop=True)


def build_combined_panel(equities: pd.DataFrame, crypto: pd.DataFrame) -> pd.DataFrame:
    """Long panel of daily returns for both asset classes on the equity calendar.

    Steps, in order:
      1. Compute returns within each panel on its own calendar (``daily_returns``).
      2. Left-merge crypto returns onto the observed equity trading days: keep only
         the crypto rows whose date is an equity trading day. Crypto returns are
         still one-day moves on the 365-day calendar; the weekend-only moves are
         dropped, not summed into Monday. That is the intended combined panel.

    Columns: ``date, ticker, asset_class, sector, ret``. Equities carry their real
    sector; crypto has no sector, so it is tagged ``"Crypto"``. The leading NaN
    return per ticker is kept so row counts reconcile with the price panels; every
    downstream statistic drops it.

    This is the CROSS-ASSET object (aggregates, dependence analysis, Part B fund
    return matrices). For the descriptive-stats table use ``build_stats_panel``
    instead, so the crypto row describes its own full calendar.
    """
    return _returns_panel(equities, crypto, crypto_on_equity_days=True)


def build_stats_panel(equities: pd.DataFrame, crypto: pd.DataFrame) -> pd.DataFrame:
    """Long returns panel with each asset class on its OWN calendar.

    Identical to ``build_combined_panel`` except crypto keeps all ~365 days/yr
    (14,610 rows) instead of being filtered to equity trading days. Use this for
    ``descriptive_stats_by_class``: crypto weekdays are more volatile than
    weekends, so weekday-only sampling paired with the sqrt(365) factor overstates
    annualised crypto vol (~107% vs ~99% on the full calendar). The sample must
    match the annualisation factor - full crypto calendar with sqrt(365).
    """
    return _returns_panel(equities, crypto, crypto_on_equity_days=False)


# --------------------------------------------------------------------------- #
# 3. Descriptive statistics by asset class
# --------------------------------------------------------------------------- #
def descriptive_stats_by_class(panel: pd.DataFrame) -> pd.DataFrame:
    """One row per asset class: daily moments plus correctly annualised figures.

    Pools every ticker's daily returns within the class. Daily columns are the
    primary characterisation; annualised columns state their factor explicitly and
    use the class-specific calendar (252 vs 365) so the two rows are comparable
    without a hidden blanket factor. ``excess_kurtosis`` is Fisher (0 = normal).
    Pass ``build_stats_panel`` output so each class is described on its own
    calendar and the sample matches the annualisation factor.
    """
    rows = []
    for cls, g in panel.groupby("asset_class"):
        r = g["ret"].dropna()
        n = ANN_DAYS[cls]
        mean_d, vol_d = r.mean(), r.std()
        rows.append({
            "asset_class": cls,
            "n_tickers": g["ticker"].nunique(),
            "n_obs": len(r),
            "mean_daily": mean_d,
            "vol_daily": vol_d,
            "min_daily": r.min(),
            "max_daily": r.max(),
            "skew": r.skew(),
            "excess_kurtosis": r.kurt(),
            "ann_factor_days": n,
            "mean_annual": mean_d * n,
            "vol_annual": vol_d * (n ** 0.5),
            "sharpe_annual": (mean_d * n) / (vol_d * (n ** 0.5)) if vol_d else float("nan"),
        })
    out = pd.DataFrame(rows)
    out["asset_class"] = pd.Categorical(out["asset_class"], _CLASS_ORDER, ordered=True)
    return out.sort_values("asset_class").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 4. Equal-weight asset-class aggregate return series
# --------------------------------------------------------------------------- #
def asset_class_aggregate(panel: pd.DataFrame) -> pd.DataFrame:
    """Equal-weight daily mean return per asset class, wide (date x asset_class).

    Each day's value is the cross-sectional mean of that class's ticker returns - a
    naive equal-weight basket, NOT a constructed fund (no optimisation). Feeds the
    growth-of-$1 figure and ``dependence.py``'s aggregate inputs. Indexed by date
    over the equity trading calendar.
    """
    agg = (panel.dropna(subset=["ret"])
                .groupby(["date", "asset_class"])["ret"].mean()
                .unstack("asset_class"))
    cols = [c for c in _CLASS_ORDER if c in agg.columns]
    return agg[cols].sort_index()


def cumulative_growth(agg: pd.DataFrame) -> pd.DataFrame:
    """Growth of $1 from the equal-weight aggregate returns: cumprod(1 + r).

    Starts each series at its first observed return date. Used by the cumulative-
    returns figure; crypto and equities share the equity trading calendar here.
    """
    return (1.0 + agg.fillna(0.0)).cumprod()


def rolling_volatility(agg: pd.DataFrame, window: int = 21) -> pd.DataFrame:
    """Annualised rolling volatility of each asset-class aggregate (descriptive).

    ``vol_ann = std(r, window) * sqrt(ann_days)`` with the class-specific calendar
    factor. Default 21-day window ~ one trading month. Optional feature; carries no
    allocation claim.
    """
    out = pd.DataFrame(index=agg.index)
    for c in agg.columns:
        out[c] = agg[c].rolling(window).std() * (ANN_DAYS.get(c, 252) ** 0.5)
    return out
