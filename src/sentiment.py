"""Station 3 - headline sentiment: finVADER scoring and the sector index.

Scores the assembled headline panel from ``src/text_panel.py`` and builds the
standalone sector sentiment index. The rules that are load-bearing here:

  1. RAW TEXT IN. Titles are passed to the analyser exactly as stored - no
     lower-casing, no punctuation stripping, no stopword removal. VADER reads
     capitalisation as emphasis ("SLASHES" scores harder than "slashes"), reads
     "!" as intensity, and treats "not" as a negation flip. Cleaning the text
     first would destroy the signal the model exists to read.
  2. SCORE DISTINCT HEADLINES, NOT ROWS. The same headline is attached to several
     tickers, so the panel has far more rows than unique strings. Scoring the
     distinct set and joining back is the difference between a slow run and a
     tolerable one, and it changes no number.
  3. TWO-STEP SECTOR AGGREGATION. The brief asks for "average ticker-day sentiment
     within each sector (equal-weight the tickers)". That is: mean per ticker-day
     first, THEN an equal-weight mean across tickers. A single flat mean over every
     headline in a sector-day is headline-count-weighted, not ticker-equal-weighted,
     and the two differ materially on this data - one ticker holds >=70% of a
     sector-day's headlines on 9.9% of days.
  4. THE FUSION SIGNAL IS LAGGED. ``fusion_signal`` shifts by at least one trading
     day before returning, so day t's decision can only see sentiment from t-1 or
     earlier. The lag is applied inside this function rather than left to the
     caller, because a forgotten shift is silent look-ahead.

finVADER = VADER's general lexicon plus the SentiBigNomics and Henry finance
lexicons. Report the package versions beside any score (``package_versions()``).
"""
from __future__ import annotations

import functools
from pathlib import Path

import numpy as np
import pandas as pd

# Compound scores live on [-1, +1] where 0.0 is neutral. Note this differs from a
# 0-100 fear-greed style scale: an earlier planning note said to neutral-fill at
# "0.5 / 50", which belongs to that other convention. On the compound scale the
# neutral value is 0.0.
NEUTRAL_SCORE = 0.0

# Forward-fill horizon for the fusion signal, in trading days. Beyond this a stale
# score stops being evidence about today and becomes an assumption.
FFILL_LIMIT = 5

# Minimum lag between a headline's aligned trading day and the day it may inform.
SENTIMENT_LAG = 1

# The scoring cache lives OUTSIDE the project folder, in the user cache directory.
#
# Two constraints have to hold at once and only this location satisfies both:
#   - ``.gitignore`` re-includes everything under ``results/`` via ``!results/**``,
#     which overrides the blanket ``*.parquet`` ignore, so the cache must not go
#     there or it gets committed.
#   - ``scripts/check_handin.py`` scans the FILESYSTEM (``ROOT.rglob("*")``) for any
#     ``.parquet``/``.csv`` outside ``results/`` and fails the hand-in check on it -
#     it does not consult git. So a correctly-gitignored ``cache/`` inside the
#     project still breaks the submission check.
#
# Putting it under the user cache directory keeps runs fast across sessions while
# guaranteeing the hand-in folder stays clean. It is a regenerable build artifact,
# so its absence on a clean checkout is correct behaviour, not a broken pipeline.
CACHE_PATH = (Path.home() / ".cache" / "fins3645_z5594806_projectB"
              / "unique_title_scores.parquet")


# --------------------------------------------------------------------------- #
# 1. The analyser
# --------------------------------------------------------------------------- #
@functools.lru_cache(maxsize=1)
def build_finvader():
    """Build the finVADER analyser ONCE and reuse it.

    The ``finvader`` package exposes a convenience function that rebuilds the whole
    analyser on every call - it re-loads the lexicons and constructs a fresh
    ``SentimentIntensityAnalyzer`` per string. Over ~100k distinct headlines that is
    unusable, so this reproduces the package's own both-lexicons recipe once:

      - load SentiBigNomics (7,295 terms) and scale every value by 0.1, the
        package's own tuning constant for classification accuracy;
      - load Henry (189 terms) unscaled;
      - merge with Henry taking precedence on collisions (``{**sbn, **henry}``);
      - update a base VADER lexicon with the result.

    Cached by ``lru_cache`` so repeated calls in one process are free.
    """
    from finvader import SentimentIntensityAnalyzer, lexicon1, lexicon2

    sentibignomics = {k: v * 0.1 for k, v in lexicon1().items()}
    henry = lexicon2()
    analyser = SentimentIntensityAnalyzer()
    analyser.lexicon.update({**sentibignomics, **henry})
    return analyser


@functools.lru_cache(maxsize=1)
def build_plain_vader():
    """The SAME analyser class as ``build_finvader``, with NO finance lexicon.

    Exists only as the baseline for ``neutrality_comparison``. Using finVADER's own
    ``SentimentIntensityAnalyzer`` rather than a separately-installed VADER is the
    point: it isolates the effect of the merged finance LEXICON, which is the
    choice being justified, instead of confounding it with a different
    implementation of the same algorithm.
    """
    from finvader import SentimentIntensityAnalyzer
    return SentimentIntensityAnalyzer()


def package_versions() -> dict:
    """Model provenance for the methodology paragraph - versions, not just names."""
    import importlib.metadata as md
    return {
        "finvader": md.version("finvader"),
        "vaderSentiment": md.version("vaderSentiment"),
        "merged_lexicon_terms": len(build_finvader().lexicon),
    }


def neutrality_comparison(scored: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """Plain VADER vs finVADER: how many headlines score exactly 0.0 under each.

    This measures the trap the brief names directly - "about half of finance
    headlines score neutral with plain VADER, and many are false neutrals. A
    finance lexicon helps, and a sentiment of zero is not 'no information'." The
    number is what justifies choosing a finance-tuned lexicon at all, so it
    belongs in a saved artifact rather than in prose.

    A compound of exactly 0.0 means no token in the headline appeared in the
    lexicon - not "balanced sentiment". ``rescued`` counts headlines plain VADER
    read as silent that finVADER scores, which is the recovered signal.

    Scored on DISTINCT headlines (the panel repeats each across tickers), so this
    describes the vocabulary rather than the news flow's weighting.
    """
    titles = pd.Index(pd.unique(scored["title"]), name="title")
    fin = (scored.drop_duplicates("title").set_index("title")["compound"]
                 .reindex(titles).to_numpy(dtype=float))

    plain_analyser = build_plain_vader()
    if verbose:
        print(f"  scoring {len(titles):,} distinct headlines with PLAIN VADER "
              f"for the neutrality baseline ...")
    plain = np.array([plain_analyser.polarity_scores(str(t))["compound"]
                      for t in titles], dtype=float)

    plain_neutral, fin_neutral = plain == 0.0, fin == 0.0
    rescued = int((plain_neutral & ~fin_neutral).sum())
    out = pd.DataFrame([{
        "n_distinct_headlines": len(titles),
        "plain_vader_lexicon_terms": len(plain_analyser.lexicon),
        "finvader_lexicon_terms": len(build_finvader().lexicon),
        "n_neutral_plain": int(plain_neutral.sum()),
        "pct_neutral_plain": 100.0 * plain_neutral.mean(),
        "n_neutral_finvader": int(fin_neutral.sum()),
        "pct_neutral_finvader": 100.0 * fin_neutral.mean(),
        "n_rescued_from_neutral": rescued,
        "pct_of_plain_neutrals_rescued":
            100.0 * rescued / plain_neutral.sum() if plain_neutral.any() else np.nan,
        "mean_compound_plain": float(plain.mean()),
        "mean_compound_finvader": float(fin.mean()),
    }])
    if verbose:
        r = out.iloc[0]
        print(f"  neutral share: plain VADER {r.pct_neutral_plain:.2f}% -> "
              f"finVADER {r.pct_neutral_finvader:.2f}%; "
              f"{r.n_rescued_from_neutral:,} headlines rescued "
              f"({r.pct_of_plain_neutrals_rescued:.1f}% of plain's neutrals)")
    return out


# --------------------------------------------------------------------------- #
# 2. Scoring
# --------------------------------------------------------------------------- #
def score_unique_titles(panel: pd.DataFrame, cache_path: Path | str = CACHE_PATH,
                        use_cache: bool = True, verbose: bool = True) -> pd.DataFrame:
    """Score each DISTINCT headline once and cache the result.

    Returns ``title, compound``. The cache is written outside the project folder -
    see ``CACHE_PATH`` for why both the ``.gitignore`` negation and
    ``check_handin.py``'s filesystem scan rule out every in-project location.

    The cache is keyed on the exact title string and is only reused when it covers
    every title in the current panel, so a grown or changed panel triggers a
    rescore rather than silently returning partial results. If the upstream panel
    changes in a way that reuses titles, delete ``CACHE_PATH`` rather than trusting
    a stale file.
    """
    cache_path = Path(cache_path)
    titles = pd.Index(pd.unique(panel["title"]), name="title")

    if use_cache and cache_path.exists():
        cached = pd.read_parquet(cache_path)
        if set(titles) <= set(cached["title"]):
            if verbose:
                print(f"  loaded {len(cached):,} cached headline scores from {cache_path}")
            return cached[cached["title"].isin(titles)].reset_index(drop=True)

    analyser = build_finvader()
    if verbose:
        print(f"  scoring {len(titles):,} distinct headlines "
              f"(panel has {len(panel):,} rows) ...")
    scores = [analyser.polarity_scores(str(t))["compound"] for t in titles]
    out = pd.DataFrame({"title": titles, "compound": scores})

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(cache_path, index=False)
    if verbose:
        print(f"  scored and cached to {cache_path}")
    return out


def score_headlines(panel: pd.DataFrame, verbose: bool = True,
                    **kwargs) -> pd.DataFrame:
    """Attach a finVADER compound score to every row of the headline panel.

    ``panel`` is ``text_panel.assemble_headline_panel`` output: one row per
    headline per ticker, with the raw ``title`` and an aligned ``trading_day``.
    Returns the same rows plus a ``compound`` column.
    """
    scores = score_unique_titles(panel, verbose=verbose, **kwargs)
    out = panel.merge(scores, on="title", how="left")
    if out["compound"].isna().any():
        raise ValueError("some headlines failed to score; delete cache/ and re-run")
    if verbose:
        print(f"  scored panel: {len(out):,} rows, mean compound "
              f"{out['compound'].mean():+.4f}")
    return out


# --------------------------------------------------------------------------- #
# 3. Two-step aggregation
# --------------------------------------------------------------------------- #
def ticker_day_score(scored: pd.DataFrame) -> pd.DataFrame:
    """Step 1: mean headline score per ticker per aligned trading day.

    Returns ``trading_day, ticker, sector, compound, n_headlines``. A ticker-day
    with no headlines simply does not appear - it is NOT neutral-filled here.
    Dropping a silent ticker from its sector's average is defensible on this data:
    even the thinnest sector still averages ~2.84 of 5 tickers active on days when
    the sector has any news, so the equal-weight mean below is usually a real
    average rather than one fabricated from a single voice.

    "Usually" is the honest word. ``min_tickers`` is 1 for nine of the ten sectors,
    so a minority of sector-days DO rest on one ticker - see
    ``pct_days_single_ticker`` in ``coverage_report``, which exists so that floor
    is quotable instead of buried under the mean.
    """
    grouped = scored.groupby(["trading_day", "ticker", "sector"], observed=True)
    out = grouped["compound"].agg(["mean", "size"]).reset_index()
    return out.rename(columns={"mean": "compound", "size": "n_headlines"})


def sector_sentiment_index(scored: pd.DataFrame) -> pd.DataFrame:
    """Step 2: equal-weight mean ACROSS TICKERS of the ticker-day scores.

    This is the brief's construction, and it is deliberately not a single groupby
    over headlines: averaging headlines directly would weight a ticker by how much
    news it happened to generate that day. Verified to matter - one ticker holds
    >=70% of a sector-day's headlines on 9.9% of days.

    A sector-day with no headlines from ANY of its tickers is left out entirely
    rather than neutral-filled. That is rare (0% of days for Tech, at most 6.6% for
    Materials and Real Estate), so the published index stays ~93%+ complete without
    inventing values. The standalone index has no obligation to be defined every
    day - only the fusion signal does, and that is handled separately.

    Returns long format ``trading_day, sector, sentiment, n_tickers``.
    """
    per_ticker = ticker_day_score(scored)
    grouped = per_ticker.groupby(["trading_day", "sector"], observed=True)
    out = grouped["compound"].agg(["mean", "size"]).reset_index()
    out = out.rename(columns={"mean": "sentiment", "size": "n_tickers"})
    return out.sort_values(["trading_day", "sector"]).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 4. The look-ahead-safe fusion signal
# --------------------------------------------------------------------------- #
def fusion_signal(scored: pd.DataFrame, trading_days: pd.DatetimeIndex,
                  ffill_limit: int = FFILL_LIMIT,
                  lag: int = SENTIMENT_LAG) -> pd.DataFrame:
    """Per-ticker daily sentiment, gap-filled and LAGGED, ready to tilt weights.

    Three things happen here that the standalone index deliberately does not do:

      1. Reindex to every trading day. The fusion rule needs a value per ticker per
         day; the published index does not.
      2. Forward-fill each ticker's last score up to ``ffill_limit`` trading days,
         then fall back to ``NEUTRAL_SCORE``. A week-old headline is weak evidence
         about today; beyond that, "no information" is more honest than "stale
         information".
      3. Shift forward by ``lag`` trading days, so a headline aligned to day t is
         first usable for day t+1's decision. Applied here, not left to the caller,
         because a forgotten shift is silent look-ahead.

    Returns a wide frame indexed by trading day, one column per ticker.
    """
    if lag < 1:
        raise ValueError(f"lag must be >= 1 trading day, got {lag}")

    per_ticker = ticker_day_score(scored)
    wide = per_ticker.pivot(index="trading_day", columns="ticker", values="compound")
    wide = wide.reindex(pd.DatetimeIndex(sorted(pd.unique(trading_days))))
    filled = wide.ffill(limit=ffill_limit).fillna(NEUTRAL_SCORE)
    return filled.shift(lag).dropna(how="all")


def sentiment_z(signal: pd.DataFrame, window: int = 252,
                min_periods: int = 63) -> pd.DataFrame:
    """Cross-sectionally comparable score: each ticker's own rolling z-score.

    Raw compound levels are not comparable across tickers - one whose coverage
    skews promotional sits permanently positive. Standardising against each
    ticker's own trailing history asks "is this ticker unusually positive FOR
    ITSELF", which is what a tilt should respond to. The window is trailing only,
    so this adds no look-ahead beyond the lag already applied upstream.
    """
    mean = signal.rolling(window, min_periods=min_periods).mean()
    std = signal.rolling(window, min_periods=min_periods).std()
    return (signal - mean) / std.replace(0.0, np.nan)


# --------------------------------------------------------------------------- #
# 5. Validation and coverage
# --------------------------------------------------------------------------- #
def validate_against_events(index: pd.DataFrame, event_dates: dict,
                            window: int = 3) -> pd.DataFrame:
    """Does the index actually dip around dates already known to be crashes?

    The rubric wants a *validated* index, not merely a computed one. This averages
    the aggregate index (mean across sectors) over a +/- ``window`` day band around
    each event and reports its percentile against the full sample. A low percentile
    means the index recognised the event.

    ``event_dates`` maps a label to a date - use Part A's verified extremes rather
    than dates chosen after seeing the index. Report the result plainly including
    if it is weak: a validation check that half-works is a finding, and claiming
    otherwise would be worse than a negative result.
    """
    daily = index.groupby("trading_day", observed=True)["sentiment"].mean().sort_index()
    rows = []
    for label, date in event_dates.items():
        date = pd.Timestamp(date)
        lo, hi = date - pd.Timedelta(days=window), date + pd.Timedelta(days=window)
        band = daily.loc[(daily.index >= lo) & (daily.index <= hi)]
        if band.empty:
            rows.append({"event": label, "date": date.date(), "n_days": 0,
                         "index_mean": np.nan, "percentile": np.nan,
                         "recognised": False})
            continue
        value = float(band.mean())
        pct = float((daily < value).mean())
        rows.append({"event": label, "date": date.date(), "n_days": len(band),
                     "index_mean": value, "percentile": pct,
                     "recognised": bool(pct < 0.25)})
    return pd.DataFrame(rows)


def coverage_report(index: pd.DataFrame,
                    trading_days: pd.DatetimeIndex) -> pd.DataFrame:
    """Per-sector completeness of the published index - the no-headline-day rule.

    Reports how many trading days each sector has an index value for, and how many
    tickers stood behind it on average. Thin sectors carry noisier index values,
    which belongs in the report as a named limitation rather than a hidden one.

    ``mean_tickers`` is the reassuring statistic and ``min_tickers`` /
    ``pct_days_single_ticker`` are the honest ones: a sector averaging 2.84 active
    tickers still has days that rest on ONE ticker's headlines, and quoting only
    the mean would hide the floor. Saved as a column so the limitation has a
    source rather than being asserted in prose.
    """
    n_days = len(pd.unique(trading_days))
    grouped = index.groupby("sector", observed=True)
    out = pd.DataFrame({
        "days_covered": grouped.size(),
        "mean_tickers": grouped["n_tickers"].mean(),
        "min_tickers": grouped["n_tickers"].min(),
        "n_days_single_ticker": grouped["n_tickers"].apply(lambda s: int((s == 1).sum())),
    }).reset_index()
    out["pct_days_covered"] = 100.0 * out["days_covered"] / n_days
    out["pct_days_single_ticker"] = (100.0 * out["n_days_single_ticker"]
                                    / out["days_covered"])
    return out.sort_values("pct_days_covered").reset_index(drop=True)
