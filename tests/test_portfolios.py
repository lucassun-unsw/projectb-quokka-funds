"""Tests for the risk estimate and the covariance-estimator switch.

    python -m pytest tests/test_portfolios.py

Section 1 of the report claims EWMA at span 252 beats the alternatives on
realised volatility, and `results/tables/parameter_study.csv` is the evidence.
That evidence is only worth anything if the estimator switch actually changes
what the optimiser sees - an inert switch would produce four identical rows that
still *look* like a comparison. These tests exist so that failure cannot happen
silently. They use synthetic data so they need no network and no data files.
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import portfolios as pf


def heteroskedastic_returns(seed: int = 7) -> np.ndarray:
    """800 days where the second half is three times as volatile as the first.

    A regime shift is what separates a decaying estimator from a flat one: EWMA
    weights the recent, noisier half more heavily and must report a higher
    variance than the full-window average. On homoskedastic data the two would
    agree and the test would pass vacuously.
    """
    rng = np.random.default_rng(seed)
    return np.vstack([rng.normal(0.0, 0.01, size=(400, 8)),
                      rng.normal(0.0, 0.03, size=(400, 8))])


def test_static_matches_numpy():
    """The static benchmark is the textbook biased sample covariance, exactly."""
    X = heteroskedastic_returns()
    assert np.allclose(pf.sample_covariance(X),
                       np.cov(X, rowvar=False, bias=True), atol=1e-12)


def test_ewma_at_huge_span_becomes_static():
    """Turning the decay off must recover the static estimator.

    This is what licenses reading the parameter study as an isolated test of
    *weighting*: the two estimators differ only in how they weight observations,
    not in centring or normalisation convention.
    """
    X = heteroskedastic_returns()
    assert np.allclose(pf.ewma_covariance(X, span=10 ** 9),
                       pf.sample_covariance(X), atol=1e-6)


def test_ewma_sees_more_risk_after_a_volatility_jump():
    """Direction check, not just difference: EWMA must read HIGHER variance.

    A switch that changed the number in the wrong direction would still make the
    parameter study's rows differ, so difference alone is not evidence.
    """
    X = heteroskedastic_returns()
    assert pf.ewma_covariance(X, span=252)[0, 0] > pf.sample_covariance(X)[0, 0]


def test_estimator_switch_changes_the_weights():
    """The switch must reach the optimiser, not just the covariance function."""
    X = heteroskedastic_returns()
    w_ewma, _ = pf.optimal_weights(X, "min_variance", 0.3, "ewma", 252)
    w_static, _ = pf.optimal_weights(X, "min_variance", 0.3, "static", 252)
    w_short, _ = pf.optimal_weights(X, "min_variance", 0.3, "ewma", 32)
    assert np.abs(w_ewma - w_static).max() > 1e-3
    assert np.abs(w_ewma - w_short).max() > 1e-3


def test_defaults_reproduce_the_production_path():
    """Adding the switch must not have moved the 12 funds.

    Passing the locked values explicitly has to be bit-identical to passing
    nothing, or every number already saved in results/ would be in question.
    """
    X = heteroskedastic_returns()
    for method in ("min_variance", "max_sharpe", "risk_parity"):
        w_default, _ = pf.optimal_weights(X, method, 0.3)
        w_explicit, _ = pf.optimal_weights(X, method, 0.3, "ewma", pf.EWMA_SPAN)
        assert np.array_equal(w_default, w_explicit), method


def test_min_cvar_ignores_the_covariance_arguments():
    """Min-CVaR optimises scenarios directly and never forms a covariance.

    Documented as a limit of the parameter study: it speaks for the three
    covariance-based methods only.
    """
    X = heteroskedastic_returns()
    w_a, _ = pf.optimal_weights(X, "min_cvar", 0.3, "static", 32)
    w_b, _ = pf.optimal_weights(X, "min_cvar", 0.3, "ewma", pf.EWMA_SPAN)
    assert np.array_equal(w_a, w_b)


def test_weights_use_only_the_window_given():
    """No look-ahead at the optimiser boundary: appending future rows to the
    panel must not move weights formed from the first `start` rows."""
    X = heteroskedastic_returns()
    start = 500
    future = np.vstack([X, heteroskedastic_returns(seed=99)])
    w_now, _ = pf.optimal_weights(X[:start], "min_variance", 0.3)
    w_with_future, _ = pf.optimal_weights(future[:start], "min_variance", 0.3)
    assert np.array_equal(w_now, w_with_future)


def test_backtest_ignores_the_scrambled_future():
    """The no-look-ahead guarantee, tested end to end on the backtest itself.

    Scramble and inflate every observation from a chosen rebalance onward, re-run,
    and require every weight formed at or before that date to be *bit*-identical -
    while later weights must move, or the test proves nothing.

    Both panels are built from arrays of the same shape by the same constructor on
    purpose. Building one with `pandas .loc` assignment instead changes the frame's
    memory layout, which changes the BLAS reduction order inside `ewma_covariance`,
    which perturbs the covariance in its last bit (~1e-18). Min-variance on this
    data is ill-conditioned enough (condition number ~1e3, a very flat minimum) to
    amplify that into ~1e-4 differences in individual weights while the portfolio
    variance itself moves by ~1e-7 relative. That is floating-point noise, not
    look-ahead - but it will fail an exact comparison, so the layout is held fixed
    and the amplification is recorded as a numerical caveat rather than hidden.
    """
    import pandas as pd

    rng = np.random.default_rng(3)
    n_days, n_assets, cut = 500, 6, 400
    A = rng.normal(0.0, 0.012, size=(n_days, n_assets))
    B = A.copy()
    B[cut:] = rng.permutation(B[cut:]) * 5.0
    idx = pd.bdate_range("2020-01-01", periods=n_days)
    cols = [f"A{i}" for i in range(n_assets)]
    base = pd.DataFrame(A, index=idx, columns=cols)
    scrambled = pd.DataFrame(B, index=idx, columns=cols)
    cut_date = idx[cut]

    for method in pf.METHODS:
        b = pf.oos_backtest(base, method, "Combined", cap=0.5,
                            burn_in=200, step=50, verbose=False)
        s = pf.oos_backtest(scrambled, method, "Combined", cap=0.5,
                            burn_in=200, step=50, verbose=False)
        past = b.weights.index[b.weights.index <= cut_date]
        future = b.weights.index[b.weights.index > cut_date]
        assert np.array_equal(b.weights.loc[past].to_numpy(),
                              s.weights.loc[past].to_numpy()), f"look-ahead in {method}"
        assert (b.weights.loc[future] - s.weights.loc[future]).abs().max().max() > 0, \
            f"{method}: future weights did not move, so the test is vacuous"


def test_crypto_only_annualises_on_a_365_day_calendar():
    """CLAUDE.md rule 2, which had no test until a mutation run exposed that.

    Setting CALENDAR["Crypto-Only"] to 252 left the whole suite green: nothing
    re-runs the pipeline, and the app reads the committed CSV rather than this
    constant. A re-run would then have inflated every Crypto-Only Sharpe by
    sqrt(365/252) = 1.20x with no check going red - the same defect class that was
    caught in the app's allocation blend and fixed there but never pinned here.
    """
    assert pf.CALENDAR["Crypto-Only"] == 365
    assert pf.CALENDAR["Combined"] == pf.CALENDAR["Equity-Only"] == 252

    # And the factor has to reach the metrics, not just sit in the dict.
    import pandas as pd
    r = pd.Series(0.001, index=pd.date_range("2021-01-01", periods=400))
    m252 = pf.performance_metrics(r, pf.CALENDAR["Combined"])
    m365 = pf.performance_metrics(r, pf.CALENDAR["Crypto-Only"])
    assert m252["calendar"] == 252 and m365["calendar"] == 365
    assert m365["ann_return"] > m252["ann_return"]


def test_backtest_carries_its_family_calendar_into_the_metrics_row():
    """A wrong factor must surface as a wrong column, not a silent number."""
    import pandas as pd

    rng = np.random.default_rng(11)
    idx = pd.bdate_range("2020-01-01", periods=400)
    R = pd.DataFrame(rng.normal(0.0, 0.01, size=(400, 8)),
                     index=idx, columns=[f"A{i}" for i in range(8)])
    for family, expected in (("Combined", 252), ("Crypto-Only", 365)):
        res = pf.oos_backtest(R, "min_variance", family, cap=0.3, verbose=False)
        assert res.calendar == expected, family
        row = pf.metrics_table([res]).iloc[0]
        assert row["calendar"] == expected, family


def test_fusion_signal_refuses_a_zero_lag():
    """CLAUDE.md rule 1: sentiment lags >= 1 trading day, enforced inside the
    signal constructor so a forgotten shift cannot become silent look-ahead.

    Untested until a mutation run deleted the guard and all 21 tests still passed.
    Kept here rather than in test_app.py because it needs no app and no network.
    """
    import pandas as pd

    from src import sentiment as sn

    days = pd.DatetimeIndex(pd.bdate_range("2021-01-01", periods=40))
    scored = pd.DataFrame({
        "trading_day": list(days[:20]) * 2,
        "ticker": ["AAA"] * 20 + ["BBB"] * 20,
        "sector": ["Tech"] * 40,
        "compound": np.linspace(-0.9, 0.9, 40),
    })

    for bad in (0, -1):
        try:
            sn.fusion_signal(scored, days, lag=bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"lag={bad} was accepted; that is look-ahead")

    # The default must not merely be nonzero - it must shift by exactly one day.
    signal = sn.fusion_signal(scored, days)
    raw = (sn.ticker_day_score(scored)
             .pivot(index="trading_day", columns="ticker", values="compound")
             .reindex(days).ffill(limit=sn.FFILL_LIMIT).fillna(sn.NEUTRAL_SCORE))
    shared = signal.index.intersection(raw.index)[1:]
    assert np.allclose(signal.loc[shared].to_numpy(),
                       raw.shift(1).loc[shared].to_numpy())


def test_cap_guard_blocks_infeasible_and_degenerate_caps():
    """The crypto cap degeneracy: 10 assets x 10% saturates at exactly 1.00, so
    every method collapses to the same equal-weight fund. It happened once."""
    pf.check_cap_feasible(60, 0.10)
    pf.check_cap_feasible(10, 0.25)
    for n, cap in ((10, 0.10), (5, 0.10)):
        try:
            pf.check_cap_feasible(n, cap)
        except ValueError:
            pass
        else:
            raise AssertionError(f"n={n} cap={cap} should not be allowed")


def test_family_caps_are_feasible_for_the_universe_each_one_serves():
    """Testing the guard is not the same as testing the constants it guards.

    A mutation setting FAMILY_CAPS["Crypto-Only"] back to 0.10 passed the guard
    test above, because that test calls check_cap_feasible with its own numbers.
    Pin the actual caps against the actual universe sizes.
    """
    universe = {"Combined": 60, "Equity-Only": 50, "Crypto-Only": 10}
    for family, n in universe.items():
        pf.check_cap_feasible(n, pf.FAMILY_CAPS[family])   # raises if degenerate
    assert pf.FAMILY_CAPS["Crypto-Only"] == 0.25
    assert pf.FAMILY_CAPS["Combined"] == pf.FAMILY_CAPS["Equity-Only"] == 0.10


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"{name} OK")
