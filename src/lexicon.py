"""Phase 5 (secondary innovation) - the AI-rater + human-review lexicon extension.

Motivated by Part A's finding that 6.12% of headlines carry a finance-lexicon
term with no general-lexicon term (14.7% in Real Estate) - "false neutrals" a
general lexicon reads as score-0. Checked against the ACTUAL merged finVADER
lexicon before proposing anything: many obvious finance terms really are absent,
and the most striking pattern is INFLECTION GAPS - the merged lexicon has
"downgrade" but not "downgrades"/"downgraded", "headwind" but not "headwinds",
"layoff" but not "layoffs". VADER does no stemming, so the plural or participle
form of a covered word silently scores neutral.

The week-8 pattern, carried: the AI agent proposes candidate terms and assigns
several independent ratings each (VADER's -4..+4 scale); two mechanical filters
(rating SD < 2.5, |mean| >= 0.5) drop ambiguous and neutral candidates; a
``human_decision`` column then gates installation - only terms marked "keep" by
the STUDENT enter the lexicon. The AI proposing and the student deciding is the
graded division of labour, so ``extend_terms(ai_only=True)`` is explicitly
labelled provisional and exists only so the pipeline can be demonstrated before
the review is done. The report's before/after must use the reviewed file.

Install mechanism - REVISED from the plan: single-token lexicon updates only.
The plan carried week 8's SPECIAL_CASES/BOOSTER_DICT two-step install for
multi-word phrases, but finvader vendors ``nltk``'s VADER class (checked with
``inspect.getmodule``), which exposes no such module-level dicts - the
vaderSentiment package's do not apply. Multi-word ideas are therefore expressed
as hyphenated single tokens (``rate-cut``, ``going-concern``), which match only
hyphenated usage in headlines; that narrowing is stated rather than hidden.

Build-only module: imports finvader (which imports nltk). The deployed app must
never import this.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

# Filters, per the week-8 pattern the plan locked: disagreement filter first,
# then a dead-zone filter so near-neutral terms add noise rather than signal.
SD_MAX = 2.5
MEAN_MIN = 0.5

# Anchored to the project root, NOT to the current working directory. This was the
# only relative path in the codebase, and a relative one fails silently rather than
# loudly: run from any other directory and `write_review_file` creates a fresh
# all-"pending" file somewhere else, `extend_terms` then finds zero keeps, and
# `run_part_b.py` falls back to PROVISIONAL_ai_only mode - flipping the `mode`
# column the report cites as "human-reviewed" while every installed term stays the
# same. A wrong provenance label is worse than a crash, so remove the possibility.
REVIEW_PATH = (Path(__file__).resolve().parent.parent
               / "results" / "tables" / "lexicon_candidates.csv")

# ---------------------------------------------------------------------------- #
# AI-proposed candidates. Five ratings per term on VADER's -4..+4 scale, assigned
# by the AI agent (this is the disclosed AI step). Every term was checked ABSENT
# from the 13,324-term merged finVADER lexicon before being proposed - proposing
# a term the lexicon already covers would only overwrite a calibrated value.
# Deliberately includes ambiguous terms (short-squeeze) and near-neutral terms
# (margin, margins) so the filters visibly do their job in the review file.
# ---------------------------------------------------------------------------- #
_CANDIDATES: list[tuple[str, tuple[int, int, int, int, int], str]] = [
    # inflection gaps: base form IS in the lexicon, this form is not
    ("downgrades",     (-2, -3, -2, -2, -2), "plural of covered 'downgrade'"),
    ("downgraded",     (-2, -3, -2, -3, -2), "participle of covered 'downgrade'"),
    ("upgraded",       (2, 3, 2, 2, 2),      "participle of covered 'upgrade'"),
    ("headwinds",      (-2, -2, -1, -2, -2), "plural of covered 'headwind'"),
    ("tailwind",       (2, 1, 2, 2, 1),      "covered 'tailwinds' missing singular? reverse gap"),
    ("tailwinds",      (2, 2, 1, 2, 2),      "positive outlook idiom"),
    ("layoffs",        (-3, -2, -3, -2, -3), "plural of covered 'layoff'"),
    ("defaults",       (-3, -2, -3, -3, -2), "plural of covered 'default'"),
    ("buybacks",       (2, 1, 2, 2, 1),      "plural of covered 'buyback'"),
    ("recalls",        (-2, -2, -2, -1, -2), "plural of covered 'recall'"),
    ("probes",         (-2, -1, -2, -2, -2), "plural of covered 'probe'"),
    ("halted",         (-2, -1, -2, -2, -1), "participle of covered 'halt'"),
    ("impaired",       (-2, -2, -2, -1, -2), "participle; writedown context"),
    ("outperformed",   (2, 3, 2, 2, 2),      "past of covered 'outperform'"),
    ("underperformed", (-2, -3, -2, -2, -2), "past of covered 'underperform'"),
    # genuinely missing finance terms
    ("restructuring",  (-1, -2, -1, -1, -1), "distress signal, mildly negative"),
    ("delisting",      (-3, -3, -2, -3, -3), "exchange removal"),
    ("delisted",       (-3, -3, -3, -2, -3), "exchange removal, done"),
    ("oversold",       (1, 2, 1, 0, 1),      "technical: bounce expected"),
    ("overvalued",     (-2, -2, -1, -2, -2), "valuation warning"),
    ("dilutive",       (-2, -1, -2, -2, -1), "shareholder dilution"),
    ("breakout",       (2, 2, 3, 2, 2),      "technical: bullish move"),
    ("moat",           (2, 1, 2, 1, 2),      "durable competitive advantage"),
    # multi-word ideas as hyphenated tokens (match hyphenated usage only)
    ("write-down",     (-2, -3, -2, -2, -2), "asset value cut"),
    ("going-concern",  (-3, -3, -4, -3, -3), "auditor doubt on survival"),
    ("rate-cut",       (1, 2, 1, 1, 2),      "easing, risk-asset positive"),
    ("rate-hike",      (-1, -2, -1, -1, -2), "tightening"),
    ("profit-taking",  (-1, -1, 0, -1, -1),  "selling into strength"),
    # deliberately ambiguous / neutral - the filters should catch these
    ("short-squeeze",  (3, -2, 2, -3, 1),    "direction depends on your book"),
    ("stress-test",    (0, -1, 0, -1, 0),    "regulatory routine, mildly negative"),
    ("margin",         (0, 1, 0, -1, 0),     "not sentiment-bearing alone"),
    ("margins",        (1, 0, 0, -1, 0),     "not sentiment-bearing alone"),
]


def propose_candidates() -> pd.DataFrame:
    """The AI-rater table: term, five ratings, mean/SD, filter verdicts.

    Adds ``passes_filters`` (SD < 2.5 and |mean| >= 0.5) and a ``human_decision``
    column initialised to ``"pending"`` - the student's column, not the AI's.
    """
    rows = []
    for term, ratings, rationale in _CANDIDATES:
        r = np.array(ratings, dtype=float)
        rows.append({"term": term, **{f"r{i+1}": v for i, v in enumerate(ratings)},
                     "mean": r.mean(), "sd": r.std(ddof=1),
                     "rationale": rationale})
    df = pd.DataFrame(rows)
    df["passes_filters"] = (df["sd"] < SD_MAX) & (df["mean"].abs() >= MEAN_MIN)
    df["human_decision"] = "pending"
    return df


def verify_absent(df: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """Drop any candidate already in the merged finVADER lexicon.

    Run at build time so the claim "these terms are absent" is checked against
    the installed lexicon, not remembered from the session that proposed them.
    """
    from src.sentiment import build_finvader
    lex = build_finvader().lexicon
    present = df["term"].str.lower().isin(lex)
    if verbose and present.any():
        print(f"  dropping {int(present.sum())} candidate(s) already in the "
              f"lexicon: {sorted(df.loc[present, 'term'])}")
    return df[~present].reset_index(drop=True)


def write_review_file(df: pd.DataFrame, path: Path | str = REVIEW_PATH,
                      verbose: bool = True) -> Path:
    """Write the candidates for human review - NEVER overwriting an existing file.

    Once the student has edited ``human_decision`` (keep / drop), a re-run must
    not clobber those decisions; if the file exists it is left alone.
    """
    path = Path(path)
    if path.exists():
        if verbose:
            print(f"  review file already exists, not overwriting: {path}")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    if verbose:
        print(f"  wrote {len(df)} candidates for review: {path}")
    return path


def extend_terms(path: Path | str = REVIEW_PATH, ai_only: bool = False,
                 verbose: bool = True) -> dict[str, float]:
    """The terms to install: ``{term: mean rating}``.

    Default mode requires the human review: only rows whose ``human_decision`` is
    ``"keep"`` AND which pass the mechanical filters install. ``ai_only=True`` is
    the PROVISIONAL mode - filter-passing rows regardless of review - for
    demonstrating the pipeline before the review is done; anything built from it
    must be labelled provisional and rebuilt after review.
    """
    df = pd.read_csv(path)
    if ai_only:
        kept = df[df["passes_filters"]]
        label = "PROVISIONAL (ai_only - pending human review)"
    else:
        kept = df[df["passes_filters"]
                  & (df["human_decision"].str.strip().str.lower() == "keep")]
        label = "human-reviewed"
    if verbose:
        print(f"  {len(kept)} of {len(df)} candidates install ({label})")
    return dict(zip(kept["term"].str.lower(), kept["mean"].astype(float)))


# --------------------------------------------------------------------------- #
# Rescoring with the extension
# --------------------------------------------------------------------------- #
def build_extended_finvader(terms: dict[str, float]):
    """A FRESH finVADER analyser with the approved terms added.

    Deliberately does not touch ``sentiment.build_finvader``'s cached analyser -
    the base and extended analysers must coexist for the before/after comparison.
    """
    from finvader import SentimentIntensityAnalyzer, lexicon1, lexicon2
    analyser = SentimentIntensityAnalyzer()
    analyser.lexicon.update({k: v * 0.1 for k, v in lexicon1().items()})
    analyser.lexicon.update(lexicon2())
    analyser.lexicon.update(terms)
    return analyser


def headlines_containing(titles: pd.Index, terms: dict[str, float]) -> pd.Index:
    """Distinct headlines that contain at least one installed term, whole-word.

    CONTAINING a term is not the same as CHANGING score, and the two counts differ
    (a term can appear in a headline whose compound score is unmoved once VADER's
    normalisation and any offsetting valence are applied). Both are reported, from
    this one definition, because quoting one under the other's label is exactly the
    kind of wrong-object slip this project has already had to catch once.
    """
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(t) for t in sorted(terms)) + r")\b",
        flags=re.IGNORECASE)
    return pd.Index([t for t in titles if pattern.search(str(t))])


def rescore_with_extension(scored: pd.DataFrame, terms: dict[str, float],
                           verbose: bool = True) -> pd.DataFrame:
    """Re-score ONLY the headlines that contain an approved term.

    A headline without any new term cannot change score, so the extended panel is
    the base panel with a patched ``compound`` for the affected titles - far
    cheaper than a full 105k-headline rescore, and exactly equal to one.
    """
    titles = pd.Index(pd.unique(scored["title"]))
    affected = headlines_containing(titles, terms)
    if verbose:
        print(f"  {len(affected):,} of {len(titles):,} distinct headlines "
              f"({len(affected) / len(titles):.2%}) contain an approved term")

    analyser = build_extended_finvader(terms)
    new_scores = {t: analyser.polarity_scores(str(t))["compound"] for t in affected}
    out = scored.copy()
    mask = out["title"].isin(affected)
    out.loc[mask, "compound"] = out.loc[mask, "title"].map(new_scores)
    return out


def before_after(scored_base: pd.DataFrame, scored_ext: pd.DataFrame,
                 terms: dict[str, float]) -> pd.DataFrame:
    """The lexicon extension's evidence table, on distinct headlines.

    The headline number is the FALSE-NEUTRAL FIX: headlines the base lexicon
    scored exactly 0.0 that now carry a nonzero score - the precise failure mode
    Part A's 6.12% finding motivated this extension to repair.
    """
    base = scored_base.drop_duplicates("title")[["title", "compound"]] \
                      .rename(columns={"compound": "before"})
    ext = scored_ext.drop_duplicates("title")[["title", "compound"]] \
                    .rename(columns={"compound": "after"})
    m = base.merge(ext, on="title")
    changed = m[m["before"] != m["after"]]
    false_neutral_fixed = changed[changed["before"] == 0.0]
    containing = headlines_containing(pd.Index(m["title"]), terms)
    return pd.DataFrame([{
        "n_terms_installed": len(terms),
        "n_distinct_headlines": len(m),
        "n_headlines_containing_term": len(containing),
        "pct_headlines_containing_term": 100.0 * len(containing) / len(m),
        "n_scores_changed": len(changed),
        "pct_scores_changed": 100.0 * len(changed) / len(m),
        "n_false_neutrals_fixed": len(false_neutral_fixed),
        "pct_false_neutrals_fixed": 100.0 * len(false_neutral_fixed) / len(m),
        "mean_abs_change_when_changed":
            float((changed["after"] - changed["before"]).abs().mean())
            if len(changed) else 0.0,
    }])
