"""Station 3 - fund construction, walk-forward backtest, and downside evaluation.

Four optimisation methods across three asset families, each (family, method) pair
being one named fund. Every parameter here was chosen against the real data before
this module was written; see ``report/OUTLINE.md`` for the evidence behind each.

The rules that are load-bearing, and where they are enforced:

  1. NO LOOK-AHEAD. ``oos_backtest`` forms every weight vector from
     ``returns.iloc[:start]`` - strictly before the rebalance date - and holds it
     until the next rebalance. Verified by a data-scrambling test: replacing all
     observations from the rebalance date onward leaves the weights bit-identical.
  2. CALENDAR. Combined and equity-only funds annualise with 252, a crypto-only
     fund with 365. ``performance_metrics`` takes the factor explicitly and echoes
     it back in a ``calendar`` column, so a wrong factor is visible in the output
     rather than hidden in an assumption.
  3. WEIGHT CAP IS FAMILY-SPECIFIC. 10% for the broad families (the UCITS
     per-issuer convention), but 25% for crypto-only: with p=10 assets a 10% cap
     is exactly saturating (10 x 10% = 1.00), admits a single feasible solution,
     and silently collapses all four methods into the same equal-weight fund.
     That is not hypothetical - it happened, and ``FAMILY_CAPS`` exists so it
     cannot happen again. See ``check_cap_feasible``.
  4. COSTS ARE BUILT IN, NOT BOLTED ON. ``oos_backtest`` accumulates two-way
     turnover at each rebalance and returns net returns across a cost grid.
     Retrofitting this after the fact means re-running everything.

Every function is importable and returns a value; none write to ``results/``
(that is ``scripts/run_part_b.py``'s job).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import optimize

# --------------------------------------------------------------------------- #
# Locked parameters. Each was decided against real data - see report/OUTLINE.md
# --------------------------------------------------------------------------- #
EWMA_SPAN = 252        # lambda = 0.9921, half-life 87 trading days. NOT a window
                       # length: all observations are used, geometrically weighted.
                       # Beat RiskMetrics' lambda=0.94 (span 32) by 1.23pp of
                       # realised vol, and a static covariance in all three OOS years.
CVAR_BETA = 0.95       # Basel's FRTB level (97.5% ES) leaves only 6.3 tail
                       # scenarios at T=252, too thin to estimate. 0.95 leaves 12.6.
BURN_IN = 252          # trading days before the first live rebalance. Unrelated to
                       # EWMA_SPAN despite the shared number - one is a hard cutoff,
                       # the other a decay rate.
REBALANCE_STEP = 21    # ~monthly, the brief's own suggested cadence
RISK_FREE = 0.0        # stated assumption, carried from Part A

FAMILY_CAPS = {"Combined": 0.10, "Equity-Only": 0.10, "Crypto-Only": 0.25}
CALENDAR = {"Combined": 252, "Equity-Only": 252, "Crypto-Only": 365}
COST_GRID_BPS = (0, 10, 20, 50)   # breakeven measured at ~20bps; the grid brackets it
METHODS = ("max_sharpe", "min_variance", "risk_parity", "min_cvar")

# Display names per the locked fund-naming convention (report/OUTLINE.md): each
# (family, method) pair is one named fund - "Combined Max-Sharpe", "Equity-Only
# Risk Parity" - and THIS exact naming is what fund_returns.csv/fund_weights.csv,
# the fact sheets, and the app's fund picker key off. Method slugs stay as the
# internal identifiers; the fund label is the public name.
METHOD_DISPLAY = {"max_sharpe": "Max-Sharpe", "min_variance": "Min-Variance",
                  "risk_parity": "Risk Parity", "min_cvar": "Min-CVaR"}


# --------------------------------------------------------------------------- #
# 1. Risk estimate
# --------------------------------------------------------------------------- #
def ewma_covariance(returns: pd.DataFrame | np.ndarray,
                    span: int = EWMA_SPAN) -> np.ndarray:
    """Exponentially weighted covariance: geometric weights over ALL observations.

    Computed directly rather than via ``pandas.DataFrame.ewm().cov()`` for two
    reasons, both verified: pandas is ~4000x slower here (262ms vs 0.06ms per
    window, and this runs at every rebalance of every fund), and its *default*
    result differs from this one because ``.cov()`` defaults to ``bias=False``.
    This function is exactly equivalent to
    ``df.ewm(span=span, adjust=True).cov(bias=True)`` (max difference 0.000%);
    against ``bias=False`` it differs by the Bessel-style factor
    ``1 / (1 - sum(w^2))``, which at span 252 is 0.40% on the full panel
    (0.48% at T=300). That factor grows as the span shortens - a note that once
    said "6.75%" was measuring a span of roughly 17, not 252.

    Weights decay as ``lambda ** k`` for an observation k days back, with
    ``lambda = (span - 1) / (span + 1)``. At span 252 that is lambda = 0.9921 and
    a half-life of 87 trading days, so a year-old observation still carries ~14%
    of yesterday's weight - the matrix stays better conditioned at 60 assets than
    a short span does. Condition numbers depend on the window, so quote one with
    its window: at the FIRST rebalance window (T=252) it is 850 here against
    4.4e4 at span 30; medians across the 36 Combined windows are 1.4e3 and 3.3e4.
    """
    X = np.asarray(returns, dtype=float)
    lam = (span - 1.0) / (span + 1.0)
    w = lam ** np.arange(len(X) - 1, -1, -1)
    w /= w.sum()
    Xc = X - w @ X
    return (Xc * w[:, None]).T @ Xc


def sample_covariance(returns: pd.DataFrame | np.ndarray) -> np.ndarray:
    """Plain full-window sample covariance - the static benchmark EWMA must beat.

    Every observation carries the same weight, so this is ``ewma_covariance`` with
    the decay switched off. Written with the same centring and the same ``bias=True``
    normalisation so a comparison between the two isolates the *weighting* and not
    an estimator convention. Only used by the parameter study; the funds themselves
    always use the EWMA estimator.
    """
    X = np.asarray(returns, dtype=float)
    w = np.full(len(X), 1.0 / len(X))
    Xc = X - w @ X
    return (Xc * w[:, None]).T @ Xc


def squared_return_autocorr(series: pd.Series,
                            lags: tuple[int, ...] = (1, 5, 10, 21)) -> pd.DataFrame:
    """Autocorrelation of returns, squared returns, and absolute returns.

    The diagnostic that justifies using a time-varying covariance at all: raw
    returns are close to unforecastable while their SIZE is strongly persistent,
    which is volatility clustering. On this data the equity aggregate shows
    ACF(r) = -0.18 but ACF(r^2) = +0.49 at lag 1.
    """
    r = series.dropna()
    return pd.DataFrame([{
        "lag": k,
        "acf_return": r.autocorr(k),
        "acf_squared": (r ** 2).autocorr(k),
        "acf_absolute": r.abs().autocorr(k),
    } for k in lags])


# --------------------------------------------------------------------------- #
# 2. The four optimisers
# --------------------------------------------------------------------------- #
def _solve_long_only(objective, n_assets: int, cap: float,
                     lower: float = 0.0) -> tuple[np.ndarray, bool]:
    """Shared SLSQP call: long-only, capped, fully invested.

    Returns ``(weights, converged)`` - the flag is what ``oos_backtest`` ANDs
    across every rebalance to report "all 520 solves converged", so it has to
    travel with the weights rather than be checked here and discarded.

    ``lower`` is nonzero only for risk parity, whose objective divides by each
    asset's own risk contribution and is undefined at a zero weight.
    """
    res = optimize.minimize(
        objective, np.full(n_assets, 1.0 / n_assets), method="SLSQP",
        bounds=[(lower, cap)] * n_assets,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0}],
        options={"maxiter": 1000, "ftol": 1e-14},
    )
    return np.clip(res.x, 0.0, None), bool(res.success)


def min_variance(cov: np.ndarray, cap: float) -> tuple[np.ndarray, bool]:
    """Global minimum-variance portfolio, long-only and capped."""
    return _solve_long_only(lambda w: w @ cov @ w, len(cov), cap)


def max_sharpe(cov: np.ndarray, mean: np.ndarray, cap: float) -> tuple[np.ndarray, bool]:
    """Mean-variance tangency portfolio with ``rf = 0``, long-only and capped.

    Maximises ``w'mu / sqrt(w'Sigma w)``. With rf = 0 the Sharpe ratio is just the
    return-to-volatility ratio, so no excess-return adjustment is needed - the
    assumption is stated in the report rather than buried here.
    """
    def neg_sharpe(w):
        vol = np.sqrt(w @ cov @ w)
        return -(w @ mean) / vol if vol > 0 else 0.0
    return _solve_long_only(neg_sharpe, len(cov), cap)


def risk_parity(cov: np.ndarray, cap: float) -> tuple[np.ndarray, bool]:
    """Equal-risk-contribution portfolio: every asset contributes the same risk.

    Minimises the dispersion of risk contributions ``w_i * (Sigma w)_i / sigma_p``
    around their equal-weight target. Unlike the other three this holds nearly the
    whole universe by construction, which is a property of the method rather than
    a bug - it is worth saying so in the report, since the fact sheet will look
    very different from the other funds'.
    """
    n = len(cov)

    def dispersion(w):
        vol = np.sqrt(w @ cov @ w)
        contrib = w * (cov @ w) / vol
        return float(((contrib - vol / n) ** 2).sum())

    return _solve_long_only(dispersion, n, cap, lower=1e-6)


def min_cvar(returns: np.ndarray, cap: float,
             beta: float = CVAR_BETA) -> tuple[np.ndarray, bool]:
    """Rockafellar-Uryasev minimum-CVaR portfolio, solved as a linear program.

    CVaR at level beta is the mean loss on the worst ``1 - beta`` fraction of
    scenarios. Rockafellar and Uryasev's result is that minimising it over
    portfolio weights is a *linear* program in ``(w, alpha, u)``, where alpha is
    the VaR level and ``u_t`` are per-scenario shortfalls:

        minimise   alpha + 1/(T(1-beta)) * sum_t u_t
        subject to u_t >= -x_t'w - alpha,  u_t >= 0,  sum w = 1,  0 <= w <= cap

    This is a genuine tail objective, not a variance proxy - the distinction
    matters because the whole motivation is Part A's finding that variance-based
    risk understates joint downside.

    Note the LP returns a *vertex* solution, so it is naturally sparse: uncapped
    it held 4 of 60 assets at 43% max weight, and 98% of a single coin in the
    crypto-only universe. The cap is what makes it a plausible retail product.
    """
    X = np.asarray(returns, dtype=float)
    T, p = X.shape
    n = p + 1 + T                                    # [weights, alpha, shortfalls]

    c = np.zeros(n)
    c[p] = 1.0
    c[p + 1:] = 1.0 / (T * (1.0 - beta))

    # -X w - alpha - u <= 0  is  u >= loss - alpha  with loss = -Xw
    A_ub = np.hstack([-X, -np.ones((T, 1)), -np.eye(T)])
    A_eq = np.zeros((1, n))
    A_eq[0, :p] = 1.0

    res = optimize.linprog(
        c, A_ub=A_ub, b_ub=np.zeros(T), A_eq=A_eq, b_eq=np.array([1.0]),
        bounds=[(0.0, cap)] * p + [(None, None)] + [(0.0, None)] * T,
        method="highs",
    )
    return np.clip(res.x[:p], 0.0, None), bool(res.success)


def optimal_weights(window: np.ndarray, method: str, cap: float,
                    cov_estimator: str = "ewma",
                    cov_span: int = EWMA_SPAN) -> tuple[np.ndarray, bool]:
    """Dispatch to one optimiser using only the returns in ``window``.

    ``window`` must already exclude the rebalance date itself - this function has
    no way to check that, so the no-look-ahead guarantee lives in the caller.

    ``cov_estimator``/``cov_span`` exist so the parameter study can re-run a fund
    under a different risk estimate. The defaults are the locked choice (EWMA at
    span 252), so every production call is unaffected.
    """
    if method == "min_cvar":
        return min_cvar(window, cap)
    cov = (sample_covariance(window) if cov_estimator == "static"
           else ewma_covariance(window, span=cov_span))
    if method == "min_variance":
        return min_variance(cov, cap)
    if method == "max_sharpe":
        return max_sharpe(cov, window.mean(axis=0), cap)
    if method == "risk_parity":
        return risk_parity(cov, cap)
    raise ValueError(f"unknown method {method!r}; expected one of {METHODS}")


def check_cap_feasible(n_assets: int, cap: float) -> None:
    """Raise if the cap cannot be satisfied, or can be satisfied only one way.

    ``n_assets * cap`` must exceed 1. At exactly 1 every asset is pinned to the
    cap and all methods return the same equal-weight vector - which is how four
    'different' crypto-only funds once came out with identical fact sheets.
    """
    budget = n_assets * cap
    if budget < 1.0 - 1e-12:
        raise ValueError(
            f"infeasible: {n_assets} assets at a {cap:.0%} cap can hold at most "
            f"{budget:.2f} of the portfolio; weights cannot sum to 1")
    if abs(budget - 1.0) < 1e-9:
        raise ValueError(
            f"degenerate: {n_assets} assets at a {cap:.0%} cap saturates exactly "
            f"(n*cap = 1.00), so equal weight is the ONLY feasible portfolio and "
            f"every method collapses to the same fund. Use a larger cap.")


# --------------------------------------------------------------------------- #
# 3. Walk-forward out-of-sample backtest
# --------------------------------------------------------------------------- #
@dataclass
class BacktestResult:
    """One fund's out-of-sample history. All series share the same date index."""
    fund: str
    method: str
    family: str
    returns: pd.Series            # gross daily OOS returns
    weights: pd.DataFrame         # target weights, one row per rebalance date
    turnover: pd.Series           # two-way turnover at each rebalance
    net_returns: pd.DataFrame     # daily returns net of cost, one column per bps
    calendar: int                 # 252 or 365, carried so it cannot be re-guessed
    solver_ok: bool

    def growth_of_one(self, net_bps: int | None = None) -> pd.Series:
        """Cumulative growth of $1. ``net_bps=None`` uses the gross series."""
        r = self.returns if net_bps is None else self.net_returns[f"net_{net_bps}bps"]
        return (1.0 + r).cumprod()

    def drawdown(self) -> pd.Series:
        """Running drawdown from the gross growth-of-$1 peak (<= 0 everywhere)."""
        g = self.growth_of_one()
        return g / g.cummax() - 1.0

    def latest_holdings(self, threshold: float = 5e-3) -> pd.Series:
        """Current target weights from the most recent rebalance, held names only.

        The fact sheet's 'current holdings' line. Distinct from the weights-over-
        time figure, which uses the whole ``weights`` frame - both are required.
        """
        last = self.weights.iloc[-1]
        return last[last > threshold].sort_values(ascending=False)


def oos_backtest(returns: pd.DataFrame, method: str, family: str,
                 cap: float | None = None, burn_in: int = BURN_IN,
                 step: int = REBALANCE_STEP,
                 cost_grid_bps: tuple[int, ...] = COST_GRID_BPS,
                 cov_estimator: str = "ewma", cov_span: int = EWMA_SPAN,
                 verbose: bool = True) -> BacktestResult:
    """Walk-forward backtest with an expanding estimation window.

    At each rebalance date the weights are formed from ``returns.iloc[:start]``
    only - every observation strictly before that date, none from it or after -
    and held for the next ``step`` trading days. The first live rebalance is at
    index ``burn_in``, so the out-of-sample period starts after the estimation
    window rather than at the first date in the data.

    Transaction costs are charged on two-way turnover at each rebalance, once, on
    the rebalance day. The first rebalance is charged as a full purchase (turnover
    1.0) since the fund starts from cash - ignoring it would flatter every fund by
    its entry cost.

    ``returns`` must have no missing values; drop or fill them before calling. For
    the combined family that means dropping the leading date on which only crypto
    trades, which otherwise shifts the first live rebalance by two trading days.
    """
    if returns.isna().any().any():
        raise ValueError("returns contains NaN; clean the panel before backtesting")
    cap = FAMILY_CAPS[family] if cap is None else cap
    check_cap_feasible(returns.shape[1], cap)
    if len(returns) <= burn_in:
        raise ValueError(f"need more than {burn_in} rows, got {len(returns)}")

    X = returns.to_numpy(dtype=float)
    starts = list(range(burn_in, len(returns), step))

    gross = pd.Series(index=returns.index, dtype=float)
    cost_charged = pd.Series(0.0, index=returns.index, dtype=float)
    weight_rows: dict[pd.Timestamp, pd.Series] = {}
    turnovers: dict[pd.Timestamp, float] = {}
    previous, all_ok = None, True

    for i, start in enumerate(starts):
        w, ok = optimal_weights(X[:start], method, cap, cov_estimator, cov_span)
        all_ok &= ok
        date = returns.index[start]
        weight_rows[date] = pd.Series(w, index=returns.columns)

        # Entering from cash costs a full one-way purchase; later rebalances cost
        # the two-way distance from the weights actually held.
        turnover = 1.0 if previous is None else float(np.abs(w - previous).sum())
        turnovers[date] = turnover
        cost_charged.iloc[start] = turnover
        previous = w

        end = starts[i + 1] if i + 1 < len(starts) else len(returns)
        gross.iloc[start:end] = X[start:end] @ w

    gross = gross.dropna()
    cost_charged = cost_charged.loc[gross.index]
    net = pd.DataFrame({f"net_{b}bps": gross - cost_charged * (b / 10_000.0)
                        for b in cost_grid_bps}, index=gross.index)

    weights = pd.DataFrame(weight_rows).T.sort_index()
    turnover = pd.Series(turnovers).sort_index()
    fund = f"{family} {METHOD_DISPLAY[method]}"

    if verbose:
        print(f"  {fund:<28} first live rebalance {gross.index[0].date()}  "
              f"{len(starts):>3} rebalances  {len(gross):>4} OOS days  "
              f"turnover {turnover.iloc[1:].mean():.1%}/reb"
              f"{'' if all_ok else '   [SOLVER WARNING]'}")

    return BacktestResult(fund=fund, method=method, family=family, returns=gross,
                          weights=weights, turnover=turnover, net_returns=net,
                          calendar=CALENDAR[family], solver_ok=all_ok)


# --------------------------------------------------------------------------- #
# 4. Performance metrics
# --------------------------------------------------------------------------- #
def performance_metrics(daily_returns: pd.Series, periods_per_year: int,
                        risk_free: float = RISK_FREE) -> dict:
    """Growth of $1, annualised return, volatility, Sharpe, and maximum drawdown.

    ``periods_per_year`` is passed in and echoed back rather than inferred, so a
    252-vs-365 mistake shows up as a wrong column in the output instead of a
    silent error. Sharpe uses ``rf = 0`` by default (stated in the report).

    ``growth_of_one`` is the terminal value of $1 invested at the first
    out-of-sample day. The brief requires it in every fund's fact sheet, and the
    cumulative product is already computed here for the drawdown - so it is
    returned rather than left to be re-derived by hand downstream, which is the
    mistake this project has made before.
    """
    r = daily_returns.dropna()
    ann_return = r.mean() * periods_per_year
    ann_vol = r.std() * np.sqrt(periods_per_year)
    growth = (1.0 + r).cumprod()
    return {
        "ann_return": float(ann_return),
        "ann_vol": float(ann_vol),
        "sharpe": float((ann_return - risk_free) / ann_vol) if ann_vol else np.nan,
        "max_drawdown": float((growth / growth.cummax() - 1.0).min()),
        "growth_of_one": float(growth.iloc[-1]) if len(growth) else np.nan,
        "calendar": periods_per_year,
        "n_days": len(r),
    }


def metrics_table(results: list[BacktestResult],
                  cost_grid_bps: tuple[int, ...] = COST_GRID_BPS) -> pd.DataFrame:
    """One row per fund: gross metrics plus net-of-cost return at each cost level.

    The net columns are what turn 'zero transaction costs' from a bare assumption
    into a testable claim - if the Sharpe ranking reorders as costs rise, that is
    a result worth reporting rather than a caveat.
    """
    rows = []
    for res in results:
        row = {"fund": res.fund, "family": res.family, "method": res.method,
               **performance_metrics(res.returns, res.calendar)}
        row["turnover_ann"] = float(res.turnover.iloc[1:].mean()
                                    * (res.calendar / REBALANCE_STEP))
        for b in cost_grid_bps:
            m = performance_metrics(res.net_returns[f"net_{b}bps"], res.calendar)
            row[f"ann_return_{b}bps"] = m["ann_return"]
            row[f"sharpe_{b}bps"] = m["sharpe"]
        rows.append(row)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# 5. Co-crash stress test (the evaluation innovation)
# --------------------------------------------------------------------------- #
def co_crash_returns(fund_returns: pd.Series,
                     crash_dates: pd.Index) -> dict:
    """A fund's behaviour on flagged joint-crash days against every other day.

    ``crash_dates`` comes from ``dependence.joint_crash_dates`` - days on which the
    equity AND crypto aggregates were both in their own worst q%. Note this is a
    JOINT threshold on two other series, used to select dates; it is a different
    object from ``CVAR_BETA``, which is a univariate level applied to the fund's
    own losses inside the optimiser. Because the two are independent, a fund doing
    well here is not the optimiser marking its own homework.
    """
    r = fund_returns.dropna()
    hit = r.index.intersection(crash_dates)
    normal = r.drop(hit)
    return {
        "n_crash_days": len(hit),
        "mean_crash": float(r.loc[hit].mean()) if len(hit) else np.nan,
        "worst_crash": float(r.loc[hit].min()) if len(hit) else np.nan,
        "mean_normal": float(normal.mean()),
        "gap": float(r.loc[hit].mean() - normal.mean()) if len(hit) else np.nan,
    }


def co_crash_bootstrap(fund_a: pd.Series, fund_b: pd.Series,
                       crash_dates: pd.Index, n_boot: int = 2000,
                       seed: int = 20260729) -> dict:
    """Paired bootstrap of the crash-day gap between two funds.

    With only 9 (q=5%) or 22 (q=10%) out-of-sample crash days, every number in the
    co-crash panel is a point estimate. This resamples the crash DATES with
    replacement and recomputes the mean gap, so the report can say whether a
    difference between funds is distinguishable from sampling noise.

    The resampling is PAIRED - both funds are evaluated on the same redrawn dates
    each draw - because the funds are highly correlated day to day, which makes
    the paired comparison far more sensitive than two separate intervals.

    Only the MEAN is bootstrapped. Do not use this on the worst single day: the
    bootstrap is not valid for extreme order statistics, since resampling can never
    produce a value below the observed minimum, so the interval's upper bound is
    just the point estimate.
    """
    shared = fund_a.index.intersection(fund_b.index).intersection(crash_dates)
    a = fund_a.loc[shared].to_numpy(dtype=float)
    b = fund_b.loc[shared].to_numpy(dtype=float)
    n = len(shared)
    if n == 0:
        raise ValueError("no overlapping crash dates between the two funds")

    diff = a - b
    idx = np.random.default_rng(seed).integers(0, n, size=(n_boot, n))
    draws = diff[idx].mean(axis=1)
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return {
        "n_crash_days": n,
        "gap": float(diff.mean()),
        "ci_low": float(lo),
        "ci_high": float(hi),
        "prob_gap_positive": float((draws > 0).mean()),
        # "distinguishable" = the interval excludes zero, i.e. the sign of the gap
        # survives resampling. A False here is a real finding, not a failed test.
        "distinguishable": bool(lo > 0 or hi < 0),
    }


def co_crash_panel(results: list[BacktestResult], crash_dates: pd.Index,
                   label: str) -> pd.DataFrame:
    """The co-crash table across funds, for one threshold. ``label`` e.g. 'q=10%'."""
    return pd.DataFrame([
        {"fund": r.fund, "threshold": label, **co_crash_returns(r.returns, crash_dates)}
        for r in results
    ])
