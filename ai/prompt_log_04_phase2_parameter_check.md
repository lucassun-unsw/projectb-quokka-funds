# Prompt log — Phase 2 fund parameters: checking conventions and the locked config against real data before coding

## What I wanted
Before writing `src/portfolios.py`, settle every judgement-call parameter it
needs (EWMA span, min-CVaR confidence level, weight cap, estimation universe,
co-crash threshold) against real data rather than inheriting whatever the
assistant defaulted to — the same discipline that caught the sector-aggregation
error in `prompt_log_03`. Then run the whole locked configuration end to end to
confirm the parameters are mutually consistent, not just individually sensible.

## Prompt(s)
- "run the 'check against real data' pass for Phase 2 before coding"
- After the first round of options: "I am thinking about the option you give, so
  maybe search online or something, like what is the most optimum/best way?"
- "i think for the portfolio, you do not include every stock, check the project
  brief to confirm this"
- "final verify all the things with the data again using our decision, if
  everything is good?"
- "try the 25% and see what going on then I will decide"
- Several conceptual checks where I made sure I actually understood what I was
  agreeing to before locking it: what the 10%/25% cap means, what q=5%/10%
  means, whether q is the same as alpha in VaR/ES, what "span 252" means.
- "and for that variance matrix, what is your opinion, like use the standard one
  or keep it like what we said"

## What the assistant produced
- Five throwaway diagnostic scripts (kept out of the project; `results/` stayed
  empty throughout) covering: calendar/universe counts per fund family, return-
  matrix completeness, backtest schedule, EWMA conditioning, min-CVaR LP scale
  and timing, solver behaviour, co-crash sample size, volatility clustering,
  span/shrinkage sweeps, universe-size sensitivity, and a full 15-check
  verification of all 12 funds.
- Web research on the published conventions for each parameter (RiskMetrics
  λ=0.94, Basel FRTB 97.5% ES, the UCITS 5/10/40 rule, Ledoit–Wolf shrinkage),
  which I asked for after finding the first round of options under-justified.

## What was wrong or risky
- **The assistant's own stated hypothesis was wrong, and it said so.** Its
  pre-run prediction was that a short EWMA span would make the 60-asset
  covariance singular. It doesn't — rank is full at every span, because EWMA
  still weights all observations. The real cost is conditioning and weight
  instability. Worth recording because the diagnostic was written to test a
  hypothesis that the data then rejected, which is the point of running it.
- **The first round of parameter options was presented without external
  grounding.** I pushed back and asked it to look up what standard practice
  actually is. That changed two answers: the weight cap gained a real
  justification (UCITS 10%), and the CVaR level gained a much better one (Basel
  uses 97.5% ES, but our T=252 window leaves only 6.3 tail scenarios there, so
  95% is a constraint-driven choice, not a default).
- **The assistant initially framed my universe question as if the brief settled
  it.** When I asked it to confirm against `PROJECT_BRIEF.md`, the honest answer
  was that the brief is silent — its only latitude is "choose your own window
  type, rebalance frequency, and constraints." I was right that funds don't hold
  every stock, but for a different reason than a brief rule: the long-only
  optimiser already drops most names (min-CVaR held 4 of 60). Pre-filtering the
  universe is a separate choice, and testing it showed it would have *hurt*
  (12.45% realised vol on all 60 vs 12.65–13.72% pre-filtered).
- **A real bug survived until the final verification sweep.** With the 10% cap
  locked, Crypto-Only has p=10, so 10 × 10% = 1.00 exactly — the cap admits one
  feasible solution and forces equal weight. All four Crypto-Only funds came out
  byte-identical (Sharpe 0.9124 across the board). Neither the earlier per-
  parameter checks nor the assistant's reasoning caught this; only running all
  12 funds together did. This is exactly the failure mode `OUTLINE.md`'s
  Verification checkpoints warn about — parameters that are individually fine
  and jointly broken.
- **The EWMA justification was weaker than the plan assumed.** Nobody had tested
  EWMA against a plain static covariance — the comparison the whole "time-series
  anchor" claim rests on. When I asked for an opinion, the test showed EWMA wins
  by only 0.33pp of annualised vol at ~9× the turnover, and its *return*
  advantage flips sign across years.

## What I changed and why
- Locked six parameters in `report/OUTLINE.md` with the evidence attached, not
  just the values: EWMA span 252; min-CVaR β 0.95; weight cap 10% for the broad
  families and **25% for Crypto-Only**; all-60 estimation universe; no
  shrinkage; co-crash at both q=5% and q=10%.
- Chose 25% for Crypto-Only after asking to see it run rather than accepting the
  recommendation on paper — it restored full method separation (closest pair
  0.107 apart) and every method then beat the collapsed equal-weight version.
- Narrowed the EWMA claim to the volatility reduction only, after the sub-period
  split showed the vol edge holds in all three years (+0.29/+0.12/+0.72pp) but
  the return edge does not (+0.63/+2.19/**−1.73**pp). Writing "EWMA improved
  returns" would not survive a marker splitting the sample.
- Demoted span 126 from "robustness alternative" to "tested and rejected" — it
  is worse than span 252 on both vol and turnover, and loses to a static
  covariance at 5 bps. Three rejected alternatives pointing at one choice reads
  better than presenting two as co-equal.
- Added the measured transaction-cost breakeven (~20 bps) to Section 6's
  recommendation, replacing a generic "add a cost model" suggestion with a
  number that says when the EWMA choice stops paying.
- Recorded that Section 4 must not be written from the plan's hypothesis:
  risk parity has the best Sharpe of the broad families (0.8416), and min-CVaR
  does *not* reliably win on mean crash-day return — it loses at q=10%. What it
  does win is the **worst single crash day, in all six family × threshold
  combinations**. That is the honest and sharper claim.
- Added a note to keep β, q, and the two 252s distinct in the report after I
  asked whether q was the same as alpha in VaR/ES. It isn't — β is univariate
  and inside the optimiser, q is joint and outside it — and that distinction is
  what stops the min-CVaR crash-day result from being circular.

## Verification I did myself
- Every number above came from a live run against the real hosted data through
  the already isolation-tested `etl`/`features`/`dependence` port, not from
  memory or a plausible-sounding default.
- Confirmed the co-crash date count reconciles with Part A's headline figure:
  13 joint-crash days ÷ 1,006 days = 1.29% of days, ÷ 5% = **25.9%** — the exact
  Part A tail-dependence figure carried in `OUTLINE.md`, so the Part B crash-date
  list and Part A's statistic are the same object.
- Ran an explicit no-look-ahead test rather than trusting the loop structure:
  scrambled every observation from the rebalance date forward and confirmed the
  weights changed by exactly 0.00e+00.
- Checked the assistant's claim that the manual EWMA computation matches pandas
  — it equals `.ewm(span=s, adjust=True).cov(bias=True)` exactly (0.000%), while
  pandas' *default* `bias=False` differs by 6.75%. Worth pinning down, since
  `OUTLINE.md` had previously just said "use `pandas .ewm().cov()`".
  **[Annotated later, after the whole-project re-audit: the 6.75% here is wrong.
  At span 252 the gap is 0.40%; 6.75% is that factor at a span of roughly 17.
  I carried the number for several sessions before catching it — see
  `prompt_log_10` and `AI_NOTES.md`. Leaving the original line as written.]**
- Confirmed `results/` stayed empty and `check_handin.py` still passes after the
  whole session — the diagnostics were throwaway, nothing leaked into the
  deliverables.

## Still open / to verify later
- The four convention sources (RiskMetrics 2006, Basel FRTB, UCITS 5/10/40,
  Ledoit & Wolf 2004) came from web search this session. Their full
  bibliographic metadata is **not** confirmed — verify each before citing under
  `.claude/rules/latex-citations.md`.
- Whether Combined and Equity-Only min-variance should ship as two funds or one:
  they correlate 0.99917 (mean crypto weight 0.46%). Decide at Phase 8 against
  the actual saved outputs.
