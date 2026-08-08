"""Station 3 (extension) - fuse the sentiment signal into the fund weights.

The locked fusion rule (report/OUTLINE.md): a per-ticker sentiment-z tilt on the
EQUITY sleeve of a fund's target weights,

    tilted_i = w_i * (1 + k * clip(z_i, -2, 2)),

renormalised so the equity sleeve keeps its original total weight, then re-capped.
Crypto weights are never touched - crypto has no headlines, so sentiment applies
to the equity data only (brief rule).

Look-ahead safety is INHERITED, not re-implemented: ``sentiment.fusion_signal``
already shifts the signal by >= 1 trading day and ``sentiment.sentiment_z``
standardises on a trailing window only. This module must consume that z frame
as-is - re-shifting here would double the lag, and un-shifting would be
look-ahead. The one check this module adds: a tilt at rebalance date d reads
``z.loc[d]``, which by construction contains information through d-1 only.

The clip at +/-2 bounds any single day's tilt to a factor of ``1 +/- 2k``, so for
k <= 0.5 no weight can be pushed negative. The tilt strength k is an owned
judgement-call parameter - ``k_grid`` exists so the report can show the choice
rather than assert it, and an honest negative result at every k is an acceptable,
explained outcome (the brief says so explicitly).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.portfolios import COST_GRID_BPS, FAMILY_CAPS, BacktestResult, metrics_table

# Default tilt strength. With clip at +/-2 this bounds any tilt factor to
# [0.8, 1.2] - a genuine but modest bet on the signal. See k_grid for the
# sensitivity the report shows alongside this choice.
DEFAULT_K = 0.10

Z_CLIP = 2.0


# --------------------------------------------------------------------------- #
# 1. The tilt itself
# --------------------------------------------------------------------------- #
def tilt_weights(weights: pd.Series, z_row: pd.Series, k: float,
                 cap: float) -> pd.Series:
    """Tilt one rebalance date's target weights by that date's sentiment z-scores.

    Only tickers present in ``z_row`` (the equities) are tilted; anything else
    (crypto) keeps its weight exactly. A ticker with a NaN z (rolling-window
    burn-in, or a long-silent name) gets a neutral factor of 1 rather than being
    dropped - no sentiment means no tilt, not no position.

    After tilting, the equity sleeve is renormalised to its ORIGINAL total weight
    (the tilt redistributes within the sleeve, it does not change the
    equity/crypto split), then re-capped: a tilt can push a name above the fund's
    weight cap, so capped excess is redistributed across the uncapped equity
    names until the cap holds. The redistribution loop terminates because each
    pass strictly shrinks the uncapped budget.
    """
    if k < 0:
        raise ValueError(f"k must be >= 0, got {k}")
    out = weights.astype(float).copy()
    tiltable = weights.index.intersection(z_row.index)
    equity_budget = float(out[tiltable].sum())
    if equity_budget <= 0 or k == 0:
        return out

    z = z_row.reindex(tiltable).astype(float).fillna(0.0)
    factor = 1.0 + k * z.clip(-Z_CLIP, Z_CLIP)
    tilted = out[tiltable] * factor
    tilted *= equity_budget / tilted.sum()

    # Re-cap: clip breaches and hand the excess to the uncapped names, keeping
    # the sleeve total fixed. A few passes suffice; guard against pathologies.
    for _ in range(20):
        over = tilted > cap + 1e-12
        if not over.any():
            break
        excess = float((tilted[over] - cap).sum())
        tilted[over] = cap
        room = tilted[~over]
        if room.empty or room.sum() <= 0:
            break
        tilted[~over] = room + excess * room / room.sum()
    out[tiltable] = tilted
    return out


def apply_sentiment(weights: pd.DataFrame, sentiment_z: pd.DataFrame,
                    k: float = DEFAULT_K, cap: float = 0.10) -> pd.DataFrame:
    """Tilt every rebalance date's weights row. The brief's named entry point.

    ``weights`` is a ``BacktestResult.weights`` frame (rows = rebalance dates);
    ``sentiment_z`` is ``sentiment.sentiment_z(sentiment.fusion_signal(...))`` -
    ALREADY lagged; pass it through untouched.
    """
    z = sentiment_z.reindex(weights.index)
    return pd.DataFrame(
        {d: tilt_weights(weights.loc[d], z.loc[d], k, cap) for d in weights.index}
    ).T[weights.columns]


# --------------------------------------------------------------------------- #
# 2. Fused backtest (same schedule, same cost machinery as the base fund)
# --------------------------------------------------------------------------- #
def fused_backtest(returns: pd.DataFrame, base: BacktestResult,
                   sentiment_z: pd.DataFrame, k: float = DEFAULT_K,
                   cost_grid_bps: tuple[int, ...] = COST_GRID_BPS) -> BacktestResult:
    """Re-run the base fund's out-of-sample history with sentiment-tilted weights.

    Everything except the weights is held fixed - the same rebalance dates, the
    same hold-forward rule, the same entry cost and cost grid - so a before/after
    difference is attributable to the tilt alone, not to a schedule change.
    ``returns`` must be the SAME panel the base fund was backtested on.
    """
    cap = FAMILY_CAPS[base.family]
    tilted = apply_sentiment(base.weights, sentiment_z, k=k, cap=cap)

    reb_dates = list(tilted.index)
    positions = [returns.index.get_loc(d) for d in reb_dates]
    gross = pd.Series(index=returns.index, dtype=float)
    cost_charged = pd.Series(0.0, index=returns.index, dtype=float)
    turnovers: dict[pd.Timestamp, float] = {}
    X = returns.to_numpy(dtype=float)
    previous = None

    for i, (date, start) in enumerate(zip(reb_dates, positions)):
        w = tilted.loc[date].to_numpy(dtype=float)
        turnover = 1.0 if previous is None else float(np.abs(w - previous).sum())
        turnovers[date] = turnover
        cost_charged.iloc[start] = turnover
        previous = w
        end = positions[i + 1] if i + 1 < len(positions) else len(returns)
        gross.iloc[start:end] = X[start:end] @ w

    gross = gross.dropna()
    cost_charged = cost_charged.loc[gross.index]
    net = pd.DataFrame({f"net_{b}bps": gross - cost_charged * (b / 10_000.0)
                        for b in cost_grid_bps}, index=gross.index)

    return BacktestResult(
        fund=f"{base.fund} +sentiment(k={k:g})", method=base.method,
        family=base.family, returns=gross, weights=tilted,
        turnover=pd.Series(turnovers).sort_index(), net_returns=net,
        calendar=base.calendar, solver_ok=base.solver_ok)


# --------------------------------------------------------------------------- #
# 3. Before-vs-after reporting
# --------------------------------------------------------------------------- #
def before_after_table(base: BacktestResult, fused: BacktestResult) -> pd.DataFrame:
    """The brief's required exhibit: base fund vs sentiment-augmented, side by side.

    Rows: base, fused, and a delta row (fused minus base) so the report quotes the
    difference from a saved table rather than hand-computing it in prose.
    """
    tbl = metrics_table([base, fused]).set_index("fund")
    num_cols = [c for c in tbl.columns if tbl[c].dtype.kind in "fi"]
    delta = tbl[num_cols].iloc[1] - tbl[num_cols].iloc[0]
    delta.name = "delta (fused - base)"
    return pd.concat([tbl, delta.to_frame().T])


def k_grid(returns: pd.DataFrame, base: BacktestResult,
           sentiment_z: pd.DataFrame,
           ks: tuple[float, ...] = (0.0, 0.05, 0.10, 0.20, 0.30, 0.50)
           ) -> pd.DataFrame:
    """Before/after headline metrics across tilt strengths.

    ``k = 0`` is a built-in self-check: it must reproduce the base fund exactly
    (its delta row is a wiring test, not a data point). The report shows this
    grid so the chosen k is a documented decision, not a lucky draw - and if the
    tilt hurts at every k, that is the honest result to report.
    """
    from src.portfolios import performance_metrics
    base_m = performance_metrics(base.returns, base.calendar)
    rows = [{"k": "base", "ann_return": base_m["ann_return"],
             "ann_vol": base_m["ann_vol"], "sharpe": base_m["sharpe"],
             "max_drawdown": base_m["max_drawdown"],
             "turnover_per_reb": float(base.turnover.iloc[1:].mean())}]
    for k in ks:
        f = fused_backtest(returns, base, sentiment_z, k=k)
        m = performance_metrics(f.returns, f.calendar)
        rows.append({"k": k, "ann_return": m["ann_return"], "ann_vol": m["ann_vol"],
                     "sharpe": m["sharpe"], "max_drawdown": m["max_drawdown"],
                     "turnover_per_reb": float(f.turnover.iloc[1:].mean())})
    return pd.DataFrame(rows)
