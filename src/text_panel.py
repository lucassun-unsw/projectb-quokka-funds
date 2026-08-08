"""Station 2 - text assembly: the daily headline panel and vocabulary counts.

Ported from the verified z5594806_projectA/src/text_panel.py, unchanged. This
module assembles the news; it does NOT score it. The rules from the brief
enforced here:

  - Trading-day alignment. Every headline maps to the same day if that day trades,
    else the NEXT trading day - holidays included, not only weekends.
  - Raw text kept. The stored ``title`` is never lower-cased, stripped, or
    de-punctuated; VADER/finVADER need casing and punctuation in ``src/sentiment.py``.
    Tokenising for the vocabulary counts and the term-frequency figure is done on a
    throwaway copy and never overwrites the panel text.
  - Counts only, no scoring. The vocabulary table counts how many headlines carry a
    sentiment-bearing term. It assigns no polarity and builds no index - that is
    ``src/sentiment.py``.

The "lexicon gap" column is a demoted flourish carried from Part A: it counts
headlines that carry a finance-specific sentiment term a general opinion lexicon
misses, motivating the Part B lexicon extension (`OUTLINE.md`'s secondary
innovation). The gap set is computed at run time as FINANCE minus GENERAL, so the
"general list misses it" claim is verified from the two lists, not asserted.

Every function is importable and returns a value; none write to ``results/``.
"""
from __future__ import annotations

import re
from collections import Counter

import pandas as pd

# --------------------------------------------------------------------------- #
# Lexicons (membership-count only - NO scores, NO polarity)
# --------------------------------------------------------------------------- #
# Representative subset of a general opinion lexicon (Hu & Liu / VADER style). This
# is an illustrative list, not the full lexicon: the report must say so. It exists
# to (a) count sentiment-bearing headlines and (b) define what "general" covers so
# the finance gap below is the set of finance terms this list omits.
GENERAL_SENTIMENT_TERMS = frozenset({
    # positive
    "good", "great", "best", "strong", "strength", "gain", "gains", "gaining",
    "win", "wins", "winning", "boost", "boosts", "rise", "rises", "rising",
    "surge", "surges", "soar", "soars", "rally", "rallies", "positive", "profit",
    "profits", "success", "successful", "benefit", "benefits", "improve",
    "improved", "improves", "bullish", "optimism", "optimistic", "upbeat",
    "record", "high", "higher", "top", "beat", "beats", "outperform", "growth",
    # negative
    "bad", "worst", "weak", "weakness", "loss", "losses", "losing", "fall",
    "falls", "falling", "drop", "drops", "dropping", "decline", "declines",
    "plunge", "plunges", "slump", "slumps", "tumble", "tumbles", "crash",
    "crashes", "negative", "fear", "fears", "worry", "worries", "concern",
    "concerns", "risk", "risks", "risky", "poor", "fail", "fails", "failure",
    "cut", "cuts", "cutting", "low", "lower", "bearish", "pessimism", "warn",
    "warns", "warning", "trouble", "crisis", "slowdown", "sell", "selloff",
})

# Finance-specific sentiment-bearing terms characteristic of the Loughran-McDonald
# financial dictionary. Also an illustrative subset. The gap set actually used is
# FINANCE_SENTIMENT_TERMS minus GENERAL_SENTIMENT_TERMS, computed at run time.
FINANCE_SENTIMENT_TERMS = frozenset({
    "litigation", "lawsuit", "lawsuits", "litigate", "downgrade", "downgrades",
    "upgrade", "upgrades", "guidance", "miss", "misses", "missed", "default",
    "defaults", "restructuring", "restructure", "bankruptcy", "bankrupt",
    "insolvency", "insolvent", "writedown", "impairment", "impaired", "dilution",
    "dilutive", "buyback", "buybacks", "dividend", "dividends", "overweight",
    "underweight", "underperform", "halt", "halts", "halted", "recall", "recalls",
    "subpoena", "probe", "probes", "investigation", "delisting", "delisted",
    "restatement", "deficit", "shortfall", "headwind", "headwinds", "tailwind",
    "tailwinds", "downside", "upside", "volatility", "volatile", "guidance",
    "distress", "distressed", "downturn", "layoffs", "layoff", "recession",
    "overvalued", "undervalued", "oversold", "overbought", "breakout", "breakdown",
})

# Compact English stopword list, used only to rank the term-frequency figure.
STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "if", "of", "to", "in", "on", "for",
    "with", "at", "by", "from", "as", "is", "are", "was", "were", "be", "been",
    "it", "its", "this", "that", "these", "those", "will", "would", "can",
    "could", "has", "have", "had", "do", "does", "did", "not", "no", "up", "down",
    "out", "over", "after", "before", "into", "about", "than", "then", "s", "vs",
    "amp", "why", "how", "what", "when", "which", "who", "you", "your", "his",
    "her", "their", "our", "we", "they", "he", "she", "i", "new", "more", "most",
    "amid", "says", "say", "said", "could", "should", "may", "might", "one", "two",
})

_TOKEN_RE = re.compile(r"[a-z]+")


def _tokens(title: str) -> list[str]:
    """Lower-case alpha tokens from a title - throwaway copy for counting only.

    The panel's stored ``title`` is never mutated by this; the raw text survives
    for ``src/sentiment.py`` scoring.
    """
    return _TOKEN_RE.findall(str(title).lower())


# --------------------------------------------------------------------------- #
# 1. Trading-day alignment + panel assembly
# --------------------------------------------------------------------------- #
def align_to_trading_day(headlines: pd.DataFrame,
                         trading_days: pd.DatetimeIndex) -> pd.DataFrame:
    """Add a ``trading_day`` column mapping each headline to its usable trading day.

    A headline on a trading day maps to that day; a headline on any non-trading day
    (weekend OR holiday) maps forward to the next trading day. Implemented with a
    forward ``merge_asof``: it finds the smallest trading day >= the headline date.
    Headlines after the last in-sample trading day have no forward match and get
    ``NaT`` (the caller drops them and reports the count). Both date columns must be
    tz-naive (``etl.load_clean_news`` already normalises the news timezone).
    """
    # merge_asof requires identical datetime resolution on both keys; the news dates
    # are datetime64[us] and the price dates datetime64[s], so pin both to ns.
    td_index = pd.DatetimeIndex(sorted(pd.unique(trading_days))).astype("datetime64[ns]")
    td = pd.DataFrame({"trading_day": td_index})
    h = headlines.sort_values("date").reset_index(drop=True)
    h["_key"] = h["date"].astype("datetime64[ns]")
    merged = pd.merge_asof(h, td, left_on="_key", right_on="trading_day",
                           direction="forward")
    return merged.drop(columns="_key")


def assemble_headline_panel(headlines: pd.DataFrame,
                            trading_days: pd.DatetimeIndex) -> pd.DataFrame:
    """Daily headline panel per ticker and sector, aligned to the trading calendar.

    One row per headline (not aggregated), so ``src/sentiment.py`` can group by
    ``trading_day`` and score. Columns: ``date`` (original publish date),
    ``trading_day`` (aligned), ``ticker``, ``sector``, ``title`` (raw, untouched).
    Headlines with no forward trading day (a handful on the final weekend) are
    dropped. Sorted by trading_day then ticker.

    Expected shape (Part A, same source data): ~146,830 rows over 10 sectors, one
    aligned trading day each.
    """
    aligned = align_to_trading_day(headlines, trading_days)
    aligned = aligned.dropna(subset=["trading_day"])
    cols = ["date", "trading_day", "ticker", "sector", "title"]
    return (aligned[cols].sort_values(["trading_day", "ticker", "date"])
                         .reset_index(drop=True))


# --------------------------------------------------------------------------- #
# 2. Article flow over time (data for the articles-over-time figure)
# --------------------------------------------------------------------------- #
def articles_over_time(panel: pd.DataFrame, freq: str = "ME") -> pd.DataFrame:
    """Headline counts per calendar period, total and by sector.

    Counts on the aligned ``trading_day``. Default ``freq="ME"`` is month-end.
    Returns a period-indexed frame with one column per sector plus ``total``. Feeds
    the articles-over-time figure; spikes flag heavy news days (e.g. the 2020 crash).
    """
    g = panel.set_index("trading_day")
    by_sector = (g.groupby([pd.Grouper(freq=freq), "sector"]).size()
                  .unstack("sector").fillna(0).astype(int))
    by_sector["total"] = by_sector.sum(axis=1)
    return by_sector


# --------------------------------------------------------------------------- #
# 3. Vocabulary counts + lexicon gap
# --------------------------------------------------------------------------- #
def _finance_gap_terms() -> frozenset:
    """Finance sentiment terms the general lexicon omits (FINANCE minus GENERAL)."""
    return frozenset(FINANCE_SENTIMENT_TERMS - GENERAL_SENTIMENT_TERMS)


def vocab_counts(headlines: pd.DataFrame) -> pd.DataFrame:
    """Per-sector headline vocabulary counts, plus the demoted lexicon-gap column.

    For each headline, membership booleans (no scores): does it contain >=1 general
    sentiment term, >=1 finance term the general lexicon misses, and the "gap-only"
    case of a finance term with NO general term. Aggregated per sector with a TOTAL
    row. Columns: ``sector, n_headlines, n_general_sentiment, pct_general,
    n_finance_gap, pct_finance_gap, n_finance_gap_only, pct_finance_gap_only``.

    ``pct_finance_gap_only`` motivates the Part B lexicon extension: headlines a
    general lexicon would read as neutral because their only sentiment cue is a
    finance term it does not know (a finance-gap term and no general term). This
    counts vocabulary coverage; it assigns no sentiment.
    """
    gap = _finance_gap_terms()
    df = headlines[["sector", "title"]].copy()
    toks = df["title"].map(lambda t: set(_tokens(t)))
    df["has_general"] = toks.map(lambda s: bool(s & GENERAL_SENTIMENT_TERMS))
    df["has_finance_gap"] = toks.map(lambda s: bool(s & gap))
    # false neutrals: a finance-gap term but NO general term, so a general lexicon
    # reads the headline as neutral - the exact set the Part B lexicon extension targets
    df["has_finance_gap_only"] = df["has_finance_gap"] & ~df["has_general"]

    grp = df.groupby("sector")
    out = pd.DataFrame({
        "n_headlines": grp.size(),
        "n_general_sentiment": grp["has_general"].sum(),
        "n_finance_gap": grp["has_finance_gap"].sum(),
        "n_finance_gap_only": grp["has_finance_gap_only"].sum(),
    }).reset_index()

    total = pd.DataFrame([{
        "sector": "TOTAL",
        "n_headlines": len(df),
        "n_general_sentiment": int(df["has_general"].sum()),
        "n_finance_gap": int(df["has_finance_gap"].sum()),
        "n_finance_gap_only": int(df["has_finance_gap_only"].sum()),
    }])
    out = pd.concat([out.sort_values("sector"), total], ignore_index=True)
    out["pct_general"] = (100 * out["n_general_sentiment"] / out["n_headlines"]).round(2)
    out["pct_finance_gap"] = (100 * out["n_finance_gap"] / out["n_headlines"]).round(2)
    out["pct_finance_gap_only"] = (100 * out["n_finance_gap_only"] / out["n_headlines"]).round(2)
    return out[["sector", "n_headlines", "n_general_sentiment", "pct_general",
                "n_finance_gap", "pct_finance_gap",
                "n_finance_gap_only", "pct_finance_gap_only"]]


# --------------------------------------------------------------------------- #
# 4. Top terms (data for the term-frequency figure)
# --------------------------------------------------------------------------- #
def top_terms(headlines: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Most frequent non-stopword tokens across all headlines.

    Tokenises a lower-cased throwaway copy (raw titles untouched), drops stopwords
    and tokens of length <= 2, and returns the top ``n`` terms as ``term, count``.
    Feeds the term-frequency figure - what the news is about, not its sentiment.
    """
    counter: Counter = Counter()
    for title in headlines["title"]:
        counter.update(w for w in _tokens(title)
                       if len(w) > 2 and w not in STOPWORDS)
    return pd.DataFrame(counter.most_common(n), columns=["term", "count"])
