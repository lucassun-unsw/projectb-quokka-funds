# Prompt log — co-crash bootstrap, the fund recommendation, and a rubric audit of the whole plan

## What I wanted
Three things, in order: understand the parameters I'd just locked well enough to
defend them in the report rather than just accept them; decide whether the
innovation was strong enough for the 30% band; and check the whole plan against
the actual rubric wording before any more building.

## Prompt(s)
- A run of conceptual checks where I made sure I understood what I had agreed to
  before it went in the report: "what is that 10% and 25% mean? like a stock or
  crypto can only upto this in the portfolio?", "and what is that q=5% or 10%
  means", "so it is like the alpha in VaR and ES?", "what is span 252 means?",
  "what is the bootstrap CIs".
- "and for that variance matrix, what is your opinion, like use the standard one
  or keep it like what we said"
- "if this plan is good and is justifiable in the final report?"
- "and for this part, do you think we should improve a bit of the innovation?"
- "so for the portfolio, we do not assume how many stock/crypto we include, but
  decide after the result out?"
- "so like I think in the report we need to said a model selected although we
  will put all four on the app, so which one is this?"
- "do a all final check and make sure all the things is satisfy, innovation is
  enough and good, interpretation is ok for our decision..... and then update the
  OUTLINE"

## What the assistant produced
- Plain-language explanations of the weight cap, the co-crash threshold q, the
  EWMA span, and the bootstrap, each tied back to real numbers from my data.
- A sub-period stability test and a transaction-cost breakeven analysis for the
  EWMA-vs-static question (EWMA wins on volatility in all three OOS years but
  its return edge flips sign; breakeven ~20 bps).
- A paired bootstrap of the co-crash panel (2,000 draws).
- A fund recommendation with a reasoning chain, and a rubric-by-rubric audit of
  the plan written into `report/OUTLINE.md`.

## What was wrong or risky
- **The assistant recommended a headline claim before testing it, and its own
  test then disproved it.** Two sessions running, it told me to lead Section 4
  with "min-CVaR wins the worst single crash day in all six family × threshold
  combinations". When I asked it to actually run the bootstrap, that claim
  collapsed: bootstrapping a minimum is a known failure case — resampling can
  never produce a day worse than the observed worst, so the confidence interval's
  upper bound *is* the point estimate, and the comparison rests on effectively
  one observation per fund. **The assistant did not flag this when it proposed
  the bootstrap**; it only surfaced when reading the output. Had I written the
  report from the earlier advice, my most impressive-sounding claim would have
  been sitting on my least defensible evidence.
- **A second claim was also wrong in the opposite direction.** The plan said
  min-CVaR "loses on mean crash-day return at q=10% (−1.52% vs −1.44%)". The
  paired bootstrap shows that gap is −0.076pp with a 95% CI of
  [−0.188, +0.041] — it straddles zero. So min-CVaR neither wins nor loses
  against min-variance; the difference is noise at both thresholds. I had been
  about to report a loss that isn't there.
- **The assistant's judgement that my innovation was "thin" was made without
  reading the rubric carefully.** It told me the parameter work was rigour not
  novelty (fair) and that the innovation band was at risk (overstated). When I
  asked for a full check against the brief, the rubric's actual wording says
  *"any one suffices"*, that credit is for *"evidenced original work, not for
  outperformance"*, and that *"a careful extension with a negative result,
  explained, still earns this band"*. By that wording the co-crash panel alone
  is HD-shaped. The assistant corrected itself, but only after I asked it to
  check rather than opine.
- **Nearly all of these numbers had never been tested for significance.** Fund
  comparisons, crash-day gaps, the EWMA edge — all point estimates over small
  samples until I asked for the bootstrap.

## What I changed and why
- Retracted both wrong claims from `report/OUTLINE.md`, in all three places they
  appeared (including the Section 4 writing instructions), and replaced them with
  what actually survives resampling: the **protective pair (min-CVaR,
  min-variance) beats the exposed pair (risk parity, max-Sharpe) by 0.9–2.2pp per
  crash day, with CIs excluding zero at both thresholds**. That is now what
  Section 4 leads with.
- Added a **claim ledger** to `OUTLINE.md` — every number the report may quote,
  split into verified / not-yet-verified / **retracted**. The retracted section
  exists specifically so a later session cannot quietly resurrect a claim I have
  already disproved. This is a direct response to the failure mode above.
- Kept the min-CVaR-equals-min-variance finding as a *result* rather than hiding
  it: on this universe, minimising variance and minimising CVaR give
  near-identical downside protection, so the tail is not separately controllable
  here. The rubric explicitly credits an explained negative result.
- Chose **Combined Min-CVaR** as the recommended fund, and wrote the reasoning
  chain into the plan — including the instruction *not* to bury the fact that
  risk parity has the best Sharpe (0.8416) and the honest caveat that min-CVaR
  over min-variance is a judgement call on objective alignment, not a measured
  win.
- Narrowed the EWMA claim to the volatility reduction only after the sub-period
  split showed the return edge flips sign, and added the measured ~20 bps cost
  breakeven so "zero transaction costs" becomes a quantified limitation rather
  than a bare assumption.
- Added a transaction-cost model and the bootstrap as innovation strands to be
  built into `oos_backtest()` from the start rather than retrofitted.
- Recorded a standing note that further Phase 2 parameter work adds rigour but
  not innovation marks, so the remaining time goes to the fusion (Phase 4).

## Verification I did myself
- Asked what each parameter actually meant before letting it into the report —
  the cap, q, the span, the bootstrap. Two of those checks changed how I will
  write things up: q is a *joint* threshold on two series and is not the same
  object as β inside the min-CVaR optimiser, and the EWMA span is a decay rate
  (λ = 0.9921, half-life 87 days) not a 252-day window, which happens to collide
  numerically with the 252-day burn-in. Both are now flagged in the plan as
  things to state plainly so a marker does not think I confused them.
- Confirmed the bootstrap was run **paired** (both funds evaluated on the same
  resampled dates) rather than as two separate intervals — the funds are highly
  correlated day to day, so unpaired intervals would have been far less
  informative.
- Confirmed `results/` stayed empty and `check_handin.py` still passed after every
  change; all of this session's work was throwaway diagnostics plus planning.

## Still open / to verify later
- The four convention sources (RiskMetrics 2006, Basel FRTB, UCITS 5/10/40,
  Ledoit & Wolf 2004) remain **bibliographically unconfirmed** — carried over
  from `prompt_log_04` and now recorded in the claim ledger.
- Everything in Phases 2–7 is still unbuilt. The plan is now more thoroughly
  audited than it is implemented, which is the main risk to manage from here.
