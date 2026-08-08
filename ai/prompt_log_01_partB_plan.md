# Prompt log — Part B plan: innovation direction, time-series method, and the report structure

## What I wanted
Turn "week 7-9 might be reusable for Part B" into a concrete, requirement-verified
Part B build plan — a locked innovation direction, a locked time-series method I
can actually defend, and a full report structure — before writing any Part B
code, so I don't repeat Part A's experience of catching gaps late.

## Prompt(s)
Across one continuous planning session:
- "Read through project B and weeks 7/8/9, summarise what's reusable, same
  style code we'll likely need."
- "Add the planning to a .md file in Part B... also read PROJECT_BRIEF, since it
  also requires innovation, what's good to do that aligns with our app/Part A —
  we did copula as innovation in Part A."
- A run of follow-up pushback on the innovation candidates the assistant
  proposed: "since all frameworks can't predict the true value, is EVT good?",
  "doesn't EVT look like the same as Part A's copula — repeat?", "how about
  ARIMA?", "or we use ARIMA as an app add-in to predict future performance",
  "I haven't learned EWMA, can we use GARCH instead?", "which one is actually
  better?", "since we have EWMA do we still need GARCH?"
- "Finalise OUTLINE.md, read the brief in detail so nothing is missing like Part
  A had things missing that wasted time — then give me the full report structure
  and the plan for each of the six report sections."
- "Do the Part A handoff items 1-4, port the Part A foundation in, and do the first
  ai/ log about our planning — check Part A's style, make sure you're on my
  side."

## What the assistant produced
- A week 7/8/9 -> Part B mapping (finVADER scoring pattern from week 9,
  cache-then-score pattern, FT figure helpers, the week 8 lexicon-extension
  pipeline) and a first `report/OUTLINE.md` update locking
  a Minimum-CVaR fund + a co-crash stress-test panel as the innovation anchor,
  tied to Part A's copula finding.
- A proposal to add EVT (POT/GPD tail fitting) as a third risk lens.
- A proposal, later, to use ARIMA as an app-only "predicted future performance"
  feature once return-forecasting itself was rejected.
- A proposal to drive the optimiser's covariance with EWMA, defaulting past my
  actual coursework without checking what I'd studied.
- After I pushed back repeatedly: a revised, scoped-down plan (EWMA only, no
  EVT, no ARIMA in any form) and, on request, a full re-read of
  `PROJECT_BRIEF.md` against the plan, producing the "Verification checkpoints"
  section and the six-section report plan with word budgets.

## What was wrong or risky
- **The EVT recommendation was redundant and I had to catch it.** The
  assistant's first pass proposed EVT largely to show "tails are fatter than
  Gaussian" — but Part A's `dependence.py::var_es_comparison` already
  established exactly that (empirical vs Gaussian ES, -10.8% vs -7.1%). Adding
  an EVT table would have repeated an already-established finding under a new
  name. I only caught this by asking directly whether it looked like a repeat —
  the assistant had not flagged the overlap itself until I raised it.
- **The ARIMA-as-app-feature idea understated a real risk until I pushed.** The
  first framing treated "app-only, not fed into the backtest" as sufficient
  safety. It took me raising "no model predicts the true value" before the
  assistant named the actual problem plainly: a fund-level ARIMA fit would
  likely just recover the historical mean dressed up as a forecast, and
  showing that confidently to a retail user conflicts with the product's own
  "transparent, honest" positioning.
- **EWMA was picked without checking what I'd learned.** I don't know EWMA;
  the assistant had defaulted to it purely on engineering-robustness grounds
  (no per-asset fit convergence risk in a ~2,900-fit walk-forward loop) without
  asking first whether it was something I could actually write about and
  defend in my own words.
- **General pattern**: the assistant proposed additions readily but did not
  self-flag redundancy or scope creep — cutting EVT, the ARIMA app feature, and
  the standalone GARCH diagnostic all happened because I asked pointed
  questions, not because the assistant volunteered the concern first.

## What I changed and why
- **Dropped EVT entirely.** Redundant with Part A's existing ES table; the
  only non-redundant version (feeding EVT into the optimiser itself) needs a
  stable per-rebalance GPD fit that a monthly window likely can't support
  reliably — not worth the risk for the marginal credit.
- **Dropped ARIMA in every form** — not as a fund input (near-random-walk
  returns, conflicts with the systematic/risk-based product thesis) and not as
  an app-only forecast feature (misleading-confidence risk to a retail user).
  Kept the safer block-bootstrap fan-chart alternative as a Section 6
  recommendation rather than building it now, to keep scope controlled.
- **Kept EWMA as the sole time-series driver of the optimiser**, after weighing
  it against GARCH myself: GARCH per asset is fittable but adds real fragility
  across ~60 assets refit every rebalance, and once I decided I'm willing to
  learn EWMA rather than force GARCH into the pipeline just because it's more
  familiar, the case for EWMA (closed-form, no convergence risk, still
  genuinely time-series-aware, industry-standard) was the stronger one. Also
  decided a standalone one-off GARCH diagnostic wasn't worth adding either —
  it wouldn't feed anything required, the same test that killed EVT.
- **Clarified my own conflation**: I had treated the co-crash stress-test panel
  as if it could count as one of the required optimisation methods. It can't —
  it's an evaluation panel applied *to* funds, not a way of constructing one.
  The required two-method minimum stays max-Sharpe + min-variance, with risk
  parity and min-CVaR as the extra methods.
- **Directed a full brief re-check before writing more code**, specifically
  because Part A's `ai/AI_NOTES.md` records several costly late catches (a
  figure plotted the wrong object, an orchestrator wiring two exhibits from
  different dataframes, a calendar/annualisation bug caught only in a late
  verification sweep). Had the assistant read that file and turn each entry
  into a named Part B checklist item rather than trust it wouldn't recur.

## Verification I did myself
- Asked the assistant to actually check `.gitignore` rather than assume a
  cache location was safe — this surfaced a real bug in its own earlier
  suggestion: `results/.cache/` would have been *committed*, not ignored,
  because `!results/**` re-includes everything under `results/` ahead of the
  blanket `*.parquet`/`*.csv` ignores. Fixed to a project-root `cache/` folder.
- After the source port (`etl.py`, `features.py`, `text_panel.py`, `ft_style.py`,
  `dependence.py` copied in from my verified Part A), ran an import check and a
  live smoke test against the real hosted data before treating the port as
  done: equity 50,300×9, crypto 14,610 rows post-cap, combined equity-calendar
  panel 60,360 rows — all three match the frozen Part A facts in
  `OUTLINE.md` exactly, so the port is verified, not just copied.
- Ran `scripts/check_handin.py` after the agent-file and source-port changes;
  fixed the one real `[FAIL]` it found (stray `.DS_Store` files) rather than
  ignoring it.
