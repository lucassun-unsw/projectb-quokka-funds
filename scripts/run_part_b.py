"""Reproduce every Part B result. Run from the project root:

    python scripts/run_part_b.py

Single entrypoint: ETL -> returns -> 12 funds -> sentiment -> fusion -> lexicon
-> every required CSV and figure under results/. The one structural rule, carried
from Part A's costliest late bug: each exhibit family is derived from ONE computed
object. Every fund's CSV rows, figures, and fact-sheet numbers come from the same
`BacktestResult`; the sentiment CSV and its figure come from the same index frame.
Nothing is recomputed per call site.

Build-only script - imports finvader/nltk via src.sentiment. The deployed app
reads the results/ files this writes and imports none of this.
"""
from __future__ import annotations

import pathlib
import sys

import matplotlib

matplotlib.use("Agg")  # headless - this script only saves files
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import dependence, etl, features, text_panel
from src import fusion as fu
from src import lexicon as lx
from src import portfolios as pf
from src import sentiment as sn
from src.ft_style import (
    FT_BLUE,
    FT_GREY,
    FT_MAROON,
    FT_TEAL,
    apply_ft_style,
    ft_header,
    save_ft,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "results" / "data"
TABLES = ROOT / "results" / "tables"
FIGURES = ROOT / "results" / "figures"

HEADLINE_K = fu.DEFAULT_K          # 0.10, provisional until confirmed (OUTLINE)
COLORS = [FT_MAROON, FT_BLUE, FT_TEAL, FT_GREY]
METHOD_LABEL = {"max_sharpe": "Max-Sharpe", "min_variance": "Min-Variance",
                "risk_parity": "Risk Parity", "min_cvar": "Min-CVaR"}

# The three Part A-verified crash events plus the positive control, defined once
# so the base index and the lexicon-extended index are validated on identical
# dates - the two tables are meant to be read against each other.
EVENT_DATES = {
    "OXY -52.0% (2020-03-09)": "2020-03-09",
    "BCH-USD -43.0% (2020-03-12)": "2020-03-12",
    "COVID crash week (2020-03-16)": "2020-03-16",
    "XLM-USD +74.9% control (2021-01-06)": "2021-01-06",
}


def wide_returns(panel: pd.DataFrame, asset_class: str | None = None) -> pd.DataFrame:
    sub = panel if asset_class is None else panel[panel["asset_class"] == asset_class]
    return (sub.pivot_table(index="date", columns="ticker", values="ret")
               .sort_index().dropna(how="any"))


# --------------------------------------------------------------------------- #
# Stage 1 - data and returns (frozen Part A foundation)
# --------------------------------------------------------------------------- #
def load_stage():
    print("[1/6] data + returns (frozen Part A foundation)")
    eq, cr = etl.load_clean_equities(), etl.load_clean_crypto()
    news = etl.load_clean_news()
    cal = etl.equity_trading_calendar(eq)
    combined_panel = features.build_combined_panel(eq, cr)
    stats_panel = features.build_stats_panel(eq, cr)
    assert eq.shape == (50300, 9) and len(combined_panel) == 60360, \
        "frozen Part A row counts drifted - stop and investigate"
    print(f"  equity {eq.shape}, crypto {cr.shape}, combined panel "
          f"{len(combined_panel):,} rows")
    return eq, cr, news, cal, combined_panel, stats_panel


# --------------------------------------------------------------------------- #
# Stage 2 - the 12 funds (Station 3 core + innovations)
# --------------------------------------------------------------------------- #
def funds_stage(combined_panel, stats_panel):
    print("[2/6] funds: 3 families x 4 methods, walk-forward OOS")
    panels = {"Combined": wide_returns(combined_panel),
              "Equity-Only": wide_returns(combined_panel, "equity"),
              "Crypto-Only": wide_returns(stats_panel, "crypto")}
    results: dict[str, pf.BacktestResult] = {}
    for family, R in panels.items():
        for method in pf.METHODS:
            res = pf.oos_backtest(R, method, family)
            results[res.fund] = res
    assert all(r.solver_ok for r in results.values()), "a solver failed"

    # required exact filenames - long format, from the SAME BacktestResults
    returns_long = pd.concat(
        [r.returns.rename("ret").rename_axis("date").reset_index()
          .assign(fund=r.fund) for r in results.values()])
    returns_long[["date", "fund", "ret"]].to_csv(DATA / "fund_returns.csv", index=False)

    weights_long = pd.concat(
        [r.weights.rename_axis("date").reset_index()
          .melt(id_vars="date", var_name="ticker", value_name="weight")
          .assign(fund=r.fund) for r in results.values()])
    weights_long = weights_long[weights_long["weight"] > 1e-6]
    weights_long[["date", "fund", "ticker", "weight"]].to_csv(
        DATA / "fund_weights.csv", index=False)

    metrics = pf.metrics_table(list(results.values()))
    metrics.to_csv(TABLES / "performance_metrics.csv", index=False)

    # current holdings per fund (fact-sheet bullet: latest target weights,
    # distinct from the weights-over-time exhibit) - same BacktestResults
    holdings = pd.concat(
        [r.latest_holdings().rename("weight").rename_axis("ticker").reset_index()
          .assign(fund=r.fund, rebalance_date=r.weights.index[-1])
         for r in results.values()])
    holdings[["fund", "rebalance_date", "ticker", "weight"]].to_csv(
        TABLES / "current_holdings.csv", index=False)
    print(f"  wrote fund_returns.csv ({len(returns_long):,} rows), "
          f"fund_weights.csv ({len(weights_long):,} rows), "
          f"performance_metrics.csv ({len(metrics)} funds)")

    # EWMA justification diagnostic (Section 1 exhibit)
    agg = features.asset_class_aggregate(combined_panel)
    acf = pd.concat([sn_acf.assign(asset_class=cls) for cls, sn_acf in
                     ((c, pf.squared_return_autocorr(agg[c])) for c in agg.columns)])
    acf.to_csv(TABLES / "vol_clustering_acf.csv", index=False)
    return panels, results, agg, metrics


def co_crash_stage(results, agg):
    print("[3/6] co-crash stress test + paired bootstrap (innovation)")
    panels, boots = [], []
    combined = {m: results[f"Combined {pf.METHOD_DISPLAY[m]}"] for m in pf.METHODS}
    # Pairs are (fund_a, benchmark). The min-variance block is the protective-pair
    # test; the min-CVaR block is what Section 4's argument actually needs, since
    # the recommended fund IS min-CVaR - "a Sharpe-shopper picks risk parity and
    # takes ~1pp more per crash day" is a claim against min-CVaR, not min-variance,
    # and it must come from a saved interval rather than a hand-quoted one.
    PAIRS = [("min_cvar", "min_variance"),
             ("risk_parity", "min_variance"),
             ("max_sharpe", "min_variance"),
             ("risk_parity", "min_cvar"),
             ("max_sharpe", "min_cvar")]
    for q in (0.05, 0.10):
        crash = dependence.joint_crash_dates(agg, q=q)
        panels.append(pf.co_crash_panel(list(results.values()), crash, f"q={q:.0%}"))
        for a, ref in PAIRS:
            b = pf.co_crash_bootstrap(combined[a].returns,
                                      combined[ref].returns, crash)
            boots.append({"threshold": f"q={q:.0%}",
                          "fund_a": f"Combined {pf.METHOD_DISPLAY[a]}",
                          "fund_b": f"Combined {pf.METHOD_DISPLAY[ref]}", **b})
        n = len(crash.intersection(combined["min_cvar"].returns.index))
        print(f"  q={q:.0%}: {n} OOS crash days")
    pd.concat(panels).to_csv(TABLES / "co_crash_panel.csv", index=False)
    pd.DataFrame(boots).to_csv(TABLES / "co_crash_bootstrap.csv", index=False)


# --------------------------------------------------------------------------- #
# Stage 2b - parameter study (the evidence behind the locked risk estimate)
# --------------------------------------------------------------------------- #
def parameter_study_stage(panels, results):
    """Re-run one fund under rival covariance estimates, and measure how far apart
    the four methods actually are.

    Section 1 rests on "EWMA at span 252 beats the alternatives on volatility" and
    Section 6 recommends a turnover-penalised rule on the strength of the EWMA-vs-
    static turnover gap. Those numbers were originally produced in an exploratory
    session and quoted from its transcript. Saving them here puts them under the
    same rule as every other number in the report: quotable only from a CSV.

    Combined Min-Variance is the test fund - the covariance estimate is the whole
    input to that objective, so the comparison isolates the estimator. Min-CVaR is
    deliberately excluded: it optimises scenarios directly and never forms a
    covariance, so it cannot separate these configurations.
    """
    print("[parameter study] rival covariance estimates + method separation")
    R = panels["Combined"]
    configs = [("ewma_span_252 (locked)", "ewma", pf.EWMA_SPAN),
               ("ewma_span_126", "ewma", 126),
               ("ewma_span_32 (RiskMetrics-style)", "ewma", 32),
               ("static_full_window", "static", pf.EWMA_SPAN)]
    rows = []
    for label, est, span in configs:
        res = pf.oos_backtest(R, "min_variance", "Combined",
                              cov_estimator=est, cov_span=span, verbose=False)
        m = pf.performance_metrics(res.returns, res.calendar)
        row = {"estimator": label, "fund": "Combined Min-Variance",
               "ann_return": m["ann_return"], "ann_vol": m["ann_vol"],
               "sharpe": m["sharpe"], "max_drawdown": m["max_drawdown"],
               "turnover_ann": float(res.turnover.iloc[1:].mean()
                                     * (res.calendar / pf.REBALANCE_STEP))}
        # By-year split: the volatility edge is claimed only because it holds in
        # every year, while the return edge flips sign and therefore is not claimed.
        for year, r in res.returns.groupby(res.returns.index.year):
            row[f"ann_vol_{year}"] = float(r.std() * np.sqrt(res.calendar))
            row[f"ann_return_{year}"] = float(r.mean() * res.calendar)
        rows.append(row)
    study = pd.DataFrame(rows)
    study.to_csv(TABLES / "parameter_study.csv", index=False)

    # Method separation: the brief's stalled-optimiser trap answered with a number.
    # If two methods returned near-identical books, "four funds" would be a fiction
    # - this is the check that caught the crypto cap degeneracy.
    #
    # Read the MINIMUM per family, not the individual pairs. The statistic saturates:
    # whenever one method pins an asset at the cap and the other holds nothing of it,
    # the maximum difference IS the cap, and half the pairs land there. Those rows say
    # "as far apart as this constraint allows", not "0.10 apart", so `at_family_cap`
    # flags them and the closest unsaturated pair is the number worth quoting.
    sep = []
    for family in ("Combined", "Equity-Only", "Crypto-Only"):
        cap = pf.FAMILY_CAPS[family]
        for i, a in enumerate(pf.METHODS):
            for b in pf.METHODS[i + 1:]:
                wa = results[f"{family} {pf.METHOD_DISPLAY[a]}"].weights
                wb = results[f"{family} {pf.METHOD_DISPLAY[b]}"].weights
                diff = float((wa - wb).abs().max().max())
                sep.append({"family": family,
                            "method_a": pf.METHOD_DISPLAY[a],
                            "method_b": pf.METHOD_DISPLAY[b],
                            "max_abs_weight_diff": diff,
                            "family_cap": cap,
                            "at_family_cap": bool(abs(diff - cap) < 1e-9)})
    separation = pd.DataFrame(sep)
    separation.to_csv(TABLES / "method_separation.csv", index=False)

    ewma, static = study.iloc[0], study.iloc[3]
    closest = separation.groupby("family")["max_abs_weight_diff"].min()
    print(f"  EWMA-252 vol {ewma.ann_vol:.2%} vs static {static.ann_vol:.2%}; "
          f"turnover {ewma.turnover_ann:.0%}/yr vs {static.turnover_ann:.0%}/yr")
    print(f"  closest method pair per family: "
          f"{', '.join(f'{k} {v:.3f}' for k, v in closest.items())}")
    n_solves = sum(len(r.weights) for r in results.values())
    print(f"  {n_solves} rebalance solves across the 12 funds, all converged")


# --------------------------------------------------------------------------- #
# Stage 3 - sentiment (Station 3 core)
# --------------------------------------------------------------------------- #
def sentiment_stage(news, cal):
    print("[4/6] sentiment: finVADER scoring -> two-step sector index")
    print(f"  versions: {sn.package_versions()}")
    hpanel = text_panel.assemble_headline_panel(news, cal)
    scored = sn.score_headlines(hpanel)
    index = sn.sector_sentiment_index(scored)
    index.to_csv(DATA / "sector_sentiment_index.csv", index=False)

    coverage = sn.coverage_report(index, cal)
    coverage.to_csv(TABLES / "sentiment_coverage.csv", index=False)
    validation = sn.validate_against_events(index, EVENT_DATES)
    validation.to_csv(TABLES / "sentiment_event_validation.csv", index=False)

    # The brief's own warning about VADER, measured on this data rather than
    # accepted on faith: "about half of finance headlines score neutral with plain
    # VADER". Saved because it is the evidence for using a finance lexicon at all,
    # and a number that lives only in prose is a number this project does not trust.
    sn.neutrality_comparison(scored).to_csv(
        TABLES / "sentiment_neutrality.csv", index=False)
    rec = validation[validation.event.str.contains("control") == False]  # noqa: E712
    print(f"  index: {len(index):,} sector-day rows; crash events recognised: "
          f"{int(rec.recognised.sum())}/{len(rec)}")
    return scored, index


# --------------------------------------------------------------------------- #
# Stage 4 - fusion (Station 3 required extension)
# --------------------------------------------------------------------------- #
def fusion_stage(panels, results, scored, cal):
    print(f"[5/6] fusion: sentiment-z tilt, headline k={HEADLINE_K:g}")
    z = sn.sentiment_z(sn.fusion_signal(scored, cal))
    R = panels["Combined"]
    rows, fused_headline = [], None
    for method in pf.METHODS:
        base = results[f"Combined {pf.METHOD_DISPLAY[method]}"]
        fused = fu.fused_backtest(R, base, z, k=HEADLINE_K)
        if method == "min_cvar":
            fused_headline = fused
        bm = pf.performance_metrics(base.returns, base.calendar)
        fm = pf.performance_metrics(fused.returns, fused.calendar)
        bn = pf.performance_metrics(base.net_returns["net_20bps"], base.calendar)
        fn = pf.performance_metrics(fused.net_returns["net_20bps"], fused.calendar)
        rows.append({
            "fund": base.fund, "k": HEADLINE_K,
            "sharpe_base": bm["sharpe"], "sharpe_fused": fm["sharpe"],
            "sharpe_delta_gross": fm["sharpe"] - bm["sharpe"],
            "sharpe_base_net20bps": bn["sharpe"], "sharpe_fused_net20bps": fn["sharpe"],
            "sharpe_delta_net20bps": fn["sharpe"] - bn["sharpe"],
            "ann_return_base": bm["ann_return"], "ann_return_fused": fm["ann_return"],
            "max_dd_base": bm["max_drawdown"], "max_dd_fused": fm["max_drawdown"],
            # Endpoint growth of $1 saved so the report can quote the before/after
            # pair from a CSV instead of reading it off the figure.
            "growth_of_one_base": float(base.growth_of_one().iloc[-1]),
            "growth_of_one_fused": float(fused.growth_of_one().iloc[-1]),
            "turnover_base": float(base.turnover.iloc[1:].mean()),
            "turnover_fused": float(fused.turnover.iloc[1:].mean())})
    before_after = pd.DataFrame(rows)
    before_after.to_csv(TABLES / "fusion_before_after.csv", index=False)
    grid = fu.k_grid(R, results["Combined Min-CVaR"], z)
    grid.to_csv(TABLES / "fusion_k_grid.csv", index=False)
    print(f"  before/after written; net-20bps Sharpe deltas: "
          f"{[f'{d:+.4f}' for d in before_after.sharpe_delta_net20bps]}")
    return before_after, fused_headline


# --------------------------------------------------------------------------- #
# Stage 5 - lexicon extension (secondary innovation)
# --------------------------------------------------------------------------- #
def lexicon_stage(scored, index):
    print("[6/6] lexicon extension (AI-rater + human review)")
    candidates = lx.verify_absent(lx.propose_candidates())
    lx.write_review_file(candidates)
    reviewed = lx.extend_terms(verbose=False)
    if reviewed:
        terms, mode = reviewed, "human-reviewed"
    else:
        terms, mode = lx.extend_terms(ai_only=True, verbose=False), "PROVISIONAL_ai_only"
        print("  ** human review pending in results/tables/lexicon_candidates.csv **")
        print("  ** before/after below is PROVISIONAL - rebuild after review    **")
    ext = lx.rescore_with_extension(scored, terms)

    # Index-level impact of the extension. Both numbers used to be quoted from a
    # session transcript; they are saved here so the report can source them. The
    # correlation answers "does the extension refine or rewrite the index?", and
    # the re-run event validation is where the OXY sharpening legitimately lives -
    # Section 3 quotes the BASE index, Section 4 quotes this file.
    index_ext = sn.sector_sentiment_index(ext)
    joined = index.merge(index_ext, on=["trading_day", "sector"],
                         suffixes=("_base", "_ext"))
    index_corr = float(joined["sentiment_base"].corr(joined["sentiment_ext"]))

    table = lx.before_after(scored, ext, terms).assign(
        mode=mode, index_corr_with_base=index_corr)
    table.to_csv(TABLES / "lexicon_before_after.csv", index=False)

    validation_ext = sn.validate_against_events(index_ext, EVENT_DATES)
    validation_ext.to_csv(TABLES / "lexicon_event_validation.csv", index=False)

    print(f"  {mode}: {int(table.n_false_neutrals_fixed.iloc[0])} false neutrals fixed; "
          f"index corr with base {index_corr:.3f}")


# --------------------------------------------------------------------------- #
# Figures - every one from the SAME objects the CSVs came from
# --------------------------------------------------------------------------- #
def year_axis(ax):
    """Readable date axis: one major tick per year - the default mushes labels."""
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


def figures_stage(results, metrics, index, before_after, fused_headline):
    print("figures: FT-style exhibits")
    apply_ft_style()
    combined = {m: results[f"Combined {pf.METHOD_DISPLAY[m]}"] for m in pf.METHODS}

    # 1. Sharpe barplot across all funds and methods (required)
    fig, ax = plt.subplots(figsize=(12, 6))
    m = metrics.copy()
    m["label"] = m["family"] + "\n" + m["method"].map(METHOD_LABEL)
    order = m.sort_values(["family", "sharpe"], ascending=[True, False])
    bars = ax.bar(range(len(order)), order["sharpe"],
                  color=[COLORS[pf.METHODS.index(mm)] for mm in order["method"]])
    ax.set_xticks(range(len(order)), order["label"], fontsize=7)
    # Mathtext, not the literal "rf": the risk-free rate is a variable with a
    # subscript, and "rf" reads as a two-letter symbol that does not exist.
    ax.set_ylabel(r"Sharpe ratio ($r_f = 0$)")
    ax.bar_label(bars, fmt="%.2f", fontsize=7, color=FT_GREY)
    # "Risk parity wins" is true WITHIN a family, and the chart's two tallest bars
    # are Crypto-Only funds - so the title has to carry the qualifier or it reads as
    # contradicted by the exhibit beneath it. ft_header does not wrap (it is the
    # frozen Part A port), so the caveat goes in the source line, which is set at
    # fontsize 8 and has roughly twice the character budget of the subtitle.
    ft_header(fig, "Risk parity wins its family on Sharpe - but Sharpe is not the "
                   "whole story",
              "Annualised Sharpe by fund family and method, out of sample, "
              r"$r_f = 0$ | "
              "calendar 252 (Combined, Equity-Only) / 365 (Crypto-Only)",
              "Source: project data, walk-forward backtest 2021-2023 (crypto from "
              "2020-09) | the two tallest bars are Crypto-Only funds on a 365-day "
              "calendar, not comparable like-for-like with the rest")
    save_ft(fig, str(FIGURES / "performance_sharpe_bar.png"))
    plt.close(fig)

    # 2. Growth of $1 - Combined methods (required)
    fig, ax = plt.subplots(figsize=(10, 6))
    for c, method in zip(COLORS, pf.METHODS):
        g = combined[method].growth_of_one()
        ax.plot(g.index, g, color=c, lw=1.8, label=METHOD_LABEL[method])
        ax.annotate(METHOD_LABEL[method], (g.index[-1], g.iloc[-1]),
                    color=c, fontsize=9, xytext=(4, 0), textcoords="offset points")
    ax.set_ylabel("Growth of $1")
    ax.margins(x=0.08)
    year_axis(ax)
    ft_header(fig, "Four constructions, four very different rides on the same assets",
              "Growth of $1, Combined equity+crypto funds, gross of costs, "
              "monthly rebalance, 252-day burn-in",
              "Source: project data | first live rebalance 2021-01-04")
    save_ft(fig, str(FIGURES / "growth_of_one.png"))
    plt.close(fig)

    # 3. Drawdown (required, >=1 fund - all four Combined funds shown)
    fig, ax = plt.subplots(figsize=(10, 6))
    for c, method in zip(COLORS, pf.METHODS):
        d = combined[method].drawdown()
        ax.plot(d.index, 100 * d, color=c, lw=1.5, label=METHOD_LABEL[method])
    ax.set_ylabel("Drawdown (%)")
    ax.legend(frameon=False, fontsize=9)
    year_axis(ax)
    ft_header(fig, "Max-Sharpe pays for its returns with the deepest drawdowns",
              "Drawdown from running peak (%), Combined funds, out of sample",
              "Source: project data, same backtest as the performance table")
    save_ft(fig, str(FIGURES / "drawdown.png"))
    plt.close(fig)

    # 4. Weights over time - one asset across all methods (required)
    ticker = "NVDA"
    fig, ax = plt.subplots(figsize=(10, 6))
    # Min-Variance and Min-CVaR both hold zero NVDA at most rebalances, so plotting
    # four solid lines drew them exactly on top of each other and whichever came
    # last simply erased the other. A dash pattern per method keeps both readable
    # where they coincide - which is the whole point of the exhibit, since "two of
    # four methods hold none of it" is the finding.
    styles = {"max_sharpe": "-", "min_variance": (0, (5, 2)),
              "risk_parity": "-", "min_cvar": (0, (1, 2))}
    for c, method in zip(COLORS, pf.METHODS):
        w = combined[method].weights[ticker]
        ax.plot(w.index, 100 * w, color=c, lw=1.8, linestyle=styles[method],
                label=METHOD_LABEL[method])
    ax.axhline(100 * pf.FAMILY_CAPS["Combined"], color=FT_GREY, lw=0.8, ls="--")
    ax.text(combined["min_cvar"].weights.index[0], 100 * pf.FAMILY_CAPS["Combined"],
            " 10% cap", color=FT_GREY, fontsize=8, va="bottom")
    ax.set_ylabel(f"{ticker} target weight (%)")
    ax.legend(frameon=False, fontsize=9)
    year_axis(ax)
    n_zero = int((combined["min_cvar"].weights[ticker] <= 5e-3).sum())
    ft_header(fig, f"How much {ticker}? The four methods fundamentally disagree",
              f"{ticker} target weight at each monthly rebalance, Combined funds | "
              f"Min-CVaR holds none of it at all {n_zero} rebalances",
              "Source: project data | weights from fund_weights.csv | Min-Variance "
              "(dashed) and Min-CVaR (dotted) coincide at zero for most of the period")
    save_ft(fig, str(FIGURES / "weights_over_time.png"))
    plt.close(fig)

    # 5. Sector sentiment index (required) - 21-day rolling mean, small multiples
    sectors = sorted(index["sector"].unique())
    fig, axes = plt.subplots(2, 5, figsize=(12, 6), sharex=True, sharey=True)
    for i, (ax, sec) in enumerate(zip(axes.flat, sectors)):
        s = (index[index.sector == sec].set_index("trading_day")["sentiment"]
             .rolling(21, min_periods=5).mean())
        ax.plot(s.index, s, color=FT_MAROON, lw=1.0)
        ax.axhline(0, color=FT_GREY, lw=0.6)
        ax.set_title(sec, fontsize=9)
        ax.tick_params(labelsize=7)
        # Label the y axis on the left-hand panel of each row. `sharey` hides the
        # tick labels elsewhere, but with no axis label anywhere the unit lived only
        # in the subtitle - and the brief requires labelled axes on every exhibit.
        if i % 5 == 0:
            ax.set_ylabel("Sentiment (compound)", fontsize=8)
        year_axis(ax)
    # The earlier subtitle promised "gaps = no-headline sector-days" and the figure
    # shows none: each series is indexed on its own observed days and the 21-day
    # rolling mean spans the holes, so the line simply connects across them. Say
    # what the reader can actually see, and put the completeness number in words.
    thin = index.groupby("sector")["sentiment"].size().min()
    n_days = index["trading_day"].nunique()
    ft_header(fig, "News sentiment is persistently positive - except when it matters",
              "Sector sentiment index (finVADER compound, 21-day rolling mean), "
              "equal-weight across tickers",
              f"Source: project data, 2020-01-02 to 2023-12-29 | no-headline "
              f"sector-days carry no row: the thinnest sector plots {thin} of "
              f"{n_days:,} days, and the smoothed line bridges the rest")
    save_ft(fig, str(FIGURES / "sentiment_index.png"))
    plt.close(fig)

    # 6. Fusion before/after (required) - growth of $1 + net-of-cost deltas
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
    base = combined["min_cvar"]
    g0, g1 = base.growth_of_one(), fused_headline.growth_of_one()
    axes[0].plot(g0.index, g0, color=FT_BLUE, lw=1.8, label="Base Min-CVaR")
    axes[0].plot(g1.index, g1, color=FT_MAROON, lw=1.4,
                 label=f"+ sentiment tilt (k={HEADLINE_K:g})")
    axes[0].set_ylabel("Growth of $1")
    axes[0].legend(frameon=False, fontsize=9)
    axes[0].set_title("Growth of $1, gross", fontsize=10)
    year_axis(axes[0])
    x = np.arange(len(before_after))
    axes[1].bar(x - 0.18, before_after["sharpe_delta_gross"], 0.36,
                color=FT_BLUE, label="gross")
    axes[1].bar(x + 0.18, before_after["sharpe_delta_net20bps"], 0.36,
                color=FT_MAROON, label="net 20 bps")
    axes[1].axhline(0, color=FT_GREY, lw=0.8)
    axes[1].set_xticks(x, [METHOD_LABEL[m] for m in pf.METHODS], fontsize=8)
    axes[1].set_ylabel("Sharpe delta (fused - base)")
    axes[1].legend(frameon=False, fontsize=9)
    axes[1].set_title("Sharpe change by method", fontsize=10)
    ft_header(fig, "The naive sentiment tilt barely moves Sharpe - and mostly hurts net",
              f"Combined funds, sentiment-z tilt at k={HEADLINE_K:g}, "
              "before vs after, gross and net of 20 bps per trade",
              "Source: project data | table: fusion_before_after.csv")
    save_ft(fig, str(FIGURES / "fusion_before_after.png"))
    plt.close(fig)

    # 7. Co-crash panel (innovation) - crash-day mean by method, both thresholds
    panel = pd.read_csv(TABLES / "co_crash_panel.csv")
    fig, ax = plt.subplots(figsize=(10, 6))
    sub = panel[panel.fund.str.startswith("Combined")]
    for i, (q, off, color) in enumerate((("q=5%", -0.18, FT_BLUE),
                                         ("q=10%", 0.18, FT_MAROON))):
        s = sub[sub.threshold == q].set_index("fund")
        vals = [100 * s.loc[f"Combined {pf.METHOD_DISPLAY[m]}", "mean_crash"]
                for m in pf.METHODS]
        ax.bar(np.arange(4) + off, vals, 0.36, color=color, label=q)
    ax.set_xticks(range(4), [METHOD_LABEL[m] for m in pf.METHODS])
    ax.set_ylabel("Mean return on joint-crash days (%)")
    ax.legend(frameon=False, fontsize=9)
    # This is the headline exhibit and it was the only figure carrying no sample
    # period. It also needs its n: nine crash days is a materially different claim
    # from twenty-two, and the reader cannot get either from the bars.
    n5, n10 = (int(sub[sub.threshold == q].n_crash_days.iloc[0]) for q in ("q=5%", "q=10%"))
    n_oos = len(combined["min_cvar"].returns)
    ft_header(fig, "On joint-crash days the downside pair loses about half as much",
              "Mean Combined-fund return on days both asset classes hit their worst "
              f"q% | n = {n5} (q=5%), {n10} (q=10%)",
              f"Source: project data | {n_oos} OOS days, 2021-01-04 to 2023-12-29 | "
              "paired bootstrap CIs (2,000 draws): co_crash_bootstrap.csv | "
              "min-CVaR vs min-variance not distinguishable")
    save_ft(fig, str(FIGURES / "co_crash_panel.png"))
    plt.close(fig)

    # 8. Full portfolio weights over time, recommended fund (stacked area) -
    #    the literal reading of the required weights-over-time exhibit; the
    #    NVDA figure above is the across-methods comparison the OUTLINE chose
    rec = combined["min_cvar"]
    w = rec.weights.copy()
    top = w.mean().nlargest(8).index
    stack = w[top].copy()
    stack["other"] = w.drop(columns=top).sum(axis=1)
    fig, ax = plt.subplots(figsize=(10, 6))
    # 9 distinct fills from the 4 FT colours: full tone, then a lighter tint of
    # each (mixed toward the cream), "other" in light grey - unique legend mapping
    from matplotlib.colors import to_rgb
    def tint(c, f=0.55):
        r, g, b = to_rgb(c)
        return (r + (1 - r) * f, g + (1 - g) * f, b + (1 - b) * f)
    palette = (COLORS + [tint(c) for c in COLORS] + ["#CFC5BC"])[:len(stack.columns)]
    ax.stackplot(stack.index, [100 * stack[c] for c in stack.columns],
                 labels=list(stack.columns), colors=palette)
    ax.set_ylabel("Target weight (%)")
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper left")
    year_axis(ax)
    ft_header(fig, "Inside the recommended fund: a broad, capped book",
              "Combined Min-CVaR target weights at each rebalance, top-8 names "
              "by average weight + all others stacked",
              "Source: project data | weights from fund_weights.csv")
    save_ft(fig, str(FIGURES / "weights_stacked_min_cvar.png"))
    plt.close(fig)

    # A ninth figure, `cost_sensitivity.png`, used to live here: net Sharpe across
    # the 0/10/20/50 bps grid plus turnover by method. DELETED 2026-07-30 as
    # redundant, not as a change of mind about the cost model. Every value it drew
    # is a column of `performance_metrics.csv` - `turnover_ann` and the eight
    # `ann_return_*bps`/`sharpe_*bps` columns - which the report prints in full as
    # Table A1, and the strand's three findings are one sentence each (the podium
    # never reorders within a family; EWMA-vs-static breaks even near 20 bps; zero
    # costs is a quantified simplification). The cost model itself is untouched:
    # it is charged inside `oos_backtest` and those columns are still written.
    print(f"  wrote 8 figures to {FIGURES.relative_to(ROOT)}/")


def main():
    for d in (DATA, TABLES, FIGURES):
        d.mkdir(parents=True, exist_ok=True)
    # The raw equity/crypto frames are consumed inside load_stage() to build the
    # combined panel; main() only needs what the later stages take.
    _eq, _cr, news, cal, combined_panel, stats_panel = load_stage()
    panels, results, agg, metrics = funds_stage(combined_panel, stats_panel)
    co_crash_stage(results, agg)
    parameter_study_stage(panels, results)
    scored, index = sentiment_stage(news, cal)
    before_after, fused_headline = fusion_stage(panels, results, scored, cal)
    lexicon_stage(scored, index)
    figures_stage(results, metrics, index, before_after, fused_headline)
    print("\nDone. All outputs under results/. Next: streamlit run streamlit_app.py, "
          "then python scripts/check_handin.py")


if __name__ == "__main__":
    main()
