# Project B — Build Plan & Status (z5594806)

Planning aid only (the report source is `report.docx`, submitted as
`report.pdf`). Part B = Funds, Sentiment & App (Stations 3-4), 50% of the
course, due Friday Week 11. Companion docs: the graded AI trail in
`ai/AI_NOTES.md` + `ai/prompt_log_01..14` (session history lives there, not
here). The frozen Part A facts and the per-paragraph writing plan that seeded the
report are folded into this file's Locked decisions and the finished
`report.docx`.

---

## Where this stands (hand-in day)

Complete and verified end to end. The build, every artifact in `results/`, and
the six-section report prose in `report.docx` are done. The project is its own
public repo with the app live (URLs below); both URLs are in `report.docx`
(Section 5 + Figure 9 caption) and `README.md`. A whole-document audit verified
every one of the 14 report tables cell-by-cell against `results/` and every
quantitative prose claim against the CSVs (NVDA 30-held/22-capped/0-for-CVaR;
holdings ranges 13-16 / 13-21 / 12-18 / 53-60 at the 0.5% threshold; 5 names at
cap on 2023-12-05; the four dropped lexicon terms; 19 OMML equations).

Figure 9 (Appendix B) is the *Fact sheet* tab of the live app for the
recommended Combined Min-CVaR fund, matching its caption. `report.pdf` was
field-updated (F9), TOC-refreshed, and re-exported from Word; the exported PDF
shows sequential Figures 1-9 / Tables 1-14 with no leftover markers.
`scripts/check_handin.py` passes (24 checks); no stray `Screenshot*.png`,
`__pycache__`, or `.ruff_cache` in the folder. Remaining: commit + push the
final `report.docx`/`report.pdf`, zip `z5594806_projectB`, submit on Moodle
with the two links.

### Running the app

```bash
cd fins2026/z5594806_projectB
../../.venv/bin/python -m streamlit run streamlit_app.py     # macOS
# Windows:  ..\..\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Streamlit prints the URL it picked and opens a browser. It uses **8501** by
default and steps to the next free port if that one is taken, so read the URL
off the terminal rather than assuming a number. Add `--server.port 8580` to pin
one.

- **Local:** run the command above and use the URL it prints. A port is not a
  deployment: nothing listens after the process exits, and the address means
  nothing on another computer.
- **Live URL:**
  https://projectb-quokka-funds-ihndbhpfsgr2aqfwey6ees.streamlit.app
- **Public repo:** https://github.com/lucassun-unsw/projectb-quokka-funds
  (branch `main`, `streamlit_app.py` at root). Both links are already pasted
  into `report.docx` and `README.md`.

**Deployment record (was "Phase 10 gotcha").** Done as planned: this folder
was `git init`-ed as its **own independent repo** (never committed into the
course repo) and pushed public; Streamlit Cloud deployed from it. Two things
learned during deploy:
- Streamlit Cloud auto-added a `.devcontainer/devcontainer.json` commit
  (Codespaces support) — harmless, kept.
- **`requirements.txt` now pins `streamlit==1.57.0`.** The unpinned cloud
  build resolved a different Streamlit whose tab DOM does not match
  `app_theme.py`'s pill-tab CSS (`button[data-baseweb="tab"]`), so the live
  app rendered plain underline tabs. Pinning the locally-audited version fixed
  it. Do not unpin; if Streamlit is ever upgraded, re-audit the app visually.
- `Screenshot*.png` is now gitignored — screenshots dropped into this folder
  must never reach the submission repo or the zip.

**Open loose ends** (all small):
- Citations: **closed**. The four convention citations were dropped rather
  than verified — each is now an unattributed convention justified by this
  project's own numbers (see the claim ledger). Do not reintroduce a named
  source without verifying its metadata.
- The scoring cache lives at `~/.cache/fins3645_z5594806_projectB/` (outside
  the project — both the `.gitignore` `!results/**` negation and
  `check_handin.py`'s filesystem scan rule out every in-project location).
  On a clean machine it regenerates deterministically (slow, once).
- `check_handin.py` greps literal strings: no `.parquet`/`.csv` outside
  `results/`, and no literal "nltk" text in `streamlit_app.py` — keep both
  true when editing.
- `ruff.toml` (added Phase 8c) makes `ruff check .` pass with **no flags**, so
  the result is the same for a marker who clones only this folder. It carries two
  narrow per-file ignores — `src/data_access.py` (provided, must stay identical
  to Part A's) and `src/etl.py` (frozen) — with the reason written beside each.
  Anything other than those exact rules in those exact files still fails. Do not
  widen them to silence a new finding; fix the finding.
- Percentages in `results/` are stored as **fractions**. Any `column_config`
  format string containing `%%` must be fed a column already scaled to 0–100
  (`as_pct()` in `streamlit_app.py`) — this is what the Phase 8c bug was, and
  `tests/test_app.py` now asserts on the displayed value, not the stored one.

Foundation note: `etl.py` / `features.py` / `text_panel.py` / `ft_style.py` /
`dependence.py` are the verified Part A port and are FROZEN — if any task
seems to require changing them, stop and flag it. The frozen Part A facts and
the nine correctness rules they enforce are in this file's Locked decisions and
in `CLAUDE.md`.

---

## Locked decisions (all data-verified; every number re-checked in Phase 8)

| Decision | Choice |
|---|---|
| Required funds | Combined equity+crypto plus Equity-Only and Crypto-Only, × 4 methods each = **12 funds**. Naming convention (CSVs, fact sheets, app picker all key off it): **"Combined Max-Sharpe", "Equity-Only Risk Parity", "Crypto-Only Min-CVaR"** etc. |
| Funds innovation (primary) | **Min-CVaR fund** — Rockafellar–Uryasev historical-scenario LP (`scipy linprog`, HiGHS), a genuine tail objective, not a variance proxy. Operationalises Part A's finding that variance-based risk understates joint downside (joint worst-5% 25.9% vs 15.5% Gaussian; 1% ES −10.8% vs −7.1%). |
| Min-CVaR β | **0.95 headline, 0.90 robustness.** Argued from scenario counts, not from a named regime (citations dropped — see the ledger): a 97.5% level leaves only 6.3 tail scenarios at T=252 (0.99 leaves 2.5) — too few to average a tail over; 0.95 leaves 12.6 at the first window, rising to **49.4 at the last** (T=987). Name the constraint in the report. **Corrected**: "50.3" is the count on the FULL panel (T=1,005), not at the last estimation window — the wrong-object slip this ledger exists to prevent. |
| Evaluation innovation (the headline) | **Co-crash stress-test panel + paired bootstrap.** Days where equity AND crypto aggregates are both in their own worst q%; report **both q=5% and q=10%** (q=5% has only 9 OOS days, 8 of them in one year — single-episode; q=10% gives 22 spread across the three OOS years). Bootstrap (2,000 paired draws) because 9–22 observations make point estimates unquotable; never bootstrap the worst single day (minima invalid — the upper CI bound equals the point estimate). |
| Cost innovation (brief-named) | **Turnover/transaction-cost model built into `oos_backtest`**: cost on two-way turnover per rebalance, grid 0/10/20/50 bps, first rebalance charged as full entry. Findings: podium never reorders (RP > CVaR > MV > MS at every level); EWMA-vs-static breakeven ≈ 20 bps. |
| Risk estimate | **EWMA covariance, span 252** (λ = 0.9921, half-life 87 trading days; geometric weights over ALL history — a decay rate, not a window; unrelated to the 252-day burn-in despite the shared number). Justified by volatility clustering: equity ACF(r²) = +0.49 at lag 1 vs ACF(r) = −0.18. Three alternatives tested and rejected, all now saved in **`parameter_study.csv`** (Combined Min-Variance, the fund whose only input is the covariance): RiskMetrics λ=0.94/span 32 (13.69% vs 12.45% realised vol, **+1.23pp**, and 1,141%/yr turnover; N_eff/p = 0.53 at 60 assets); span 126 (worse vol at 12.58% AND **496%/yr** turnover); static full-window (12.79%, beaten on vol in all three OOS years: +0.29/+0.12/+0.72pp). Chosen over per-asset GARCH for robustness inside the walk-forward loop. Computed manually — equals `df.ewm(span, adjust=True).cov(bias=True)` exactly; pandas' default `bias=False` differs by **0.40%** on the full panel (the Bessel-style factor `1/(1−Σw²)`; 0.48% at T=300) and is ~4000× slower. **Corrected**: this row said 6.75%, which is the factor at a span of roughly 17 — a short-span number that migrated into the span-252 row. Do not quote 6.75%. |
| EWMA claim boundary | **Claim the volatility reduction only** (holds every year). The return edge flips sign (+0.63/+2.19/−1.73pp) — never claim it. EWMA costs **263%/yr** two-way turnover vs static's **30%**; free only under zero costs — state with the ~20 bps breakeven. All of this is now in `parameter_study.csv`. |
| Estimation universe | **All 60 assets**; the long-only cap and objective do the selecting — holdings are an output (from `fund_weights.csv` at the 0.5% threshold: Min-CVaR 13–16 names, Min-Variance 13–21, Max-Sharpe 12–18, Risk Parity all 60 by construction; an earlier "4–16" came from a pre-lock exploratory run and is superseded). Pre-filtering tested and rejected (12.65–13.72% vol vs 12.45%). The brief is silent here; an owned design choice. |
| Weight cap | **10% for Combined/Equity-Only (the retail-fund single-issuer convention, stated unattributed); 25% for Crypto-Only** — 10 assets × 10% = 1.00 saturates exactly and collapses all four methods into one equal-weight fund (caught in verification; `check_cap_feasible` now hard-blocks n·cap ≤ 1). 25% enforces ≥4 holdings and restores full method separation. |
| Shrinkage | **Not used, tested and reported**: Ledoit–Wolf-style shrinkage cuts the condition number 227× at span 32 but changes realised vol only 0.05pp at span 252 — a methodological finding, not an omission. **Quote these two with their settings, because neither is in a CSV and both are setting-specific.** The 227× is at **shrinkage intensity δ = 0.2, median across the 36 Combined windows** (δ=0.1 gives 102×, δ=0.5 gives 886×). The span-252 condition number is **850 at the FIRST rebalance window (T=252)**; the median across windows is 1.4e3 and the full-panel value is 658. Either state the window and δ, or drop the numbers and keep the qualitative finding. |
| Sentiment model | **finVADER** (VADER + SentiBigNomics 7,295 terms ×0.1 + Henry 189; merged lexicon 13,324 terms; versions finvader 1.0.2 / vaderSentiment 3.3.2 — state beside scores). Analyser built ONCE (`sentiment.build_finvader`; the package's own convenience function rebuilds per call — unusable at 105k headlines). Raw text in, always. |
| Sector index construction | **Two-step, per the brief's wording**: ticker-day mean first, THEN equal-weight across tickers. Not a flat headline mean (headline-count-weighted): one ticker holds ≥70% of a sector-day's headlines on 9.9% of days; worked example Tech 2020-03-12: two-step +0.0627 vs flat +0.0881. |
| No-headline-day rule (three levels) | **Ticker-day** silent → drop from that day's sector mean (thinnest sector still averages 2.84/5 active tickers on news days). **Sector-day** all-silent → row undefined, never invented (Materials/RealEstate 6.6% of days; index ≥93.4% complete). **Fusion signal only** → forward-fill ≤5 trading days then neutral **0.0** (VADER compound scale; an early draft said "0.5/50" — that is the 0–100 fear-greed convention, corrected). |
| Sentiment lag | **≥1 trading day, always**, applied INSIDE `sentiment.fusion_signal` (rejects lag=0 with an error). Machine-verified: signal[t] = raw[t−1] exactly. Day-t decisions see day t−1 news or older. |
| Fusion rule | Per-ticker sentiment-z tilt on the equity sleeve only: `tilt = 1 + k·clip(z, ±2)`, renormalised to the sleeve's weight, then re-capped. z = each ticker's own trailing-252-day standardisation. **k = 0.10 confirmed by the student** (bounds any tilt to ±20% of a name's weight); grid {0…0.5} reported, k=0 reproduces the base to 0.00e+00 (wiring check). **Measured verdict: negligible gross, ≈zero-to-negative net of 20 bps.** An explained naive result — the brief accepts it; not tuned after the fact. |
| Lexicon extension (secondary) | AI proposed + rated 32 candidates (each verified ABSENT from the live merged lexicon before proposing); filters SD<2.5, \|mean\|≥0.5 dropped the four deliberately planted ambiguous terms; **student reviewed and approved all 28 passing terms** (recorded in `lexicon_candidates.csv`; pipeline runs in human-reviewed mode). Headline finding: **inflection gaps** — 'downgrade' present, 'downgrades'/'downgraded' absent; VADER does no stemming. Install is single-token only (finvader vendors nltk's VADER — no SPECIAL_CASES dicts); multi-word ideas as hyphenated tokens, stated openly. |
| Backtest | Walk-forward, expanding window, 252-day burn-in, 21-day rebalance, weights strictly from past data (verified by future-data scrambling: weights moved 0.00e+00). First live rebalance **2021-01-04** (Combined, Equity-Only; 36 rebalances), **2020-09-10** (Crypto-Only; 58). rf = 0 stated. The leading 2020-01-02 crypto-only row is dropped from the Combined matrix (all 50 equities NaN there). |
| Annualisation | **√252 Combined/Equity-Only, √365 Crypto-Only** — verified from actual obs/yr (252.1/252.1/365.5), echoed in a `calendar` column per fund row. Never blended. |
| Recommended fund | **Combined Min-CVaR** (all 12 stay in the app; the pick is a highlighted default). Chain: (1) the bootstrap splits methods into a protective pair (Min-CVaR, Min-Variance) and an exposed pair (RP, MS) on crash days — **against the recommended Min-CVaR, 0.94–2.22pp per crash day**, all four CIs excluding zero (RP −1.32 / MS −2.22 at q=5%; RP −0.94 / MS −1.69 at q=10%); (2) within the pair Min-CVaR earns more (8.26% vs 6.76% ann., Sharpe 0.6180 vs 0.5427) at indistinguishable protection; (3) its objective targets tail loss directly, matching the product promise. **Caveat stated plainly**: Min-CVaR over Min-Variance is a judgement call on objective alignment, not a measured win. Never bury Risk Parity's Sharpe (0.8416). |
| Why the co-crash panel earns its place | The Sharpe ranking and the crash-day ranking **disagree** — Sharpe alone sends a user to Risk Parity, which loses **0.94pp more per crash day than the recommended Min-CVaR at q=10%, CI [0.71, 1.16]** (1.32pp, CI [0.97, 1.66] at q=5%; both exclude zero — `co_crash_bootstrap.csv`, rows with `fund_b = Combined Min-CVaR`). If the rankings agreed the panel would be redundant; because they disagree it reveals what the required metrics hide. This framing is the centre of Section 4. |
| Management fee | **0.35% p.a., display-only — LOCKED.** The brief's product is a business that earns a management fee, and the app had none until now. 0.35% is the judgement call: above a broad-index tracker (~0.20%) because a 21-day rebalance over 60 assets with a crypto sleeve costs more to run, below an active crypto mandate (~0.50%). It is charged **in display only** (`MGMT_FEE` + `after_fee()` in `streamlit_app.py`), NOT inside `oos_backtest` — so **every number in `results/` is unchanged** and stays the right object for comparing strategies; the fee is a platform charge on the investor, not a cost the strategy incurs. Accrued on each fund's own calendar (`fee/252` or `fee/365`), which is the √252-vs-√365 trap in a new place — a 365-day fund charged at 1/252 would be overcharged ~45%. Shown as a Key-facts item and as an after-fee growth of $1 beside the gross one, never replacing it. Terminal drag: **−1.04%** for the 252-day funds, **−1.15%** for Crypto-Only (longer window from 2020-09-10). Three tests cover it; both mutations (fee dropped, calendar hardcoded) were confirmed to fail. |
| Presentation | **Two registers, deliberately — superseded Phase 8c; the earlier "FT look shared across report exhibits AND the app" is wrong and `streamlit_app.py` imports no `ft_style`.** Report exhibits keep `ft_style.py`'s cream FT look (right for print). The app is a dark trading-terminal surface (`src/app_theme.py` + `.streamlit/config.toml`) — a retail product is not a newspaper page. Safe because the app draws its charts live from `results/`, so restyling it cannot alter a report exhibit. The app **does** carry a defensible design system worth claiming: hue = method, dash = asset family (12 funds → 12 distinct pairs, test-pinned), the user's blend in white so it never collides with a component, every colour set explicitly rather than derived from a theme token, and responsive breakpoints verified at 390/768/1280px (and again at 430/1600px in Phase 11). **Extended in Phase 11 — describe the system, do not attribute it (LOCKED):** the app's surface follows one documented token set rather than per-widget choices — a dark-tile ladder on a true-black floor, one interactive accent decoupled from every data colour, the 300/400/600/700 weight ladder with 500 deliberately absent, a documented radius scale where the pill is reserved for actions, and motion that fires only on intent (press `scale(0.96)`, a frosted sticky sub-nav) with `prefers-reduced-motion` honoured and measured. **Do NOT name any company as the source.** The tokens were adapted from a third-party reconstruction of a consumer marketing site, which is not a citable design standard, and the borrowed palette was never the claimable part. What is claimable is the app's own system, all of it code-provable: hue = method, dash = family, colour set never derived, one accent, reduced motion measured, contrast 5.6:1. The departures are the argument: the consumer surface's one-tile-per-viewport spacing was rejected as wrong for a dense analytics tool, and the accent rule is documented in code as knowingly unreachable for Streamlit's `ProgressColumn`. Section 5 can say the app answers to a stated set of tokens and name where it departs from it. |
| Priority discipline | The parameter analysis is finished — more of it buys rigour, not innovation marks. All innovation strands are built; remaining effort goes to the report prose. |

**Considered and rejected** (material for Section 6 and the AI log):
- **EVT (POT/GPD tail fitting)** — repeats Part A's Gaussian-understates-tails
  finding; a per-window GPD fit inside the CVaR optimiser needs more tail
  exceedances than monthly rebalancing provides.
- **ARIMA / GARCH-EVT return forecasting** — daily returns ≈ random walk;
  conflicts with Quokka's risk-based (not market-timing) positioning.
- **Block-bootstrap fan chart** — defensible but deferred for scope; now a
  Section 6 recommendation.

---

## Claim ledger — every number the report may quote

All verified against live runs and re-checked in the Phase 8 sweep (metrics
recomputed independently from `fund_returns.csv` match `performance_metrics.csv`
to 6.3e-15). Quote from the named CSV; never re-derive by hand.

**Data & backtest frame**
- Equity 50,300×9; crypto 14,610 post-cap; combined panel 60,360 rows;
  calendars 252.1 / 252.1 / 365.5 obs/yr.
- First live rebalance 2021-01-04 / 2021-01-04 / 2020-09-10; 36/36/58
  rebalances; 753 / 753 / 1,208 OOS days.
- Vol clustering: equity ACF(r²) +0.49 at lag 1 (ACF(r) −0.18); crypto +0.17.

**Fund performance (`performance_metrics.csv`)**
- Combined Sharpe: RP **0.8416**, CVaR **0.6180**, MV **0.5427**, MS **0.5193**.
- Equity-Only Sharpe: RP 0.7231, CVaR 0.5590, MV 0.5291, MS 0.2996.
- Crypto-Only MV: **Sharpe 1.3160 on −71.2% max drawdown** (the
  Sharpe-misleads exhibit). Combined MS max DD −34.6% vs MV −16.1%.
- Ann. return: CVaR 8.26%, MV 6.76%. **Growth of $1 is now a saved column for
  all 12 funds** (`performance_metrics.csv` → `growth_of_one`, added Phase 8c
  because the brief requires it in every fact sheet and no CSV held it):
  Combined RP 1.4410, MS 1.3166, CVaR 1.2463, MV 1.1958; Crypto-Only MV 10.0973
  is the largest. Quote the column, never a hand-run cumprod.
- Annual two-way turnover: MS ~409%, MV ~263%, CVaR ~100%, RP ~49%.
- Net Sharpe: podium RP > CVaR > MV > MS at every cost level; at 50 bps
  MV 0.427 vs MS 0.424.
- EWMA vs static (`parameter_study.csv`): 12.45% vs 12.79% realised vol; edge
  +0.29/+0.12/+0.72pp by year; return edge +0.63/+2.19/−1.73pp (do not claim);
  turnover 263%/yr vs 30%/yr; breakeven ≈ 20 bps.
- Numerical caveat (Section 6 material, verified in the Phase 8c re-check): the
  no-look-ahead scramble gives **exactly 0.00e+00** for all four methods when the
  panel's memory layout is held fixed. Change the layout and min-variance weights
  move by up to 1.8e-04 — because the covariance shifts in its last bit (~1e-18)
  and the minimum is very flat (condition number ~1.3e3, the median across the 36
  Combined windows), so the *objective* moves only 2.4e-07 relative. Not
  look-ahead, and far below any reported precision, but it is the second argument
  for shrinkage alongside the 227× condition-number finding. Locked in by
  `tests/test_portfolios.py`.
- Method separation (`method_separation.csv`): closest pair per family
  0.078 Combined / 0.076 Equity-Only / 0.150 Crypto-Only (all Min-Variance vs
  Risk Parity). 520 rebalance solves across the 12 funds, all converged.
- Holdings: Min-CVaR 16 names at the latest rebalance (2023-12-05), max at
  the 10% cap (`current_holdings.csv` ≡ final weights row, 0.0e+00).

**Co-crash (`co_crash_panel.csv`, `co_crash_bootstrap.csv`)**
- **The crash-day gap: which range, and against which fund (corrected Phase 8c).**
  There is no single "1.0–2.1pp". `co_crash_bootstrap.csv` holds **10 pairings,
  8 of them distinguishable**, and the span depends on the comparison fund:
  - **vs the recommended Combined Min-CVaR: 0.94–2.22pp** — RP −1.32 CI
    [−1.66, −0.97] and MS −2.22 CI [−2.95, −1.48] at q=5%; RP −0.94 CI
    [−1.16, −0.71] and MS −1.69 CI [−2.17, −1.20] at q=10%. **This is the
    pairing Sections 2 and 4 need**, because the recommended fund is Min-CVaR.
  - vs Combined Min-Variance: 1.01–2.13pp — RP −1.23, MS −2.13 at q=5%;
    RP −1.01, MS −1.76 at q=10%.
  - Not distinguishable either way: Min-CVaR vs Min-Variance, +0.09 CI
    [−0.07, +0.25] at q=5% and −0.08 CI [−0.19, +0.04] at q=10%.
  An earlier summary read "1.0–2.1pp (1.01/2.13 at q=5%)" — that **1.01 is the
  q=10% figure transcribed into the q=5% slot** (q=5% is 1.23), and it quoted the
  vs-Min-Variance pairing inside a sentence justifying Min-CVaR. Same wrong-object
  trap as Phase 8b's crash-day CI. The app now computes its caption from the file;
  quote the file, never a remembered range.
- 13 joint-crash days full-sample at q=5% (= 1.29% of days ÷ 5% = Part A's
  25.9% — the same object; one reconciliation sentence in S4); 9 in the OOS
  window. q=10%: 28 total, **22 OOS for Combined and Equity-Only, 23 for
  Crypto-Only** — that family's window opens 2020-09-10 and catches one extra
  day. Say "22" only about Combined/Equity-Only; `co_crash_panel.csv` shows 23 on
  the Crypto-Only rows and an unqualified 22 will read as an error. Every
  bootstrap pairing uses Combined funds only, so no interval is affected.
- Crash-day means q=10%: MV −1.44% ≈ CVaR −1.52% ≪ RP −2.46% ≪ MS −3.21%.
- Paired bootstrap vs MV (q=10%): CVaR −0.08pp CI [−0.19, +0.04] (**not
  distinguishable** — nor at q=5%: +0.09pp CI [−0.07, +0.25]);
  RP −1.01pp CI [−1.20, −0.82]; MS −1.76pp CI [−2.21, −1.32] (both exclude 0).
- Paired bootstrap **vs the recommended Min-CVaR** (q=10%): RP −0.94pp CI
  [−1.16, −0.71]; MS −1.69pp CI [−2.17, −1.20]. At q=5%: RP −1.32pp CI
  [−1.66, −0.97]; MS −2.22pp CI [−2.95, −1.48]. All four exclude zero — this
  is the pairing Section 4's "a Sharpe-shopper pays ~1pp per crash day"
  argument needs, since the recommended fund is Min-CVaR.

**Sentiment (`sector_sentiment_index.csv` + tables)**
- 105,330 distinct headlines / 146,830 rows; mean compound +0.0692; index
  9,832 sector-day rows × 10 sectors.
- **Why finVADER, measured (`sentiment_neutrality.csv`).** The
  brief's own warning — "about half of finance headlines score neutral with plain
  VADER" — confirmed on this data: **48.09% of the 105,330 distinct headlines
  score exactly 0.0 under plain VADER vs 16.00% under finVADER**; the finance
  lexicon rescues **34,662 of plain VADER's 50,654 neutrals (68.4%)**; lexicon
  **7,502 → 13,324** terms. Baseline built from finVADER's OWN analyser class with
  no lexicon update, so the comparison isolates the lexicon, not the
  implementation — scoring the baseline with the separately-installed
  `vaderSentiment` package instead gives 47.99% / 34,602, because its lexicon
  carries four terms nltk's does not. **Quote the CSV, not either scratch run.**
  **Distinct from the 253 false neutrals in `lexicon_before_after.csv`** — that is
  the 28-term extension on top of finVADER; this is finVADER against bare VADER.
  Two different objects, two different magnitudes; never merged.
- Note for the data paragraph: news is **146,836 rows post-dedup** (= the brief's
  149,683 − 2,847 exact duplicates, matching exactly), and the headline panel is
  **146,830** — the 6 lost rows are headlines dated 2023-12-30/31, after the last
  trading day (2023-12-29), which cannot map forward. One sentence, or a marker
  doing the brief's arithmetic gets 146,836 and finds no explanation.
- Coverage: Materials/RealEstate 93.44% of days covered (2.84/2.97 mean
  tickers), Tech 100% (4.32), Consumer 99.2% (4.73).
- **The floor, not just the mean (`sentiment_coverage.csv`).** `min_tickers` is
  **1 for nine of the ten sectors** — only
  Consumer never drops below 3. `pct_days_single_ticker` now carries how often
  each sector's index value rests on ONE ticker: **RealEstate 16.2% (152 days),
  Materials 15.7% (148), Utilities 12.7% (122)**, against ≤2.0% for the other
  seven and 0% for Consumer. So roughly **one covered day in six** is a
  single-voice reading in the two thinnest sectors — a materially stronger
  limitation than "averages 2.84 of 5", which states only the comfortable half of
  the fact. Use it in S3 P3 and again in S6 P3.
- Event validation (BASE index — these are the CSV's numbers): OXY percentile
  **0.074**, BCH-USD **0.183**, COVID week **0.235** (all recognised, <0.25);
  positive control XLM +74.9% at 0.559, correctly NOT flagged.
- Fusion: gross ΔSharpe +0.0034/−0.0107/+0.0015/+0.0050 (MS/MV/RP/CVaR); net
  20 bps +0.0019/−0.0139/−0.0075/−0.0009; k-grid peaks ~k=0.3 (0.6347) with
  drawdown worsening monotonically; growth of $1 CVaR 1.2463 → 1.2488 fused
  (now saved as `growth_of_one_base`/`_fused` in `fusion_before_after.csv`).
- Lexicon (human-reviewed mode, `lexicon_before_after.csv`): 28 of 32
  installed. **Two counts that are NOT the same number and must not be
  swapped**: **1,106 headlines (1.05%) contain an installed term**
  (`n_headlines_containing_term`), of which **1,097 (1.04%) actually changed
  score** (`n_scores_changed`) — nine contain a term whose compound is
  unmoved. Then **253 false neutrals fixed**; mean |change| 0.380; index
  correlation with the base index **0.990** (`index_corr_with_base`).
- Post-extension event validation (`lexicon_event_validation.csv`, a separate
  file from the base `sentiment_event_validation.csv`): OXY 0.055, BCH 0.151,
  COVID 0.239, control 0.513 still not flagged. The 0.074→0.055 sharpening
  lives ONLY in the Section 4 lexicon discussion, never in Section 3 (they
  describe different objects).
- **Report all three movements, not the two that flatter the extension.** OXY
  sharpens 0.074→**0.055** and BCH 0.183→**0.151**, but the **COVID week moves
  the wrong way, 0.2346→0.2386** (still recognised, still under 0.25). Two of
  three improving is the honest claim; quoting only OXY and BCH is the one place
  S4 could fairly be read as cherry-picked, in a report whose whole credibility
  rests on volunteering results that went against it. The control also tightens
  0.559→0.513 while staying correctly unflagged — worth one clause, since a
  control drifting toward the flag threshold is the thing to watch.

**Citations — resolved by removal.** The four named sources (RiskMetrics,
Basel FRTB, UCITS 5/10/40, Ledoit–Wolf) were never bibliographically verified,
and the report does not need them: nothing in the argument rests on the
authority of a source, only on numbers from this project's own data. Each is
now stated as an unattributed convention and justified on its own evidence —
"a λ = 0.94 short-span alternative costs +1.23pp of realised vol", "a 97.5%
level leaves only 6.3 tail scenarios at T = 252", "a 10% per-issuer cap in the
retail-fund convention", "shrinkage cuts the condition number 227× but moves
realised vol 0.05pp". **Do not reintroduce a named citation unless you verify
its metadata first** (`.claude/rules/latex-citations.md`). If the report ends
up with no reference list at all, that is fine — the brief does not require one.

**RETRACTED — never use:** "min-CVaR wins the worst single crash day in all
six family × threshold combinations" (bootstrap invalid on minima); "min-CVaR
loses to min-variance on mean crash-day return at q=10%" (the gap straddles
zero).

---

## Report section plan — final budgets (sum = 5,000)

**Page limit: settled.** The brief's "max 10 pages of written narrative" stands,
but the **lecturer confirmed he will be flexible**, so the planned body is
accepted as-is. **Exhibits reallocated to trim it**: body is now
**7 figures + 4 tables** (was 8 + 5), landing near **12 pages** rather than 13,
with the appendix on top. The word budgets stay — they discipline the argument, not
the page count.

The reallocation kept all seven brief-required exhibits plus `co_crash_panel.png`
in the body, moved `weights_stacked_min_cvar.png` and `parameter_study.csv` to the
appendix, retired the duplicate per-fund fact-sheet table (body Table 1 now carries
all six required elements for all twelve funds), condensed `current_holdings.csv`
from 236 printed rows to 12, and stopped printing three one-to-eight-row tables
(`vol_clustering_acf`, `sentiment_neutrality`, `lexicon_before_after`) that are
quoted in prose instead. **Final numbering (the earlier
"co-crash = Figure 6 / cost sensitivity = Figure A2" note was stale):** the
finished document uses one continuous SEQ sequence, Figures 1–9 and Tables
1–14, appendix exhibits included. Body = 6 figures (1 Sharpe bar, 2 growth,
3 drawdown, 4 sentiment index, **5 co-crash**, 6 fusion) + Tables 1–4;
appendix = Figures 7 (stacked weights), 8 (NVDA), 9 (live-app screenshot) +
Tables 5–14. There is no "Figure A2" anywhere. All typed in-text references
were machine-checked against a simulated F9 renumbering — every one matches.

Derived from marks-per-word: Section 4 carries the 30% band (max words);
Section 5's 15% is earned by the deployed app itself (min words); Section 6 is
the only criterion earned entirely by prose. **Each section below was written
from a per-paragraph plan with every number placed.**

1. **Funds & backtest design (~700)** — frame; data/universe (input vs
   output); the four objectives + β decision; caps incl. the crypto
   degeneracy; EWMA with the three rejected alternatives (volatility claim
   only); the backtest contract with actual dates, rf = 0,
   costs-with-breakeven, verified calendars.
2. **OOS results & fact sheets (~1,100)** — lead with RP's Sharpe; metrics
   table interpreted; growth/drawdown; the two weights reads (NVDA across
   methods + stacked book); costs preview; solver honesty + current holdings;
   the recommendation chain with its caveat ("funds are compared"). Per-fund
   fact-sheet detail → appendix.
3. **Sentiment index (~600)** — model + versions + raw-text justification;
   two-step construction with the worked example; three-level no-headline
   rule; validation with the positive control (BASE numbers); caveats.
4. **Extensions & innovations (~1,450)** — frame; Min-CVaR fund; **co-crash +
   bootstrap (the headline, ~400w)** incl. the β/q independence point, sample
   honesty, and the owned negative result; cost model; fusion honest verdict;
   lexicon with the disclosed division of labour; close naming the headline.
5. **App & investor journey (~400)** — the user; the journey as the tabs
   implement it; engineering facts (public repo, live URL, precomputed-only);
   one honest scope line. The scope line now has something concrete to say: the
   app carries an explicit coursework / not-investment-advice statement because
   it is published openly and reads as a live product (Phase 8c, item 9).
6. **Reflection & three recommendations (~700)** — what worked (named); what
   didn't (each with its number — this paragraph is the band's
   differentiator); limitations with numbers; three recommendations:
   turnover-penalised rebalancing (263%/yr vs 30%, ~20 bps breakeven),
   block-bootstrap fan chart, human-labelled lexicon calibration.

**Section 6 gained a paragraph in Phase 8c: the verification failure.** Every
other "what didn't work" item is a hypothesis that lost to the data. This one is
different — the analysis was right and the *product* was wrong, and the checks in
place could not have told the difference. Eleven of twelve funds displayed at
"0.1%", the headline co-crash exhibit at −0.02% instead of −1.85%, no number in
`results/` ever wrong, and it survived `AppTest` (0 exceptions) plus the
seven-item sweep (wiring to 6.3e-15) because **a test can only fail on the
dimension it observes**. Written up as **P2b** in the report with the full
evidence list, in my own words. **Section 6 stays at
700 words**: P2b is funded by trimming the other paragraphs (P1 150→120,
P2 200→130, P3 130→120, P4–P6 220→210), not by extending the section.

---

## Rubric position (Part B criteria)

| Criterion | Wt | Status |
|---|---|---|
| Funds & OOS backtest | 15% | Built + verified: 12 display-named funds, no-look-ahead machine-checked, calendars verified, all required exhibits rendered and eyeballed, current-holdings artifact present. Fact-sheet presentation lands in the app + report |
| Sentiment & fusion | 10% | Built + verified: validated index (3/3 events + control), lag-exact fusion, honest negligible-net verdict. Critical-assessment prose written (Phase 9 done) |
| Innovation | 30% | All four strands **built and demonstrated** with saved artifacts (the rubric bar: "any one suffices"; explained negative results credited). Interpretive depth written (Phase 9 done) |
| App | 15% | Built and **visually audited tab by tab** (Phase 8c): a 100× display-scale defect plus ten further findings, checked at 390/768/1280px as well as full width, `tests/test_app.py` added (11 tests) to cover the render layer, Ruff clean, tab bodies fragmented (8 → 5 figure renders per fund switch). **Phase 11** restyled it onto one documented token system (see the Presentation row — describe it, do not attribute it; claim the app's own encoding system, which is code-provable) and re-screenshotted all five tabs at 1600/430px; the rubric's top band names "polished, coherent design and user experience — including an original design system" explicitly, so this is scored here as well as under Innovation. **Deployed: public repo + live URL (Phase 10)** |
| Interpretation & reflection | 10% | Material strong (real negative results, quantified limitations). **Written (Phase 9 done)** |
| AI workflow | 20% | Best-covered: own agent files, **14** prompt logs, ~30 recorded corrections in `AI_NOTES.md`. Keep one log per non-trivial task |

---

## Produced artifacts (all verified; single-object wiring)

- `results/data/`: `fund_returns.csv` (10,856 rows), `fund_weights.csv`
  (8,951), `sector_sentiment_index.csv` — the exact required names.
- `results/tables/`: `performance_metrics.csv` (12 funds, `growth_of_one` +
  calendar + net
  columns), `current_holdings.csv`, `co_crash_panel.csv`,
  `co_crash_bootstrap.csv`, `fusion_before_after.csv`, `fusion_k_grid.csv`,
  `lexicon_before_after.csv`, `lexicon_candidates.csv` (28 keep / 4 drop
  recorded), `lexicon_event_validation.csv` (the extended index re-validated
  on the same four events), `sentiment_event_validation.csv`,
  `sentiment_coverage.csv` (with the `pct_days_single_ticker` floor),
  `sentiment_neutrality.csv` (plain VADER vs finVADER neutral share — the
  evidence for the model choice), `vol_clustering_acf.csv`,
  `parameter_study.csv` (rival covariance estimates with by-year splits),
  `method_separation.csv` (max |Δw| for all six method pairs per family).
  **15 tables in total.**
- `results/figures/` (**8** figures): `performance_sharpe_bar`, `growth_of_one`,
  `drawdown`, `weights_over_time` (NVDA across methods),
  `weights_stacked_min_cvar`, `sentiment_index`, `fusion_before_after`,
  `co_crash_panel` — all FT-style with assertion titles, all eyeballed.
  `performance_sharpe_bar` was regenerated so its axis label and
  subtitle set the risk-free rate as mathtext (`$r_f = 0$`) rather than the
  literal "rf"; the re-run was checksum-diffed and that PNG was the only file in
  `results/` that moved.
  A ninth, `cost_sensitivity`, was **deleted**: every value it plotted
  is a column of `performance_metrics.csv` that the report prints as Table A1, so
  it duplicated a table. The cost model is unaffected — still charged inside
  `oos_backtest`, still written to those columns. The cost strand now argues from
  the table plus three one-sentence findings.

Everything regenerates from `python scripts/run_part_b.py` (deterministic:
seeded bootstrap, deterministic solvers; isolation-tested — and re-proved in
Phase 8c, when the lint sweep touched `run_part_b.py`, `portfolios.py`,
`sentiment.py` and `fusion.py`: a full re-run left all 14 CSVs and 9 PNGs
bit-identical — the counts as they stood then; the set is 18 CSVs and 8 figures
now, and the re-audit re-proved the same property, with only the
artifacts it deliberately changed moving).

Supporting files, none of which feed a number: `ruff.toml` (lint settings +
the two documented frozen-file exemptions) and the test suite — **29 tests**:
`tests/test_app.py` (14, display-layer, including the management-fee tests),
`tests/test_portfolios.py` (13, the risk estimate, the no-look-ahead scramble,
and the calendar / lag / cap rules added after mutation testing showed three of
them had no test that could fail), `tests/test_smoke.py` (2). All 29 pass;
`ruff check .` clean with no flags.

---

## Verification checkpoints — the Part A lessons that still apply in the writing phase

- Never edit `report.docx` by script while it is open in Word, or vice versa.
- Every named ticker/sector/headline example must exist in the data (all
  current ones verified; check any NEW example before writing it in).
- Every percentage in prose must be a literal value in a saved CSV.
- If an exhibit is regenerated, figures and tables must come from the same
  computed object — re-run `run_part_b.py` wholesale, never patch one output.
- Report the numbers as they are: the honest split results (fusion, min-CVaR
  vs min-variance) are creditable findings, not failures to explain away.
- One log per non-trivial AI task in `ai/`, same discipline as before.

## Standing guardrails (unchanged)

No look-ahead anywhere; sentiment lag ≥1 trading day; √252/√365 never blended;
sentiment applies to equities only; the deployed app reads `results/` only
(never imports the scoring stack, never recomputes a backtest); raw data never
committed; own interpretation only — AI drafts code and structure, never the
report's economic reasoning; only this project's own `z5594806_projectA`/
`z5594806_projectB` folders are ever opened in the AI tool (brief §7).

---

## Status

- [x] Phase 0 — agent files + AI logging
- [x] Phase 1 — Part A foundation ported, isolation-verified
- [x] Phase 2 — `portfolios.py`: four optimisers, EWMA, walk-forward backtest
      with the cost grid, co-crash panel + paired bootstrap, cap guard;
      claim-ledger numbers reproduced exactly; no-look-ahead scramble test
- [x] Phase 3 — `sentiment.py`: finVADER built once, cached scoring, two-step
      index, three-level no-headline rule, lag-exact fusion signal, event
      validation passed (3/3 + control)
- [x] Phase 4 — `fusion.py`: tilt / fused backtest / k-grid; honest
      negligible-net verdict; k = 0.10 confirmed
- [x] Phase 5 — `lexicon.py`: AI-rater + filters + human review (28 keeps
      recorded); 253 false neutrals fixed; human-reviewed mode active
- [x] Phase 6 — `run_part_b.py`: six stages, all artifacts, single-object
      wiring, frozen-count assertions at startup
- [x] Phase 7 — `streamlit_app.py`: five-tab investor journey, precomputed-only,
      AppTest 0 exceptions (**an insufficient bar on its own — the app audit is in
      `ai/prompt_log_10`**). Later restyled against an adapted third-party token
      set, re-screenshotted, pipeline re-run checksum-clean (logged as Phase 11 in
      `ai/prompt_log_11`) — the evidence for the design-system claim in the App
      rubric row
- [x] Phase 8 — four independent verification passes (sweep, pre-writing audit,
      app audit, whole-project re-audit; detailed in `ai/prompt_log_07`–`10`).
      Together they proved **no number in `results/` was ever wrong** while the
      *documentation* around them had drifted, and left 42/42 brief requirements
      traceable in this file
- [x] **Phase 9 — write `report.docx`** (six sections; own words). **All six
      sections drafted and inserted, in my own words.** Exhibits renumbered to a
      continuous Figure 1–9 / Table 1–14 scheme. The pre-export steps (delete the
      one remaining marker, F9-update fields, export `report.pdf`) fold into
      Phase 10.
- [x] Phase 10a — deployed: own public repo
      (`lucassun-unsw/projectb-quokka-funds`) + Streamlit Cloud live URL;
      `streamlit==1.57.0` pinned after the cloud build's tab styling diverged;
      URLs pasted into `report.docx` + `README.md`; whole-document audit run
      (all 14 tables and all prose numbers verified against `results/`; two
      typos fixed)
- [x] Phase 10b — hand in: fields + TOC updated (F9), `report/report.pdf`
      re-exported and verified (sequential Figures 1-9 / Tables 1-14, no
      leftover markers). Figure 9 replaced with the *Fact sheet* tab of the
      live app, its caption rewritten to match. `check_handin.py` passes (24);
      folder clean (no `Screenshot*.png` / `__pycache__` / `.ruff_cache`).
      Remaining: commit + push the final `report.docx`/`report.pdf`, zip, submit
      final report, zip `z5594806_projectB`, submit on Moodle with both links
