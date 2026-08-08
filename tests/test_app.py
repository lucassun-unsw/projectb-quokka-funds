"""App tests: the whole script runs, and every displayed percentage is scaled.

    python -m pytest tests/test_app.py

The scale test exists because of a real bug. `column_config`'s ``format`` is a
printf string, not a percent directive, so ``"%.1f%%"`` applied to the stored
0.0826 printed "0.1%" rather than "8.3%". Every rate in results/ is a fraction,
so a table that formats one with %% must scale it first - the Compare table, the
holdings weights, the co-crash panel, and the event percentiles all shipped 100x
too small until this was caught. These tests pin the fix down at the value level.
"""
import pathlib
import re
import sys

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

APP = ROOT / "streamlit_app.py"
RESULTS = ROOT / "results"


def run_app():
    """A fresh app instance. Any test that changes a widget needs its own -
    the module fixture is shared, and one test renaming the blend sliders
    silently disarmed another until this was split out."""
    at = AppTest.from_file(str(APP), default_timeout=300)
    at.run()
    return at


@pytest.fixture(scope="module")
def app():
    """Shared instance for read-only assertions. Do not mutate it."""
    return run_app()


def test_app_runs_without_exceptions(app):
    assert not app.exception, [str(e) for e in app.exception]


def test_all_five_tabs_render(app):
    assert len(app.tabs) == 5


def test_no_derived_contrast_message_widgets(app):
    """st.info/success/warning tint themselves from the theme and derive their
    own text contrast. This app lightened those theme colours, so every message
    must draw its own foreground and background instead."""
    assert not app.info and not app.success and not app.warning and not app.error


def test_percent_columns_are_scaled_before_display():
    """A column formatted with %% must hold 0-100, not 0-1."""
    from streamlit_app import as_pct

    met = pd.read_csv(RESULTS / "tables" / "performance_metrics.csv")
    scaled = as_pct(met, "ann_return", "ann_vol", "max_drawdown", "turnover_ann")
    # Combined Min-CVaR earns 8.26% a year: the display value must read 8.26.
    row = scaled.set_index("fund").loc["Combined Min-CVaR"]
    assert row.ann_return == pytest.approx(8.2623, abs=1e-3)
    assert row.ann_vol == pytest.approx(13.3694, abs=1e-3)
    # ...and the source frame must be left untouched.
    assert met.set_index("fund").loc["Combined Min-CVaR", "ann_return"] < 1.0

    cc = as_pct(pd.read_csv(RESULTS / "tables" / "co_crash_panel.csv"), "mean_crash")
    worst = cc["mean_crash"].min()
    assert worst < -1.0, f"crash-day means should read as percent, got {worst}"


def test_holdings_never_exceed_their_family_cap():
    """The holdings bar is scaled to the cap, so the cap has to be the real one."""
    from streamlit_app import UNIVERSE

    hold = pd.read_csv(RESULTS / "tables" / "current_holdings.csv")
    for fund, grp in hold.groupby("fund"):
        family = fund.split(" ", 1)[0]
        cap = 0.25 if family == "Crypto-Only" else 0.10
        assert grp["weight"].max() <= cap + 1e-9, fund
        assert len(grp) <= UNIVERSE[family], fund


def test_blend_of_one_fund_reproduces_that_fund():
    """A single-fund blend is that fund, so its stats must match the published
    metrics exactly - including the annualisation calendar. Using 252 for a
    crypto-only blend understated its volatility by roughly a fifth."""
    app = run_app()
    fund = "Crypto-Only Min-Variance"
    blend = next(m for m in app.multiselect if m.label == "Funds to blend")
    blend.set_value([fund]).run()
    assert not app.exception, [str(e) for e in app.exception]

    met = pd.read_csv(RESULTS / "tables" / "performance_metrics.csv").set_index("fund")
    expected_vol = f"{met.loc[fund, 'ann_vol']:.2%}"
    expected_sharpe = f"{met.loc[fund, 'sharpe']:.4f}"
    rendered = " ".join(m.value for m in app.markdown)
    assert expected_vol in rendered, f"expected {expected_vol} in the blend panel"
    assert expected_sharpe in rendered
    assert "365-day" in rendered


def test_every_fund_renders_a_fact_sheet():
    """All twelve, not just the default - the families differ in calendar,
    universe size and weight cap, so one working fund proves little."""
    app = run_app()
    picker = app.selectbox[0]
    for fund in picker.options:
        picker.set_value(fund).run()
        assert not app.exception, (fund, [str(e) for e in app.exception])


def test_zero_weights_do_not_print_a_nan_sharpe():
    """Every slider at zero is reachable: the sliders bottom out at 0. It used
    to divide a 0% return by 0% volatility and print Sharpe as "nan".

    Builds its own AppTest rather than sharing the module fixture - another test
    changes which funds are blended, which renames these sliders.
    """
    app = run_app()
    blend = next(m for m in app.multiselect if m.label == "Funds to blend")
    for s in app.slider:
        if s.label in blend.value:
            s.set_value(0)
    app.run()
    assert not app.exception
    rendered = " ".join(m.value for m in app.markdown)
    # Match a rendered *cell value*, not the letters "nan" inside a CSS word.
    bad = re.findall(r">\s*[-+]?(?:nan|inf)\s*<", rendered, flags=re.I)
    assert not bad, bad
    assert "weight is at zero" in rendered


def test_bootstrap_caption_matches_the_bootstrap_csv(app):
    """The crash-day range is read from co_crash_bootstrap.csv, not typed into
    the sentence - a hand-written range goes stale on the next pipeline run,
    and the one that used to sit here was narrower than the file beside it."""
    boot = pd.read_csv(RESULTS / "tables" / "co_crash_bootstrap.csv")
    sep = boot[boot["distinguishable"]]
    lo, hi = 100 * sep["gap"].abs().min(), 100 * sep["gap"].abs().max()
    caption = next(c.value for c in app.caption if "Paired bootstrap" in c.value)
    assert f"{lo:.2f}–{hi:.2f}pp" in caption, caption
    assert str(len(boot)) in caption


def test_every_fund_has_all_six_fact_sheet_elements():
    """PROJECT_BRIEF, Station 3: "Fact sheet per fund (one per (family, method)
    fund): growth of $1, annualised return, annualised volatility, Sharpe ratio,
    maximum drawdown, and current holdings."

    All six must be readable from a saved CSV for all twelve funds, or the report
    ends up hand-computing them. `growth_of_one` was missing until Phase 8c - it
    existed only inside the app, which recomputes it live from daily returns.
    """
    met = pd.read_csv(RESULTS / "tables" / "performance_metrics.csv")
    hold = pd.read_csv(RESULTS / "tables" / "current_holdings.csv")

    for col in ["growth_of_one", "ann_return", "ann_vol", "sharpe", "max_drawdown"]:
        assert col in met.columns, f"fact-sheet element missing from CSV: {col}"
        assert met[col].notna().all(), col
    assert len(met) == 12
    # ...and current holdings for every fund, not just the recommended one.
    assert set(hold["fund"]) == set(met["fund"]), "holdings missing for some funds"

    # growth_of_one must be the terminal cumulative product, not something else.
    rets = pd.read_csv(RESULTS / "data" / "fund_returns.csv", parse_dates=["date"])
    expected = (rets.sort_values("date").groupby("fund")["ret"]
                .apply(lambda s: (1.0 + s).prod()))
    got = met.set_index("fund")["growth_of_one"]
    pd.testing.assert_series_equal(got.sort_index(), expected.sort_index(),
                                   check_names=False, atol=1e-10)


def test_fund_colour_and_dash_pair_is_unique_per_fund():
    """Colour carries the method and the dash carries the family; together they
    have to identify all twelve funds or two lines plot identically."""
    from streamlit_app import color_for, style_for

    funds = pd.read_csv(RESULTS / "tables" / "performance_metrics.csv")["fund"]
    keys = {(color_for(f), style_for(f)) for f in funds}
    assert len(keys) == len(funds)


def test_management_fee_accrues_on_the_funds_own_calendar():
    """The fee is a rate per YEAR, so it must be divided by the calendar the
    fund actually trades. Charging a 365-day crypto fund at 1/252 per day
    overcharges it by ~45%, and the error is invisible in a single number."""
    from streamlit_app import MGMT_FEE, after_fee

    daily = pd.Series([0.0] * 252)
    charged = daily.iloc[0] - after_fee(daily, 252).iloc[0]
    assert charged == pytest.approx(MGMT_FEE / 252)
    # A full year of accrual costs one fee, on either calendar.
    for cal in (252, 365):
        year = pd.Series([0.0] * cal)
        total = 1.0 - (1.0 + after_fee(year, cal)).prod()
        assert total == pytest.approx(MGMT_FEE, abs=1e-5), cal


def test_after_fee_is_strictly_worse_than_gross_for_every_fund():
    """A displayed 'after fee' figure that equals the gross one means the fee
    was never applied - the exact failure a screenshot would not reveal."""
    from streamlit_app import after_fee

    rets = pd.read_csv(RESULTS / "data" / "fund_returns.csv", parse_dates=["date"])
    met = pd.read_csv(RESULTS / "tables" / "performance_metrics.csv").set_index("fund")
    for fund, grp in rets.groupby("fund"):
        s = grp.sort_values("date")["ret"]
        cal = int(met.loc[fund, "calendar"])
        gross = (1.0 + s).prod()
        after = (1.0 + after_fee(s, cal)).prod()
        assert after < gross, f"fee not applied for {fund}"


def test_app_states_the_fee_and_the_market_gap():
    """Both are brief requirements: the business earns a management fee, and the
    app must name the gap in the market it fills."""
    src = (ROOT / "streamlit_app.py").read_text()
    assert "MGMT_FEE = 0.0035" in src
    assert "management fee" in src.lower()
    assert "gap we fill" in src.lower(), "value proposition not stated in the app"
