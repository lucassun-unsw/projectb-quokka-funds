# Prompt log — Phase 9b, drafting Sections 4–6 and a whole-document verification pass

## What I wanted
Write Section 4 (extensions and innovations, the 30% band) in my own words and
get it into `report/report.docx`, then check the whole document — not just
Section 4 — for correct content and consistent style. Same discipline as
Sections 1–3: every quoted number holds to the quote-the-CSV rule, and the
prose is mine.

## What I directed
- **Section 4, five strands.** I gave the assistant the points each strand had
  to cover from my per-paragraph writing plan and wrote the prose myself: the
  Min-CVaR fund, the co-crash panel with the paired bootstrap (the headline),
  the transaction-cost model, the sentiment-fusion before/after, and the lexicon
  extension. It listed the bullets, pre-checked every number against the saved
  CSVs, style-checked my draft, then inserted the agreed text into `report.docx`
  with each exhibit after the paragraph that cites it. I typed the five display
  equations into Word myself; the assistant left placement notes saying which
  equation went where.
- **A sign convention across the whole report.** In body prose, drop the leading
  "+" on positive numbers and keep "-" on negatives. I asked the assistant to
  apply it everywhere and to tell me whether the same rule should hit tables.
- **A content-theory check of the entire document.** Not just numbers — the
  descriptions of each method too.

## What the assistant produced
- Bullet plans and a number-check for all five strands, a style pass on my
  drafts (British spelling, ISO dates, "%", compound-modifier hyphens,
  quote-the-CSV), and the `python-docx` insertion with the exhibits in place and
  equation-placement notes.
- The whole-document sweep: fund-name hyphenation fixed in Section 2
  (`Min CVaR`/`Max Sharpe`/`Min Variance` → hyphenated), the "+" signs stripped
  from body prose (kept in the two symmetric-scale captions), and a set of
  consistency fixes (`annualized` → `annualised`, `percent` → `%`, stray
  compound-modifier hyphens, one wrong serial comma).
- Two content-theory problems it flagged and I fixed (below), plus a read of the
  actual equation markup after I typed the equations in.

## What was wrong or risky
- **It over-diagnosed the equations from flattened math text — and was wrong
  twice.** Reading the equations as plain concatenated text (which drops every
  fraction bar, bracket, and accent), the assistant claimed the turnover
  equation was missing its absolute-value bars and that the tilt equation was
  circular (same symbol on both sides). When I asked it to read the real OMML
  XML, both were false: the `|·|` bars were present, and the tilt's left side
  already carried an accent that distinguishes it from the base weight. Only two
  equation issues were real: the Min-CVaR denominator had lost its closing
  parenthesis (`T(1-β` instead of `T(1-β)`), and the weight vector was typed as
  ω in some equations and w in others. The lesson: you cannot judge an
  equation's correctness from the text it flattens to — you have to look at the
  structure.
- **A theory error in my own Section 1 prose.** I had written that Equal Risk
  Contribution "allocates weights evenly." That describes 1/N equal-weighting,
  not risk parity, and it contradicted my own next sentence. The assistant
  caught it on the content read.
- **An overstatement in my Section 2 recommendation.** I wrote that a Risk
  Parity investor must accept "Max-Sharpe-like drawdowns." Checked against
  `performance_metrics.csv`, Risk Parity's max drawdown is -20.5%, nowhere near
  Max-Sharpe's -34.6% and much closer to the downside-focused funds. The real
  trade-off is its weaker crash-day protection, which is my Section 4 point.
- **Style drift between sections.** Section 2 still carried unhyphenated fund
  names and a couple of `percent`/`annualized` spellings that Sections 1 and 4
  did not — small, but the kind of inconsistency a marker notices.

## What I changed and why
I wrote all of Section 4 myself from the strand plans; the assistant's job was
the bullet list, the number-check, the style pass, and the mechanical Word
edits. I typed the five equations in by hand and fixed the two real problems it
found: I closed the Min-CVaR denominator parenthesis and changed every weight ω
to w so the five equations use one symbol for weights (one inline ω is the last
to change). I ignored the two equation problems it had invented, once the markup
showed they were not there.

On the two content problems, both were mine and both were worth fixing: I
rewrote the risk-parity sentence to say it allocates by risk rather than by
capital, and I replaced "Max-Sharpe-like drawdowns" with the accurate
trade-off, weaker protection on the market's worst days. The number-check earned
its place here — the drawdown overstatement only surfaced because the assistant
pulled Risk Parity's actual -20.5% from the CSV instead of taking my sentence at
face value.

On style, I took the consistency fixes (hyphenated fund names, "%" over
"percent", British spelling) because they make the report read as one document,
and I kept the "+" signs in the two symmetric-scale captions (a VADER scale
reads naturally as -1 to +1) while dropping them from prose. I left the delta
columns in the fusion table signed, on the assistant's argument that a signed
column reads better decimal-aligned than a bare positive next to a negative —
prose and tables are read differently.

---

# Section 5 — the app and the investor journey

## What I wanted
Write Section 5 (the app and the investor journey, the 15% band, ~430 words) in
my own words and get it into `report/report.docx`. This section is earned by the
deployed app itself, so the prose points at what the app does — the user, the
journey the tabs implement, the business model and fee, the design system, and
the engineering facts — rather than re-arguing the models from Sections 1–4.

## What I directed
I gave the assistant the paragraph points from my per-paragraph writing plan and
wrote the prose myself: the market gap and the 0.35% display-only fee, the tab-by-tab
journey, the two-channel design system (hue = method, dash = asset family), the
public repo and live URL, the precomputed-only engineering, and one honest scope
line. It listed the bullets, fact-checked each claim against the app source and
the CSVs, style-checked my draft, then inserted the agreed text into
`report.docx`. I typed the fee display equation (f, C) into Word myself; the
assistant left a placement note.

## What the assistant produced
A bullet plan, a read of the actual app source to confirm the design claims, a
fact-check that caught the tab miscount and the missing deployment sentence, a
style pass, and the `python-docx` insertion with the fee-equation placement note.

## What was wrong or risky
- **A tab miscount in my own draft.** I wrote that the journey runs across "four
  tabs." The app has five, and the not-investment-advice disclosure lives in the
  fifth (About and Data), so "four" both undercounted what a marker sees and hid
  where the disclosure sits.
- **A missing deployment sentence.** I had left out the public repo and live URL
  the brief requires. The assistant flagged it and dropped in a Phase 10
  placeholder, which still reads `[paste live URL and repo — Phase 10]` until I
  deploy.
- **A wording trap on the breakpoints.** I listed the tested viewport widths
  (390/430/768/1280/1600px) as if they were the CSS breakpoints. The real
  breakpoints are 900px and 520px, so I restated the widths as "verified at those
  widths" and kept the breakpoints as their own fact.
- **Design claims I had to verify rather than assert.** The accent, the 5.6:1
  contrast, the 300/400/600/700 weight ladder with 500 absent, and the
  reduced-motion measurement are all code-provable, so the assistant read the
  source and confirmed each before I kept it. The risk was describing a design
  system I had not checked.

## What I changed and why
I rewrote the journey as "four core tabs plus a fifth (About and Data)" and named
the disclosure's location in that fifth tab. I added the deployment sentence with
the Phase 10 placeholder so the real URL and repo drop in at deploy. I split the
tested widths from the breakpoints. I kept the design paragraph because every
claim held against the source — and I describe the system without attributing it
to any company, the locked decision after an earlier attribution failed
verification.

---

# Section 6 — critical reflection, and the final whole-document audit

## What I wanted
Write Section 6 (critical reflection and three recommendations, ~610 words) in my
own words — the one criterion earned entirely by prose — and run the final
whole-document pass here, since it is the last section.

## What I directed
I gave the assistant the paragraph plan from my writing plan and wrote the prose
myself: what the disciplined process caught early, the hypotheses that failed
against the data, the render-layer verification lesson, the limitations, and the
three recommendations (a turnover-penalised rebalance rule, a block-bootstrap fan
chart, and human-labelled lexicon calibration). I asked the assistant to
number-check every quoted figure against the CSVs and to run a full-document
audit — cross-references and dead exhibits, not just Section 6.

## What the assistant produced
A bullet plan; a number-check of the reflection's figures against the CSVs
(min-CVaR protection −0.08pp, CI [−0.19, +0.04]; EWMA 12.79% → 12.45% realised
vol; turnover 263% vs 30%; the ~20 bps breakeven; XLM 0.559; 253 false neutrals;
2.84–2.97 active tickers; 12.6 initial tail scenarios; 8 of 9 q=5% crash days
inside one 2022 episode); the full-document audit; and the Word edits.

## What was wrong or risky
Both problems came from the audit, and neither a section-level number-check nor a
read of the prose would have found them.
- **Stale cross-references.** Two body-table captions still pointed at "Table A5"
  and "Table A4" — the old appendix numbering I had already replaced with the
  continuous 1–14 sequence, so they pointed at tables that no longer exist. Fixed
  to Appendix F and Appendix E.
- **Dead exhibits.** Three appendices (E, H, I) — the co-crash full panel, fusion
  robustness, and the lexicon extension — had no reference anywhere in the body,
  which my own rule calls dead weight. Added a one-clause cross-reference to each.

The lesson repeats the render-layer bug the section is about: a number can be
right and an exhibit can be real, and the thing still wrong is whether the
document connects them — a check has to look at the join, not the two ends.

## What I changed and why
I repointed the two captions at the live appendix letters and added the three
missing cross-references, so no appendix is dead weight. I kept the reflection's
figures once the number-check confirmed them, and I kept the honest negatives —
fusion adds ≈0 net of costs, min-CVaR's crash-day protection is indistinguishable
from min-variance, and the crash sample is thin and episode-concentrated —
because volunteering results that went against the thesis is what this section's
credibility rests on.
