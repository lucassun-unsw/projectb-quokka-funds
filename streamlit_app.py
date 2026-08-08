"""Quokka - systematic multi-asset funds with news-sentiment analytics.

Station 4 app: compare the 12 funds, open a fact sheet, set an allocation, read
the sector sentiment analytics. The investor journey the brief names, in that
order, one tab each.

Look and feel: a dark product surface (src/app_theme.py + .streamlit/config.toml),
deliberately different from the cream Financial-Times style the printed report
exhibits use. A retail investing product reads like a trading terminal, not like
a newspaper page, and the app draws its own charts live from results/ - so this
choice cannot alter a single report exhibit.

Deployment rules enforced by construction:
  - Reads ONLY precomputed artifacts from results/ (written by
    scripts/run_part_b.py) plus the hosted price data via src/data_access.
  - Never imports the text-scoring or optimisation stack and never recomputes a
    backtest. The only maths here is display arithmetic on precomputed daily
    returns (cumprod for growth of $1, running-max for drawdown, weighted sums
    for the allocation blend).

Run locally:   streamlit run streamlit_app.py
Deploy:        public GitHub repo -> share.streamlit.io, entrypoint streamlit_app.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from src.app_theme import (
    ACCENT,
    AMBER,
    BLEND,
    CSS,
    FAMILY_STYLES,
    GREEN,
    METHOD_COLORS,
    ON_ACCENT,
    R_MD,
    R_SM,
    RED,
    SURFACE,
    TEAL,
    TEXT,
    TEXT_DIM,
    TEXT_MUTED,
    TRACK_TITLE,
    app_fig,
    note,
    quote_header,
    stat_grid,
    status_banner,
)

ROOT = pathlib.Path(__file__).resolve().parent
RESULTS = ROOT / "results"
RECOMMENDED = "Combined Min-CVaR"
AUTHOR = "Lucas Sun"
ZID = "z5594806"

# How many assets each family's optimiser actually chooses from. "16 of 60" is
# only right for Combined - an Equity-Only fund picks from 50 and a Crypto-Only
# fund from 10, and quoting 60 there understates how concentrated it is.
UNIVERSE = {"Combined": 60, "Equity-Only": 50, "Crypto-Only": 10}

# The business model. The brief's product is a fund platform that earns a
# management fee, so the fee has to be visible the way a real fact sheet shows
# it - iShares puts the MER in Key Facts at the top, not in a footnote.
#
# 0.35%/yr is the judgement call: mid-range for a rules-based multi-asset
# product, above a broad-index tracker (~0.20%) because a 21-day rebalance over
# a 60-asset universe with a crypto sleeve costs more to run, and below the
# ~0.50% an active crypto mandate charges.
#
# It is charged in DISPLAY only, deliberately. Deducting it inside
# `oos_backtest` would change every number in results/, and the fee is a
# platform charge on the investor rather than a cost the strategy incurs - the
# gross series is still the right object to compare strategies on. Every net
# figure is therefore labelled "net of fee" wherever it appears, and the gross
# one is shown beside it rather than replaced.
MGMT_FEE = 0.0035

# Accrued on the same calendar the fund annualises on, so a crypto-only fund
# (365 trading days) is not charged 252/365ths of its fee.
def after_fee(daily: pd.Series, calendar: int) -> pd.Series:
    """Daily returns with the management fee accrued pro rata."""
    return daily - MGMT_FEE / calendar

# `initial_sidebar_state` stays "auto": expanded on a desktop, collapsed on a
# phone. Forcing "expanded" looked right on a laptop and made the app unusable
# on a narrow screen - below ~768px Streamlit overlays the sidebar instead of
# pushing the page across, so it covered the tab strip and nothing was reachable.
st.set_page_config(page_title="Quokka Funds", page_icon="🦘", layout="wide",
                   initial_sidebar_state="auto")
st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Precomputed artifacts (the app's only inputs besides the hosted prices)
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def load_results() -> dict:
    out = {
        "returns": pd.read_csv(RESULTS / "data" / "fund_returns.csv",
                               parse_dates=["date"]),
        "weights": pd.read_csv(RESULTS / "data" / "fund_weights.csv",
                               parse_dates=["date"]),
        "index": pd.read_csv(RESULTS / "data" / "sector_sentiment_index.csv",
                             parse_dates=["trading_day"]),
        "metrics": pd.read_csv(RESULTS / "tables" / "performance_metrics.csv"),
        "holdings": pd.read_csv(RESULTS / "tables" / "current_holdings.csv",
                                parse_dates=["rebalance_date"]),
        "co_crash": pd.read_csv(RESULTS / "tables" / "co_crash_panel.csv"),
        "boot": pd.read_csv(RESULTS / "tables" / "co_crash_bootstrap.csv"),
        "fusion": pd.read_csv(RESULTS / "tables" / "fusion_before_after.csv"),
        "events": pd.read_csv(RESULTS / "tables" / "sentiment_event_validation.csv"),
        "coverage": pd.read_csv(RESULTS / "tables" / "sentiment_coverage.csv"),
    }
    out["funds"] = list(out["metrics"]["fund"])
    return out


def growth_of_one(daily: pd.Series) -> pd.Series:
    return (1.0 + daily).cumprod()


def drawdown(daily: pd.Series) -> pd.Series:
    g = growth_of_one(daily)
    return g / g.cummax() - 1.0


def fund_series(returns: pd.DataFrame, fund: str) -> pd.Series:
    return returns[returns["fund"] == fund].set_index("date")["ret"].sort_index()


def method_of(fund: str) -> str:
    return fund.split(" ", 1)[1] if " " in fund else fund


def family_of(fund: str) -> str:
    return fund.split(" ", 1)[0]


def color_for(fund: str):
    return METHOD_COLORS.get(method_of(fund), TEAL)


def style_for(fund: str) -> str:
    return FAMILY_STYLES.get(family_of(fund), "-")


def as_pct(frame: pd.DataFrame, *cols: str) -> pd.DataFrame:
    """Scale fraction columns to 0-100 for display.

    `column_config`'s format string is printf, not a percent directive: given the
    stored 0.0826, ``"%.1f%%"`` prints "0.1%", not "8.3%". Every rate in results/
    is stored as a fraction, so the scaling has to happen here - once, on a copy,
    right before the table is drawn.
    """
    out = frame.copy()
    for col in cols:
        out[col] = 100.0 * out[col]
    return out


# Header and body rows both measure 28px at this theme's 13px base font, so a
# table sized to its own row count ends exactly on its last row. Left to itself
# Streamlit caps the box around ten rows, which clipped the twelve-fund table
# mid-row; a fixed guess in the other direction leaves empty grid below the data.
ROW_PX = 28


def grid_height(n_rows: int) -> int:
    """Exact pixel height for an n-row dataframe: no clipping, no blank rows."""
    return ROW_PX * (n_rows + 1) + 3


def show(fig):
    """Render and free a matplotlib figure - the app draws many per rerun."""
    st.pyplot(fig, width="stretch")
    plt.close(fig)


def panel(title: str, subtitle: str = "") -> None:
    """A section heading inside a tab, so long tabs stay scannable."""
    sub = (f"<div style='color:{TEXT_MUTED};font-size:0.86rem;margin-top:-2px'>"
           f"{subtitle}</div>") if subtitle else ""
    st.markdown(
        f"<div style='margin:6px 0 10px'>"
        f"<span style='font-size:1.05rem;font-weight:700'>{title}</span>{sub}</div>",
        unsafe_allow_html=True)


R = load_results()
MET = R["metrics"].set_index("fund")
REC = MET.loc[RECOMMENDED]


# --------------------------------------------------------------------------- #
# Sidebar - identity, the one global control, and provenance
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:9px'>"
        f"<div style='width:26px;height:26px;border-radius:{R_SM};"
        f"background:{ACCENT};"
        f"color:{ON_ACCENT};font-weight:700;font-size:15px;display:flex;"
        f"align-items:center;justify-content:center'>Q</div>"
        f"<div style='font-size:1.2rem;font-weight:600;"
        f"letter-spacing:{TRACK_TITLE}'>"
        f"QUOKKA</div></div>"
        f"<div style='color:{TEXT_MUTED};font-size:0.8rem;margin:4px 0 2px'>"
        f"Systematic multi-asset funds</div>"
        # Byline under the wordmark. It does two jobs in one line: it attributes
        # the app (the marker opens a bare URL, with no report attached to it),
        # and it says "coursework" on a PUBLIC page that otherwise reads as a
        # live retail product recommending a fund to buy.
        f"<div style='color:{TEXT_DIM};font-size:0.72rem;margin:0 0 9px;"
        f"letter-spacing:.01em'>{AUTHOR} · {ZID}<br>"
        f"UNSW FINS3645</div>"
        f"<div style='color:{TEXT_MUTED};font-size:0.78rem;line-height:1.55'>"
        f"Almost nobody sells one fund that holds equities and crypto together. "
        f"An investor who wants both buys two products, sizes the crypto sleeve "
        f"alone, and never sees how the two behave when they fall on the same "
        f"day. <b style='color:{TEXT}'>That is the gap we fill.</b><br><br>"
        f"We build rules-based funds from a fixed universe of 50 US large-caps "
        f"and 10 cryptocurrencies, and we judge them on the days that actually "
        f"hurt, not just on average. We charge "
        f"<b style='color:{TEXT}'>{MGMT_FEE:.2%} a year</b> on what you hold, "
        f"and nothing on the way in or out.<br><br>"
        f"Every fund here is <b style='color:{TEXT}'>backtested out of sample</b>: "
        f"weights are formed only from data available before each rebalance, so "
        f"nothing you see was fitted with hindsight. We publish the drawdowns, "
        f"the turnover, and the results that went against us.</div>",
        unsafe_allow_html=True)
    st.divider()

    st.markdown(f"<div style='color:{TEXT_MUTED};font-size:0.78rem;"
                f"text-transform:uppercase;letter-spacing:.04em'>Our pick</div>"
                f"<div style='font-weight:600;color:{ACCENT};font-size:1.05rem;"
                f"letter-spacing:{TRACK_TITLE}'>"
                f"{RECOMMENDED}</div>", unsafe_allow_html=True)
    st.caption("Chosen for downside awareness rather than for the top Sharpe. "
               "The fact sheet's co-crash panel shows the trade-off.")
    st.divider()

    cost = st.select_slider(
        "Trading cost assumption", options=[0, 10, 20, 50], value=0,
        format_func=lambda b: f"{b} bps",
        help="Applies the precomputed net-of-cost columns to every fund-level "
             "return and Sharpe. Nothing is re-optimised. Costs were charged "
             "inside the backtest on two-way turnover at every rebalance.")
    st.caption(f"Fund returns and Sharpe are shown **net of {cost} bps** per "
               "unit of two-way turnover. Volatility, drawdown, the growth "
               "charts, and the blend on *Your allocation* stay gross, because "
               "only the net columns were precomputed.")
    st.divider()

    st.markdown(f"<div style='color:{TEXT_DIM};font-size:0.76rem;line-height:1.5'>"
                "50 US large-caps + 10 cryptocurrencies, 2020–2023.<br>"
                "Walk-forward out-of-sample, no look-ahead, "
                "<i>r</i><sub>f</sub> = 0.<br>"
                "All analytics precomputed by <code>scripts/run_part_b.py</code>."
                "</div>", unsafe_allow_html=True)

    # This page is deployed publicly and reads as a live retail product: a
    # recommended fund, growth-of-$1 figures, an allocation builder. Someone
    # arriving without the report has no way to know it is a university
    # exercise on a fixed 2020-2023 dataset, so say so where it cannot be
    # missed rather than only in the About tab.
    st.markdown(
        f"<div style='margin-top:12px;padding:9px 11px;border-radius:{R_MD};"
        f"background:{SURFACE};border-left:3px solid {AMBER};color:{TEXT_MUTED};"
        f"font-size:0.72rem;line-height:1.5'>"
        f"<b style='color:{TEXT}'>Coursework, not investment advice.</b><br>"
        f"A university project built on a fixed 2020–2023 teaching dataset. "
        f"The funds are backtests, not tradeable products, and nothing here is "
        f"a recommendation to buy or sell anything.</div>",
        unsafe_allow_html=True)


def net(col: str) -> pd.Series:
    """Metric column at the cost level chosen in the sidebar."""
    return MET[f"{col}_{cost}bps"]


# --------------------------------------------------------------------------- #
# Header - the recommended fund's headline numbers, before any tab
# --------------------------------------------------------------------------- #
rec_growth = float(growth_of_one(fund_series(R["returns"], RECOMMENDED)).iloc[-1])
st.markdown(
    quote_header(
        f"{RECOMMENDED}   ·   our pick",
        f"{rec_growth:.4f}",
        f"{rec_growth - 1:.4f}",
        f"{rec_growth - 1:+.2%}",
        up=rec_growth >= 1,
        sub="Growth of $1 since the first live rebalance (2021-01-04), gross of "
            "costs · twelve funds across three asset families and four "
            "construction methods, judged on what happens when equities and "
            "crypto fall together"),
    unsafe_allow_html=True)
st.markdown(stat_grid([
    ("Ann. return", f"{net('ann_return')[RECOMMENDED]:+.2%}",
     GREEN if net("ann_return")[RECOMMENDED] >= 0 else RED),
    ("Ann. volatility", f"{REC.ann_vol:.2%}", TEXT),
    ("Sharpe (<i>r</i><sub>f</sub> = 0)",f"{net('sharpe')[RECOMMENDED]:.4f}", TEXT),
    ("Max drawdown", f"{REC.max_drawdown:.2%}", RED),
    ("Turnover p.a.", f"{REC.turnover_ann:.0%}", TEXT),
    ("Holdings", f"{len(R['holdings'][R['holdings']['fund'] == RECOMMENDED])} of "
                 f"{UNIVERSE[REC.family]}", TEXT),
    ("Out-of-sample days", f"{int(REC.n_days):,}", TEXT),
    ("Calendar", f"{int(REC.calendar)}-day", TEXT),
], cols=4), unsafe_allow_html=True)

tab_compare, tab_sheet, tab_alloc, tab_sent, tab_about = st.tabs(
    ["Compare funds", "Fact sheet", "Your allocation",
     "Sentiment analytics", "About & data"])


# --------------------------------------------------------------------------- #
# Tab bodies
#
# Each tab is a fragment, not an inline block. Streamlit executes the body of
# EVERY tab on every rerun - the tab strip only hides the output - so picking a
# different fund used to redraw the sentiment chart, both allocation charts and
# the fact sheet's three figures as well. Nine matplotlib figures rebuilt to
# change one. `st.fragment` scopes a rerun to the fragment whose widget changed,
# so a control inside a tab now redraws that tab only.
#
# The sidebar cost slider is deliberately left OUTSIDE the fragments: it changes
# the numbers on every tab, so it should trigger a full rerun. Everything a
# fragment reads (R, MET, cost, net) is module-level and set during that full
# run, which is what keeps a fragment-only rerun consistent with the sidebar.
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# 1 - Compare funds
# --------------------------------------------------------------------------- #
@st.fragment
def render_compare():
    panel("Twelve funds, one honest comparison",
          "Sorted by Sharpe at the cost level set in the sidebar. "
          "The recommended fund is marked ●.")

    m = MET.copy()
    m["ann_return"], m["sharpe"] = net("ann_return"), net("sharpe")
    table = (m.reset_index()[["fund", "family", "method", "ann_return", "ann_vol",
                              "sharpe", "max_drawdown", "turnover_ann", "calendar"]]
             .sort_values("sharpe", ascending=False))
    table.insert(0, "", ["●" if f == RECOMMENDED else "" for f in table["fund"]])
    # Show the method the way the rest of the app names it ("Min-CVaR"), not the
    # CSV's internal key ("min_cvar") - the fund name already carries it.
    table["method"] = table["fund"].map(method_of)
    table = as_pct(table, "ann_return", "ann_vol", "max_drawdown", "turnover_ann")

    st.dataframe(
        table, width="stretch", hide_index=True,
        height=grid_height(len(table)),
        column_config={
            "": st.column_config.TextColumn("", width="small"),
            "fund": st.column_config.TextColumn("Fund", width="medium"),
            "family": st.column_config.TextColumn("Family"),
            "method": st.column_config.TextColumn("Method"),
            "ann_return": st.column_config.NumberColumn("Ann. return", format="%.1f%%",
                                                        help="Annualised, net of the "
                                                             "selected cost level"),
            "ann_vol": st.column_config.NumberColumn("Ann. vol", format="%.1f%%"),
            "sharpe": st.column_config.ProgressColumn(
                "Sharpe", format="%.2f", min_value=0.0,
                max_value=float(table["sharpe"].max())),
            "max_drawdown": st.column_config.NumberColumn("Max drawdown",
                                                          format="%.1f%%"),
            "turnover_ann": st.column_config.NumberColumn(
                "Turnover p.a.", format="%.0f%%",
                help="Two-way turnover per year, which is what the cost "
                     "slider charges"),
            "calendar": st.column_config.NumberColumn("Cal.", format="%d",
                                                      help="252 trading days for "
                                                           "Combined/Equity-Only, "
                                                           "365 for Crypto-Only, "
                                                           "never blended"),
        })
    st.caption("Returns, volatility, drawdown, and turnover are annual "
               "percentages. Crypto-Only funds annualise on a 365-day calendar, "
               "so their Sharpe is not comparable like-for-like with the "
               "Combined and Equity-Only families. The Cal. column says which "
               "each fund uses.")

    st.divider()
    panel("Growth of $1",
          "Gross of costs, out of sample. Colour is the method; the dash "
          "pattern is the asset family (solid Combined, dashed Equity-Only, "
          "dotted Crypto-Only).")
    picks = st.multiselect("Funds to plot", R["funds"],
                           default=[RECOMMENDED, "Combined Risk Parity",
                                    "Combined Max-Sharpe"],
                           label_visibility="collapsed")
    if picks:
        fig, ax = app_fig()
        for fund in picks:
            g = growth_of_one(fund_series(R["returns"], fund))
            emph = fund == RECOMMENDED
            ax.plot(g.index, g, lw=2.2 if emph else 1.3, color=color_for(fund),
                    linestyle=style_for(fund), alpha=1.0 if emph else 0.85,
                    label=fund, zorder=3 if emph else 2)
        ax.legend(frameon=False, fontsize=8, labelcolor=TEXT_MUTED, ncol=2)
        ax.set_ylabel("Growth of $1")
        show(fig)
    else:
        st.markdown(note("Select at least one fund to plot."),
                    unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# 2 - Fact sheet
# --------------------------------------------------------------------------- #
@st.fragment
def render_fact_sheet():
    fund = st.selectbox("Fund", R["funds"], index=R["funds"].index(RECOMMENDED))
    row, daily = MET.loc[fund], fund_series(R["returns"], fund)
    is_rec = fund == RECOMMENDED

    g_end = float(growth_of_one(daily).iloc[-1])
    hold_n = len(R["holdings"][R["holdings"]["fund"] == fund])
    dr = net("ann_return")[fund] - net("ann_return")[RECOMMENDED]
    ds = net("sharpe")[fund] - net("sharpe")[RECOMMENDED]
    dd = row.max_drawdown - REC.max_drawdown

    cal = int(row.calendar)
    g_fee = float(growth_of_one(after_fee(daily, cal)).iloc[-1])

    st.markdown(
        quote_header(
            f"{fund}{'   ·   our pick' if is_rec else ''}",
            f"{g_end:.4f}", f"{g_end - 1:.4f}", f"{g_end - 1:+.2%}",
            up=g_end >= 1,
            sub=f"Growth of $1 · {len(daily):,} out-of-sample days from "
                f"{daily.index[0].date()} · {cal}-day calendar · "
                f"<b>{g_fee:.4f} after the {MGMT_FEE:.2%} management fee</b>"),
        unsafe_allow_html=True)

    # Key facts, the way a real fact sheet opens: what it costs and how it runs,
    # before any performance number. The fee is first because it is the one
    # figure the investor pays regardless of how the fund does.
    panel("Key facts")
    st.markdown(stat_grid([
        # TEXT, not ACCENT: the accent means "interactive" everywhere else in
        # this app, and a stat value is not clickable. The label carries the
        # emphasis instead.
        ("Management fee", f"{MGMT_FEE:.2%} p.a.", TEXT),
        ("Inception", f"{daily.index[0].date()}", TEXT),
        ("Rebalance", "every 21 trading days", TEXT),
        ("Holdings", f"{hold_n} of {UNIVERSE[row.family]}", TEXT),
        ("Cap per asset", f"{25 if row.family == 'Crypto-Only' else 10}%", TEXT),
        ("Calendar", f"{cal} days", TEXT),
        ("Asset universe", row.family, TEXT),
        ("Method", row.method, TEXT),
    ], cols=4), unsafe_allow_html=True)
    st.caption(
        f"The fee is charged on the investor's balance, not inside the "
        f"strategy: every performance figure below is gross of the "
        f"{MGMT_FEE:.2%} fee and net of the {cost} bps trading-cost setting. "
        f"The after-fee growth of $1 is shown above.")
    st.markdown(stat_grid([
        ("Ann. return", f"{net('ann_return')[fund]:+.2%}",
         GREEN if net("ann_return")[fund] >= 0 else RED),
        ("Ann. volatility", f"{row.ann_vol:.2%}", TEXT),
        ("Sharpe (<i>r</i><sub>f</sub> = 0)",f"{net('sharpe')[fund]:.4f}", TEXT),
        ("Max drawdown", f"{row.max_drawdown:.2%}", RED),
        ("Return vs pick", "this is the pick" if is_rec else f"{dr:+.2%}",
         TEXT_MUTED if is_rec else (GREEN if dr >= 0 else RED)),
        ("Sharpe vs pick", "n/a" if is_rec else f"{ds:+.4f}",
         TEXT_MUTED if is_rec else (GREEN if ds >= 0 else RED)),
        ("Drawdown vs pick", "n/a" if is_rec else f"{dd:+.2%}",
         TEXT_MUTED if is_rec else (GREEN if dd >= 0 else RED)),
        ("Turnover p.a. · holdings",
         f"{row.turnover_ann:.0%} · {hold_n} of {UNIVERSE[row.family]}", TEXT),
    ], cols=4), unsafe_allow_html=True)

    st.divider()
    left, right = st.columns(2)
    with left:
        panel("Growth of $1")
        fig, ax = app_fig((8, 3.8))
        g = growth_of_one(daily)
        ax.plot(g.index, g, color=color_for(fund), lw=2.0)
        ax.fill_between(g.index, g, g.min(), color=color_for(fund), alpha=0.12)
        ax.set_ylabel("Growth of $1")
        show(fig)
    with right:
        panel("Drawdown")
        fig, ax = app_fig((8, 3.8))
        dd = drawdown(daily)
        ax.fill_between(dd.index, 100 * dd, 0, color=RED, alpha=0.55)
        ax.plot(dd.index, 100 * dd, color=RED, lw=1.0)
        ax.set_ylabel("Drawdown (%)")
        show(fig)

    st.divider()
    cap = 25 if row.family == "Crypto-Only" else 10
    panel("Current holdings",
          f"Target weights at the most recent rebalance. Cap: {cap}% per asset "
          f"(Crypto-Only uses 25%, because a 10-asset universe saturates at "
          f"10%).")
    hold = (R["holdings"][R["holdings"]["fund"] == fund]
            .sort_values("weight", ascending=False))
    hold_pct = as_pct(hold, "weight")
    hcol, hchart = st.columns([1, 2])
    with hcol:
        st.dataframe(
            hold_pct[["ticker", "weight"]], width="stretch", hide_index=True,
            height=grid_height(len(hold)),
            column_config={
                "ticker": st.column_config.TextColumn("Holding"),
                "weight": st.column_config.ProgressColumn(
                    "Weight", format="%.1f%%", min_value=0.0,
                    max_value=float(cap))})
        st.caption(f"{len(hold)} holdings of {UNIVERSE[row.family]} on "
                   f"{hold['rebalance_date'].iloc[0].date()}. The optimiser sees "
                   f"all {UNIVERSE[row.family]} assets; the objective and the "
                   f"{cap}% cap choose these. Bars are scaled to the cap.")
    with hchart:
        fig, ax = app_fig((8, 3.6))
        ax.bar(hold["ticker"], 100 * hold["weight"], color=color_for(fund))
        ax.set_ylabel("Weight (%)")
        ax.tick_params(axis="x", labelsize=7, rotation=90)
        show(fig)

    st.divider()
    panel("Co-crash stress test",
          "The exhibit most funds never show you: what happened on the days "
          "equities AND crypto were both in their own worst q%.")
    cc = as_pct(R["co_crash"][R["co_crash"]["fund"] == fund],
                "mean_crash", "worst_crash", "mean_normal", "gap")
    st.dataframe(
        cc[["threshold", "n_crash_days", "mean_crash", "worst_crash",
            "mean_normal", "gap"]],
        width="stretch", hide_index=True, height=grid_height(len(cc)),
        column_config={
            "threshold": st.column_config.TextColumn("Threshold"),
            "n_crash_days": st.column_config.NumberColumn("Crash days", format="%d"),
            "mean_crash": st.column_config.NumberColumn("Mean on crash days",
                                                        format="%.2f%%"),
            "worst_crash": st.column_config.NumberColumn("Worst single day",
                                                         format="%.2f%%"),
            "mean_normal": st.column_config.NumberColumn("Mean, other days",
                                                         format="%.2f%%"),
            "gap": st.column_config.NumberColumn("Gap", format="%.2f%%")})
    # Read the bootstrap range out of co_crash_bootstrap.csv rather than typing
    # it into the sentence. A hand-written range goes stale the moment the
    # pipeline is re-run, and the one that used to sit here ("1.0-2.1pp") was
    # already narrower than the file it sits next to.
    boot = R["boot"]
    sep = boot[boot["distinguishable"]]
    lo, hi = 100 * sep["gap"].abs().min(), 100 * sep["gap"].abs().max()
    same = boot[~boot["distinguishable"]]
    st.caption(
        f"Paired bootstrap over the crash days, {len(boot)} fund pairings: the "
        f"protective pair (Min-CVaR, Min-Variance) beats Risk Parity and "
        f"Max-Sharpe by **{lo:.2f}–{hi:.2f}pp per crash day**, confidence "
        f"intervals excluding zero in all {len(sep)} of those pairings. "
        f"Min-CVaR versus Min-Variance is **not** statistically distinguishable "
        f"at either threshold ({len(same)} pairings, intervals straddling zero), "
        f"stated rather than glossed. The worst single day is shown for "
        f"context only: a bootstrap cannot put an interval on a minimum.")

    with st.expander("Weights over time (every rebalance)"):
        w = R["weights"][R["weights"]["fund"] == fund]
        wide = (w.pivot_table(index="date", columns="ticker", values="weight")
                 .fillna(0.0).sort_index())
        st.area_chart(100 * wide[wide.mean().nlargest(10).index],
                      height=280, y_label="Weight (%)")
        st.caption("Top-10 holdings by average weight, from fund_weights.csv.")


# --------------------------------------------------------------------------- #
# 3 - Your allocation
# --------------------------------------------------------------------------- #
@st.fragment
def render_allocation():
    panel("Blend the funds into your own portfolio",
          "Pick funds and set weights; they are renormalised to 100%. The blend "
          "uses the funds' precomputed daily returns on the trading days they "
          "share, gross of costs.")
    chosen = st.multiselect("Funds to blend", R["funds"],
                            default=[RECOMMENDED, "Combined Risk Parity"],
                            label_visibility="collapsed")
    if not chosen:
        st.markdown(note("Pick at least one fund to build a blend."),
                    unsafe_allow_html=True)
        return

    # Wrap the sliders instead of laying one column per fund. All twelve funds is
    # a normal thing to pick, and twelve columns gives each slider ~100px - too
    # narrow to drag, with the fund name truncated above it. Three per row keeps
    # every slider wide enough to use and the label readable.
    per_row = min(len(chosen), 3)
    raw = []
    for start in range(0, len(chosen), per_row):
        batch = chosen[start:start + per_row]
        # Pad the final row so a lone slider keeps its width instead of stretching.
        cols = st.columns(per_row)
        for col, f in zip(cols, batch):
            raw.append(col.slider(f, 0, 100, 100 // len(chosen), 5))
    total = sum(raw)

    # Every slider at zero is a reachable state, not a pathological one: the
    # sliders bottom out at 0 and a user can drag them all down. Renormalising
    # by a zero total left a portfolio of nothing - 0% return on 0% volatility,
    # and a Sharpe printed as "nan". Say what is missing instead.
    if total == 0:
        st.markdown(note("Every weight is at zero, so there is no portfolio to "
                         "measure. Give at least one fund a weight above 0%."),
                    unsafe_allow_html=True)
        return

    weights = {f: v / total for f, v in zip(chosen, raw)}
    st.caption("Renormalised: " +
               " · ".join(f"**{f}** {w:.0%}" for f, w in weights.items()))

    series = pd.concat({f: fund_series(R["returns"], f) for f in chosen},
                       axis=1).dropna()
    blend = (series * pd.Series(weights)).sum(axis=1)

    # Calendar is a property of the days actually held, not a constant. A
    # crypto-only blend trades all 365 days; mixing in any equity-bearing
    # fund intersects the index down to the 252-day trading calendar. Using
    # 252 for a pure crypto blend understates its volatility by ~20%.
    cal = 365 if all(family_of(f) == "Crypto-Only" for f in chosen) else 252
    ann_ret, ann_vol = blend.mean() * cal, blend.std() * np.sqrt(cal)

    # A mean is linear in weights, so the blend's crash-day mean is exactly
    # the weighted average of the funds' precomputed crash-day means.
    cc = R["co_crash"].set_index(["fund", "threshold"])
    blend_crash = sum(w * cc.loc[(f, "q=10%"), "mean_crash"]
                      for f, w in weights.items())
    g_blend = float(growth_of_one(blend).iloc[-1])
    blend_dd = drawdown(blend).min()
    # Same fee on a blend as on a single fund: the investor holds one balance
    # with us either way, so blending is not a way to avoid the charge.
    g_blend_fee = float(growth_of_one(after_fee(blend, cal)).iloc[-1])

    st.markdown(
        quote_header(
            "Your blend", f"{g_blend:.4f}", f"{g_blend - 1:.4f}",
            f"{g_blend - 1:+.2%}", up=g_blend >= 1,
            sub=f"Growth of $1 over the {len(blend):,} trading days these "
                f"funds share, gross of costs · "
                f"<b>{g_blend_fee:.4f} after the {MGMT_FEE:.2%} "
                f"management fee</b>"),
        unsafe_allow_html=True)
    st.markdown(stat_grid([
        ("Ann. return", f"{ann_ret:+.2%}", GREEN if ann_ret >= 0 else RED),
        ("Ann. volatility", f"{ann_vol:.2%}", TEXT),
        ("Sharpe (<i>r</i><sub>f</sub> = 0)",f"{ann_ret / ann_vol:.4f}", TEXT),
        ("Max drawdown", f"{blend_dd:.2%}", RED),
        ("Mean on joint-crash days (q = 10%)", f"{blend_crash:+.2%}",
         GREEN if blend_crash >= 0 else RED),
        ("Funds blended", f"{len(chosen)}", TEXT),
        ("Largest sleeve", f"{max(weights.values()):.0%}", TEXT),
        ("Calendar", f"{cal}-day", TEXT),
    ], cols=4), unsafe_allow_html=True)
    st.caption("The crash-day figure is exact, not simulated: a mean is "
               "linear in weights, so the blend's average on those days is "
               "the weighted average of the funds' own, which is the number a "
               "Sharpe-only comparison hides.")
    fig, ax = app_fig()
    g = growth_of_one(blend)
    for f in chosen:
        gg = growth_of_one(series[f])
        ax.plot(gg.index, gg, lw=1.1, alpha=0.65, color=color_for(f),
                linestyle=style_for(f), label=f)
    # White, not ACCENT: ACCENT is Min-CVaR's colour, so a blend containing
    # Min-CVaR used to draw two blue lines and leave the reader guessing
    # which one was theirs.
    ax.plot(g.index, g, color=BLEND, lw=2.6, label="Your blend", zorder=5)
    ax.legend(frameon=False, fontsize=8, labelcolor=TEXT_MUTED, ncol=2)
    ax.set_ylabel("Growth of $1")
    show(fig)


# --------------------------------------------------------------------------- #
# 4 - Sentiment analytics
# --------------------------------------------------------------------------- #
@st.fragment
def render_sentiment():
    idx = R["index"]
    daily_idx = idx.groupby("trading_day")["sentiment"].mean().sort_index()
    last21, prev21 = daily_idx.iloc[-21:].mean(), daily_idx.iloc[-42:-21].mean()
    ev_real = R["events"][~R["events"]["event"].str.contains("control")]

    as_of = daily_idx.index[-1].date()
    st.markdown(
        quote_header(
            f"Market sentiment · all sectors, 21-day mean to {as_of}",
            f"{last21:+.4f}", f"{last21 - prev21:+.4f}",
            f"{(last21 - prev21) / abs(prev21):+.1%}" if prev21 else "n/a",
            up=last21 >= prev21,
            sub=f"Compound score, equal-weighted across the 10 equity sectors, "
                f"over the 21 trading days ending {as_of}. Change is against the "
                f"preceding 21 trading days. This is the end of the fixed "
                f"2020–2023 course dataset, not a live feed."),
        unsafe_allow_html=True)
    st.markdown(stat_grid([
        ("Sector-day observations", f"{len(idx):,}", TEXT),
        ("Sectors covered", f"{idx['sector'].nunique()}", TEXT),
        ("Index span", f"{idx['trading_day'].min().date()} → "
                       f"{idx['trading_day'].max().date()}", TEXT),
        ("Crash events recognised", f"{int(ev_real['recognised'].sum())} of "
                                    f"{len(ev_real)}", GREEN),
        ("Thinnest sector coverage", f"{R['coverage']['pct_days_covered'].min():.1f}%",
         TEXT),
        ("Fewest mean tickers", f"{R['coverage']['mean_tickers'].min():.2f}", TEXT),
        ("Signal lag", "≥ 1 trading day", TEXT),
        ("No-headline days", "left undefined", TEXT),
    ], cols=4), unsafe_allow_html=True)

    panel("What the news says, sector by sector",
          "Finance-tuned VADER compound scores on 105,330 distinct headlines "
          "(146,830 headline-ticker rows): ticker-day mean first, then "
          "equal-weight across each sector's tickers. Sector-days with no "
          "headlines are left undefined, never invented.")

    sectors = sorted(idx["sector"].unique())
    c1, c2 = st.columns([3, 2])
    picks = c1.multiselect("Sectors", sectors,
                           default=["Tech", "Energy", "Financials"])
    window = c2.select_slider("Smoothing", [1, 5, 21, 63], value=21,
                              format_func=lambda d: f"{d}-day")
    if picks:
        wide = (R["index"].pivot_table(index="trading_day", columns="sector",
                                       values="sentiment")[picks]
                .rolling(window, min_periods=max(2, window // 4)).mean())
        fig, ax = app_fig((9, 4.4))
        for sec in picks:
            ax.plot(wide.index, wide[sec], lw=1.6, label=sec)
        ax.axhline(0, color=TEXT_DIM, lw=0.8)
        ax.legend(frameon=False, fontsize=8, labelcolor=TEXT_MUTED)
        ax.set_ylabel("Sentiment (compound)")
        show(fig)
    else:
        st.markdown(note("Select at least one sector to plot its index."),
                    unsafe_allow_html=True)
    st.caption("In the funds, sentiment is lagged at least one trading day, so "
               "a decision on day t may only use day t−1 news or older.")

    st.divider()
    left, right = st.columns(2)
    with left:
        panel("Does the index recognise real crashes?")
        st.dataframe(
            as_pct(R["events"], "percentile")[
                ["event", "index_mean", "percentile", "recognised"]],
            width="stretch", hide_index=True,
            height=grid_height(len(R["events"])),
            column_config={
                "event": st.column_config.TextColumn("Event", width="medium"),
                "index_mean": st.column_config.NumberColumn("Index level",
                                                            format="%.3f"),
                "percentile": st.column_config.NumberColumn("Percentile",
                                                            format="%.1f%%"),
                "recognised": st.column_config.CheckboxColumn("Flagged")})
        st.caption("Three crash events Part A verified as real all sit in the "
                   "index's bottom quartile. The fourth row is a positive "
                   "control, a large *rally*, and is correctly not flagged. "
                   "The control is what makes this a test rather than decoration.")
    with right:
        panel("Coverage by sector", "The no-headline-day rule, quantified.")
        st.dataframe(
            R["coverage"][["sector", "pct_days_covered", "mean_tickers",
                           "pct_days_single_ticker"]]
            .sort_values("pct_days_covered"),
            width="stretch", hide_index=True,
            height=grid_height(len(R["coverage"])),
            column_config={
                "sector": st.column_config.TextColumn("Sector"),
                "pct_days_covered": st.column_config.ProgressColumn(
                    "Days covered", format="%.1f%%", min_value=0.0,
                    max_value=100.0),
                "mean_tickers": st.column_config.NumberColumn("Mean tickers",
                                                              format="%.2f"),
                "pct_days_single_ticker": st.column_config.NumberColumn(
                    "Days on 1 ticker", format="%.1f%%",
                    help="Share of that sector's covered days whose index value "
                         "rests on a single ticker's headlines")})
        # The mean is the flattering number; the last column is the honest one. A
        # sector averaging 2.84 active tickers still has days carried by one name.
        worst = R["coverage"].sort_values("pct_days_single_ticker").iloc[-1]
        st.caption(
            f"The thinnest sectors still average roughly three active tickers on "
            f"the days they have news, but the floor is one, not three: "
            f"**{worst['sector']}** rests on a single ticker on "
            f"**{worst['pct_days_single_ticker']:.1f}%** of its covered days. "
            f"Those readings are the noisiest in the index.")

    st.divider()
    panel("Did sentiment improve the funds?", "The honest answer.")
    st.dataframe(
        R["fusion"][["fund", "sharpe_base", "sharpe_fused",
                     "sharpe_delta_gross", "sharpe_delta_net20bps"]],
        width="stretch", hide_index=True, height=grid_height(len(R["fusion"])),
        column_config={
            "fund": st.column_config.TextColumn("Fund", width="medium"),
            "sharpe_base": st.column_config.NumberColumn("Sharpe, base",
                                                         format="%.4f"),
            "sharpe_fused": st.column_config.NumberColumn("Sharpe, with tilt",
                                                          format="%.4f"),
            "sharpe_delta_gross": st.column_config.NumberColumn("Δ gross",
                                                                format="%.4f"),
            "sharpe_delta_net20bps": st.column_config.NumberColumn("Δ net 20 bps",
                                                                   format="%.4f")})
    st.caption("A sentiment-z tilt (k = 0.1, capped, lagged) on the equity "
               "sleeve: slightly positive gross for three of four funds, and "
               "roughly zero-to-negative once 20 bps of trading cost is charged "
               "because the tilt trades more than the signal knows. Reported as it "
               "came out rather than tuned until it flattered.")


# --------------------------------------------------------------------------- #
# About & data
# --------------------------------------------------------------------------- #
@st.fragment
def render_about():
    st.markdown(
        status_banner(
            False,
            f"University coursework, not investment advice · {AUTHOR} ({ZID})",
            "Built for UNSW FINS3645 Financial Market Data Design &amp; Analysis, "
            "Project Part B. Every fund on this site is a backtest over a fixed "
            "2020–2023 teaching dataset: none is a tradeable product, past "
            "backtested performance is not a forecast, and nothing here is a "
            "recommendation to buy or sell any security."),
        unsafe_allow_html=True)
    st.write("")
    panel("How Quokka works")
    st.markdown("""
- **Universe**: 50 US large-caps (10 sectors) + 10 cryptocurrencies, 2020–2023,
  loaded from the hosted course dataset. Each fund's optimiser sees its family's
  whole universe (60 assets for Combined, 50 for Equity-Only, 10 for
  Crypto-Only), and the long-only cap (10%, 25% for Crypto-Only) plus the
  objective choose the holdings. Concentration is an output, not a setting: at
  the latest rebalance the Combined funds hold 12–20 of 60, Equity-Only 15–19
  of 50, and Crypto-Only 5–7 of 10. Risk Parity is the exception, holding every
  asset by construction.
- **Methods**: Max-Sharpe, Min-Variance, Risk Parity, and Min-CVaR
  (Rockafellar–Uryasev linear program on historical scenarios at β = 0.95).
- **Risk estimate**: EWMA covariance, span 252 (half-life ≈ 87 trading days),
  recomputed at each rebalance from strictly-past data.
- **Backtest**: walk-forward, expanding window, 252-day burn-in, monthly
  (21-trading-day) rebalance; first live rebalance 2021-01-04 (2020-09-10 for
  Crypto-Only). No look-ahead: weights and sentiment use only earlier data, and
  the guarantee is machine-tested, not asserted.
- **Costs**: headline figures are gross; the sidebar slider applies the
  precomputed net-of-cost columns (0/10/20/50 bps per unit of two-way turnover).
  Within each asset family the Sharpe ranking never reorders across that grid.
  Across families it can: Equity-Only Min-Variance leads Combined Max-Sharpe by
  0.002 at 20 bps and trails it by 0.011 at 50 bps, because it turns over more.
- **Sentiment**: a finance-tuned VADER lexicon (general + two finance word
  lists, plus 28 human-reviewed terms), scored on raw headline text and lagged
  at least one trading day before any fund decision.
- **This app recomputes nothing.** Every number is read from `results/`,
  precomputed by `scripts/run_part_b.py`; the sentiment model runs only at build
  time, and the app's only arithmetic is display math (growth of $1, drawdowns,
  allocation blends).
""")
    st.divider()
    panel("The hosted data, live",
          "Proof the pipeline still points at the real source.")
    try:
        from src import data_access
        # The loader caches with show_spinner=False, so without a spinner of our
        # own the panel is simply blank while the bundle downloads - which reads
        # as a broken empty box rather than as work in progress.
        with st.spinner("Connecting to the hosted dataset…"):
            eq = data_access.load_equity_prices()
        st.markdown(
            status_banner(
                True,
                f"Connected: {eq.shape[0]:,} equity price rows · "
                f"{eq['ticker'].nunique()} tickers · "
                f"{eq['date'].min().date()} to {eq['date'].max().date()}",
                "Downloaded live from the hosted course bundle at page load, not "
                "read from results/. The first twelve rows are shown below."),
            unsafe_allow_html=True)
        st.dataframe(
            eq.head(12), width="stretch", hide_index=True, height=grid_height(12),
            column_config={
                "ticker": st.column_config.TextColumn("Ticker"),
                "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                "open": st.column_config.NumberColumn("Open", format="%.2f"),
                "high": st.column_config.NumberColumn("High", format="%.2f"),
                "low": st.column_config.NumberColumn("Low", format="%.2f"),
                "close": st.column_config.NumberColumn("Close", format="%.2f"),
                "adjClose": st.column_config.NumberColumn("Adj. close",
                                                          format="%.2f"),
                "volume": st.column_config.NumberColumn("Volume", format="%,d"),
                "sector": st.column_config.TextColumn("Sector")})
    except Exception as exc:  # keep the app alive if the host is briefly down
        st.markdown(
            status_banner(
                False, "Hosted data unavailable right now",
                f"{exc}<br>The fund analytics are unaffected, because they read "
                f"local results/."),
            unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Mount each fragment in its tab. Rendering happens here, in tab order, so the
# investor journey reads top to bottom in one place.
# --------------------------------------------------------------------------- #
with tab_compare:
    render_compare()
with tab_sheet:
    render_fact_sheet()
with tab_alloc:
    render_allocation()
with tab_sent:
    render_sentiment()
with tab_about:
    render_about()
