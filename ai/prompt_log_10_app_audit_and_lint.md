# Prompt log — full app audit (the 100x scale bug), lint sweep, tab fragments, and the whole-project re-audit

Six sections, written as the work happened over 2026-07-30. Sections 1–5 are the
app audit and its follow-ups; **Follow-up 6 is an independent re-audit of the
entire project**, including the four mistakes the assistant made inside an audit
about correctness and the mutation testing that found three of my own rules had no
test that could fail.

## What I wanted

`prompt_log_09` ended with the assistant admitting it had never actually *seen*
the app — the macOS screen-recording permission dialog went unanswered, so it
reasoned about my UI from source code. I granted the permission and asked it to
check the whole app design properly and fix whatever it found.

## Prompt(s)

- "now back to part B, app design, check everythings of the app design, since
  you now have permission, and also change/fix everything needed"
- "write the ai log, and help me to fix the '39 pre-existing ruff findings in
  files I didn't touch (mostly scripts/run_part_b.py, some in frozen src/). Out
  of scope.' and also change the 'All five tabs compute on every rerun ...' no
  change to 'Mixing Combined with Crypto-Only in the growth chart ...' this is
  fine. so just help me to fix the first two"

## What the assistant produced

**The headline: every percentage in every table was rendering 100x too small,
and both of my earlier verification passes were structurally incapable of
catching it.**

`st.column_config`'s `format` is a printf string, not a percent directive. My
CSVs store rates as fractions, so `"%.1f%%"` applied to `0.0826` printed
**"0.1%"**, not 8.3%. What that actually looked like on screen:

- The twelve-fund comparison table — the app's centrepiece — showed **eleven of
  twelve funds as "0.1%" annual return**. Crypto-Only Min-Variance's 97.4% read
  as 1.0%; its −71.2% drawdown read as −0.7%.
- The **co-crash stress panel**, the exhibit `OUTLINE.md` calls the centre of
  Section 4, read −0.02% / 0.00% instead of −1.85% / +0.06% — directly
  contradicting its own caption ("1.0–2.1pp per crash day").
- Current holdings showed every position at **0.1%** while the bar chart beside
  it, drawn from the same column, correctly showed 10%.
- The page header (plain f-strings) said +8.26% while the table below it said
  0.1%. The app contradicted itself on one screen.

Fixed with an `as_pct()` helper applied on a copy immediately before each table.
It also deleted the caption that had been *explaining* the bug — "Percentages
are shown on a 0–1 scale by the formatter; read Ann. return 8.3 as 8.3%" —
which described behaviour that never happened, since the cell said 0.1%.

Four more real defects, all found by looking:

- **"of 60" was wrong for two of three families.** An Equity-Only fund optimises
  over 50 assets and a Crypto-Only fund over 10. Both the header and the fact
  sheet claimed 60.
- **The allocation blend always annualised with √252.** For a Crypto-Only blend
  that understates volatility by about a fifth (61.5% vs the correct 74.0%) —
  a straight violation of my own rule 2 (never assume the calendar from the
  family name). Now 365 when every chosen fund is Crypto-Only.
- **"Your blend" was drawn in the same accent blue as Combined Min-CVaR**, so a
  blend containing my recommended fund drew two blue lines with no way to tell
  which was mine.
- **Method colour collided across families** — all three Min-CVaR funds plotted
  in the same blue. Added a dash pattern per family; twelve funds now have
  twelve distinct (colour, dash) pairs.

Plus: the 12-row table was clipped mid-row; the sentiment headline read as live
with no as-of date on a fixed 2020–2023 dataset; the sidebar claimed costs
applied "across the app" when volatility, drawdowns and the blend are gross; the
`st.info` empty states still used Streamlit's derived contrast — the exact
mechanism that broke the About panel in log 09; and the About tab's live table
showed raw column names and `00:00:00` timestamps.

Then, on the follow-up: all 39 Ruff findings cleared, and the five tab bodies
converted to `st.fragment`.

## What was wrong or risky

- **The real lesson is about my verification, not the assistant's code.**
  Phase 7 signed the app off on "AppTest 0 exceptions" and Phase 8's sweep
  checked wiring to 6.3e-15. Both passed while the main table displayed eleven
  wrong numbers, because **AppTest asserts that the script runs, not what the
  screen shows** — it reads the values I passed in, which were correct all
  along. The bug lived entirely in the render layer, which is the one layer
  neither check touched. Every number was right in the CSV, right in the
  variable, and wrong in the browser.

- **Log 09's blindness was the cause, not a side note.** The assistant could not
  see the screen for the whole of Phase 7 and the log 09 design pass. Given a
  browser, it found the scale bug in the first screenshot. Roughly two sessions
  of UI work were done by reasoning about code instead of looking at output, and
  this is what that costs.

- **It could not use the browser I granted it either.** The permission came back
  at a read-only tier — screenshots allowed, clicks blocked — so it could see
  the default tab and nothing else. It said so rather than working around it,
  and drove its own headless browser instead, which is what made all five tabs
  and the non-default widget states reachable. Worth noting that the tool
  limitation was reported, not silently absorbed into a partial answer.

- **It got the table height wrong on the first attempt**, guessing 35px per row.
  The screenshot showed four empty grid rows hanging below the data — replacing
  a clipped table with a padded one. It then measured the actual row box in the
  DOM (28px) instead of guessing again.

- **Its first attempt to prove the fragment change worked measured nothing.**
  The benchmark reported ~2,527 ms for every variant because the number was
  dominated by a fixed `wait_for_timeout(2500)` in its own script — a timing
  harness measuring its own sleep. It caught this from the suspiciously
  identical numbers and rebuilt the measurement server-side, counting actual
  figure renders. This is the same failure shape as log 09's fresh-subprocess
  assert: a check constructed so it cannot fail.

- **Risk I made it stop and think about: the frozen files.** Three of the 39
  lint findings sat in `src/data_access.py` (provided, must stay identical to
  Part A's) and `src/etl.py` (frozen, verified to reproduce Part A's exact row
  counts). Auto-fixing those would have been the obvious move and the wrong one.

## What I changed and why

- **Accepted lint exemptions over edits for the two untouchable files.** A new
  `ruff.toml` records line-length and rule selection for this folder as a
  standalone repo — a marker who clones only this project would otherwise get
  Ruff's defaults and a different result from the one I report — plus two
  *narrow* per-file ignores with the reason written next to each. Anything other
  than those specific rules in those specific files still fails. I would rather
  a reader see the boundary than see a frozen file quietly reformatted.

- **Demanded proof the lint sweep changed no numbers.** The other 36 findings
  touched `run_part_b.py`, `portfolios.py`, `sentiment.py` and `fusion.py` —
  files that produce every figure I quote. I had it checksum all 26 artifacts,
  re-run `run_part_b.py` end to end, and diff: **all 14 CSVs and all 9 PNGs
  bit-identical**. Cosmetic changes are only cosmetic once you have checked.

- **Made it measure the fragment change instead of asserting it.** Result:
  page load renders 6 figures either way, but a fund switch on the fact sheet
  went from **8 figure renders to 5**. A real improvement and a partial one —
  some interactions still trigger a full rerun — and I would rather have the
  measured 8→5 than a claim that it "now only redraws one tab". The sidebar cost
  slider is deliberately left outside the fragments, since it changes the
  numbers on every tab and should rerun everything.

- **Added `tests/test_app.py` (7 tests) so the display layer is covered too.**
  The scale test asserts on the *displayed* value (8.26, not 0.0826); another
  asserts a single-fund blend reproduces that fund's published Sharpe and
  calendar exactly, which is what catches the √252/√365 bug; another asserts the
  twelve funds have twelve distinct colour/dash pairs. The gap that let this
  through was a class of test I did not have, so the fix is a test, not a note.

- **Confirmed log 09's open item.** The "hosted data, live" rectangle is
  genuinely fixed — verified by looking at it, which is the thing that was
  missing last time. The `st.info` panels it flagged as unconverted are now
  converted too.

- Kept the growth chart on a linear axis. Mixing Combined with Crypto-Only
  squashes the equity lines, but crypto genuinely grew about tenfold over the
  window and a log axis would flatter the comparison. Truthful beats tidy.

## Follow-up: I asked "so the app is all good now?" — it was not

Rather than answer from the list of things it had just fixed, it went and tested
the widget states it had *not* reached, and found three more.

- **A reachable state printed `Sharpe: nan`.** The allocation sliders bottom out
  at 0, so dragging them all down is something a user can simply do. The blend
  then renormalised by a zero total and reported 0% return on 0% volatility with
  a nan Sharpe. Now it says what is missing instead. My earlier screenshot pass
  never found this because I only ever looked at default widget values.
- **`co_crash_bootstrap.csv` was loaded and never used**, while the caption
  beside it quoted "1.0–2.1pp per crash day" as typed-in prose. That breaks my
  own guardrail — *every percentage in prose must be a literal value in a saved
  CSV* — and the number was wrong: the file's separable pairings actually span
  **0.94–2.22pp**. The caption is now computed from the loaded table (0.94–2.22pp,
  8 of 10 pairings distinguishable, 2 straddling zero), so it cannot drift from
  the file again. Worth noting the same "1.0–2.1pp" also sits in `OUTLINE.md`'s
  claim ledger — **check it before quoting it in Section 4.**
- **One of its own new tests was silently disarmed.** The zero-weight test used
  the shared module fixture, and an earlier test changes which funds are blended,
  which renames the sliders it was trying to set — so it set nothing and passed
  on a page that was working normally. Every mutating test now builds its own app
  instance. A test that passes for the wrong reason is worse than no test, and
  this is the third instance of that same shape in two sessions.

Verified good under the same sweep: all twelve fact sheets render, the cost
slider works at 50 bps, and empty selections on every tab are handled. Test
count 7 → 10.

## Follow-up 2: the narrow-viewport pass — and a regression I had asked for

Rendered all five tabs at 390 / 768 / 1280 px. Three findings, the first of them
self-inflicted earlier in this same session.

- **`initial_sidebar_state="expanded"` made the app unusable on a phone.** It was
  added earlier today with a sensible-sounding reason — the sidebar holds the one
  global control, so keep it open. Below ~768px Streamlit *overlays* the sidebar
  instead of pushing the page across, so at 390px the sidebar covered about
  three-quarters of the screen and buried the tab strip: **all four non-default
  tabs were unreachable.** Reverted to `"auto"`, which is expanded on a laptop
  and collapsed on a phone. A change that is right at one breakpoint and never
  checked at another is a change that was not really checked.
- **The stat grid dropped its fourth column's values.** `stat_grid(cols=4)` writes
  a fixed four-column CSS grid inline. At 390px the labels wrapped to two lines
  and the fourth column's *value* was pushed outside the panel — "Max drawdown"
  and "Calendar" appeared as labels with no number. Now steps to two columns
  under 900px and one under 520px, verified by reading the computed
  `grid-template-columns` back out of the DOM: 4 at 1500px, 1 at 390px.
- **`st.columns(len(chosen))` did not survive a full basket.** Blending all
  twelve funds produced twelve columns — roughly 100px per slider, too narrow to
  drag, with truncated labels — and that one is a desktop bug, not a mobile one.
  Sliders now wrap three per row; measured 268–348px each with all twelve
  selected.

No horizontal page overflow at any of the three widths (`scrollWidth` equals
`innerWidth`); the wide tables scroll inside their own container, which is the
intended behaviour.

The honest summary of this whole thread: I asked "is it all good?" twice, and the
answer was no both times — eight defects on the first pass, three on the second,
three on this one. What changed is not that the assistant got more careful but
that each round tested a dimension the previous one had not: default screens,
then widget states, then viewport widths. Nothing here was found by re-reading
the code.

## Follow-up 3: attribution, and a risk I had not thought about

I asked it to put my name and zID under the QUOKKA wordmark, and whether that was
even needed. Two things worth recording.

- **It checked before answering.** Neither `SUBMISSION_CHECKLIST.md` nor the brief
  requires a name inside the app, and it said so rather than inventing a
  requirement to justify the work I had just asked for.
- **It raised a second reason I had not considered, and I think it is the better
  one.** The app deploys to a public URL from a public repo and presents as a
  live retail product — a wordmark, "OUR PICK: Combined Min-CVaR", growth-of-$1
  figures, an allocation builder. Someone arriving without the report has no way
  to know it is a university exercise on a frozen 2020–2023 dataset. Attribution
  is a marking convenience; "this is not investment advice" is the part that
  actually matters on a public page. So the byline now does both jobs, and there
  is a standing note in the sidebar (visible on every tab) plus a fuller
  statement at the top of *About & data*: backtests, not tradeable products, past
  backtested performance is not a forecast, no recommendation to buy or sell.

**What I changed:** dropped "Project Part B" from the byline — the course code is
enough, and the extra line made the brand block look like a title page. Kept the
fuller wording in the About tab, where it is a sentence rather than a credit.

It also flagged, without being asked, that a personal name directly under a
wordmark reads as "authored by" and slightly undercuts the trading-terminal
register the design is going for, and that the conventional home for a byline is
the provenance footer. I kept it under the wordmark anyway — the course line
carries it — but I want the reasoning on the record as mine, not overlooked.

## Follow-up 4: the same wrong number was in my planning docs, not just the app

Fixing the app's caption exposed that `OUTLINE.md`'s claim ledger
carried the same bad range — so the report would have inherited
it even though the app was now correct.

Two distinct errors, both worse than "imprecise":

- **A transcription slip.** The ledger read "1.0–2.1pp (1.01/2.13 at q=5%,
  1.01/1.76 at q=10%)". The **1.01 is the q=10% figure written into the q=5%
  slot** — q=5% is 1.23. The number was real, just attached to the wrong row.
- **A wrong-object error, the same shape Phase 8b caught.** Both files quoted the
  **vs-Min-Variance** pairing inside the sentence justifying **Min-CVaR** as the
  recommended fund. The two pairings genuinely differ: **0.94–2.22pp against
  Min-CVaR**, 1.01–2.13pp against Min-Variance. The recommendation argument needs
  the first.

Rewritten from `co_crash_bootstrap.csv` in both files, with all four vs-Min-CVaR
intervals spelled out (RP −1.32 [−1.66, −0.97] and MS −2.22 [−2.95, −1.48] at
q=5%; RP −0.94 [−1.16, −0.71] and MS −1.69 [−2.17, −1.20] at q=10%), the
vs-Min-Variance span kept separately with "do not mix the two in one sentence",
and both not-distinguishable rows stated. Then machine-checked: every CI triple
asserted anywhere in `report/` was matched back against the CSV — **8 of 8
present, 0 mismatches**. The stale string survives only in the passages that
explain what the error was.

Also added **P2b** to the Section 6 plan in `OUTLINE.md`: the verification failure
as evidence pointers with a word-budget note, not as prose. My own words still
have to carry it.

**The lesson I am taking from this one:** fixing a number in one place is not
fixing it. The app, the ledger and the writing guide each held their own copy,
and only the app had a test. Numbers that appear in more than one artifact need a
single source — which is why the app now computes its caption from the file
rather than restating it.

## Follow-up 5: checking the writing guide against the brief found a missing requirement

I asked it to bring `OUTLINE.md` up to date and to make sure everything the
brief asks for is in there. Checking the plan against `PROJECT_BRIEF.md`
line by line turned up two things the guide got wrong about my own deliverables,
and one factual error about my own app.

- **A required fact-sheet element had no artifact behind it.** The brief lists
  six things per fund: growth of $1, annualised return, annualised volatility,
  Sharpe, max drawdown, and current holdings. **Growth of $1 was in no CSV.** It
  existed only inside the app, which recomputes it live from daily returns, and
  in `fusion_before_after.csv` for four funds. Writing twelve fact sheets would
  have meant hand-computing twelve numbers — precisely what this project's own
  rule forbids, and the same failure mode Phase 8b fixed for four other numbers.
  Fixed at the source: `performance_metrics` already computes the cumulative
  product for the drawdown, so it now returns it. **Verified additive** — re-ran
  the pipeline and diffed: only `performance_metrics.csv` changed, only by
  gaining the column, every pre-existing column bit-identical, all 25 other
  artifacts untouched, and the new column matches an independent cumprod to
  2.3e-14. A test now asserts all six elements exist for all twelve funds.
- **The guide called a requirement optional.** Table A5 said "recommended fund's
  16 names; the other 11 funds optional". The brief requires current holdings in
  *every* fund's fact sheet. The data was always there (236 rows, all 12 funds);
  the guide would have talked me out of using it.
- **The guide described my app wrongly.** Section 5 told me to write that the app
  "shares the report's FT style". It does not — it is a deliberately separate
  dark product surface and `streamlit_app.py` imports no `ft_style` at all. The
  same wrong claim sat in `OUTLINE.md`'s locked-decision table. Both corrected,
  and the replacement is better material: the app has a real design system worth
  claiming (hue = method, dash = family, explicit colour, responsive
  breakpoints), which is what the rubric's design band actually asks for.

**What I decided:** keep Section 6 at **700 words**, not the 820 it proposed. The
new P2b is funded by trimming the other paragraphs (150→120, 200→130, 130→120,
220→210) rather than growing the section. The lecturer is flexible on length, but
a budget that moves whenever new material appears is not a budget.

**The pattern worth naming, since it is now three for three:** every time I
pointed this project at a *different* artifact — the screen instead of the code,
the widget states instead of the defaults, the brief instead of the plan — it
found something. Nothing was found by re-reading the same document more carefully.

**Caught by the linter, not by the assistant:** the sidebar disclaimer used
`SURFACE` and `AMBER` without importing them. Ruff's F821 caught it immediately,
which is the argument for the `ruff.toml` added earlier in this session — an
undefined name in a rarely-rendered branch is exactly the kind of thing that
would otherwise surface as a blank page on the deployed app.

---

## Follow-up 6: an independent re-audit of the whole project — and four assistant errors caught inside it

By this point the app had been audited, the docs corrected, and every gate was
green. I wanted a clean-slate check of the entire Part B folder against the brief
rather than another pass over one layer, so I asked for the broadest thing I could
ask for and then kept pushing until nothing was left.

## Prompt(s)

- "run through the entire Project B file to check if there is all satisfy, like
  good to follow every detail in project brief, if all the code are good, if all
  the data used/result is consistent through all the file, if the result, data is
  correct for the project brief and reasonable? do it detailly, take your time"
- "so are you already help me to fix all these problem?"
- "so like everything is clean now?"
- "yes close them all, I will do [the report, the deployment, the README] myself
  after you check that all other things are good"
- "help me to allocate all the figure and table to the propriate place of the
  report section in my report plan and clean the table/figure if they are no need"
- "list out the table or figure that are/may not neccessary that can delete then
  I will decide delete or not"
- "ok delete cost_sensitivity.png then, and run through the project Brief,
  OUTLINE, and REPORT GUIDE last time to check if the REPORT GUIDE and OUTLINE
  are fully consistent/satisfy all the requirement of the project brief"

## What the re-audit found in my work

It re-derived numbers from the raw data instead of trusting my docs. The reassuring
half first: **all twelve funds reconcile from `fund_returns.csv` to 6.3e-15**,
`current_holdings.csv` matches the last weights row for all twelve with zero
mismatches, weights sum to 1.000000 at all 520 rebalances, the sentiment lag is
exact at 0.000e+00 across 1,005 days × 50 tickers, and Part A's four motivating
numbers (25.87% vs 15.50%, −10.77% vs −7.05%) reproduce exactly. **No number in
`results/` was wrong.** Again.

The documentation had drifted, though, and one item was simply false:

- **A factual error, not an imprecision.** `portfolios.py` and `OUTLINE.md` both
  said pandas' `bias=False` differs from my EWMA covariance by **6.75%**. It is
  **0.40%** — the Bessel-style factor `1/(1−Σw²)`, which at span 252 is 1.00399.
  6.75% corresponds to a span of roughly **17**, so it is a short-span number that
  migrated into the span-252 note during the RiskMetrics exploration. Had I quoted
  it, the report would have carried a wrong number attributed to my own code.
- **Two condition-number claims that only reproduce at unstated settings.** "850 at
  span 252" is the value at the **first** rebalance window; the median across the 36
  windows is 1.4e3 and the full-panel value is 658. The "227× shrinkage reduction"
  needs **δ = 0.2, span 32** (δ = 0.1 gives 102×, δ = 0.5 gives 886×). Both are now
  labelled with their window and intensity, and both are flagged as Provenance
  notes — my guide claimed there were two such notes; there are four.
- **A wrong-object slip of exactly the kind this project polices.** "0.95 leaves
  12.6→50.3 tail scenarios" — 50.3 is the count on the **full panel**, not at the
  last estimation window, which is **49.4** (T = 987). And the co-crash
  reconciliation denominator is 1,005, not the 1,006 my guide had.
- **An overclaim in the app.** The About tab said "the Sharpe ranking never
  reorders across that grid". True **within** each family, false across all twelve:
  at 50 bps Equity-Only Min-Variance drops below Combined Max-Sharpe, having led by
  0.002 at 20 bps.
- **Three of my own non-negotiable rules had no test that could fail.** This is the
  finding I care most about — see the next section.
- **Figure defects only visible by looking.** `sentiment_index.png`, a required
  exhibit, had **no y-axis label at all**, and its subtitle promised "gaps =
  no-headline sector-days" when the 21-day rolling mean bridges every gap, so there
  are none. `performance_sharpe_bar.png`'s title said "Risk parity wins on Sharpe"
  while its own two tallest bars are Crypto-Only funds. `co_crash_panel.png`, the
  headline exhibit, was the only figure with no sample period.
- **A silent-degradation path in my own pipeline.** `lexicon.py`'s `REVIEW_PATH`
  was the one relative path in the codebase. Run `run_part_b.py` from any other
  directory and it writes a fresh all-"pending" review file somewhere else,
  `extend_terms` finds zero keeps, and the run **silently falls back to
  `PROVISIONAL_ai_only`** — flipping the `mode` column my report cites as
  "human-reviewed", while installing the identical 28 terms. A wrong provenance
  label that no gate would catch. Now anchored to the project root.
- **Selective reporting I had not noticed.** The lexicon extension sharpens OXY
  (0.074→0.055) and BCH (0.183→0.151), which my docs quote — but the **COVID week
  drifts the wrong way, 0.2346→0.2386**, and nothing mentioned it. In a report
  whose credibility rests on volunteering results that went against me, quoting two
  of three movements was the one place Section 4 could fairly be called
  cherry-picked.
- **The comfortable half of a limitation.** My docs said the thinnest sector
  "averages 2.84 of 5 active tickers". True — but `min_tickers` is **1 for nine of
  the ten sectors**, and RealEstate rests on a single ticker on **16.2%** of its
  covered days. The mean was stated; the floor was not.
- **A requirement the brief names and I had answered without recording.** The brief
  warns that "about half of finance headlines score neutral with plain VADER, and a
  sentiment of zero is not 'no information'". Measured on all 105,330 distinct
  headlines: **48.09% neutral under plain VADER against 16.00% under finVADER**,
  with **34,662 of 50,654** silent headlines rescued. That is the strongest
  justification for my model choice, it confirms the brief's own warning on my own
  data, and it existed nowhere. Now `sentiment_neutrality.csv`.

## The technique that actually found things: mutation testing

I had 21 passing tests and a green lint. Rather than read them, the assistant
**injected six deliberate defects and re-ran the suite**. Three passed clean:

| Injected defect | Result before |
|---|---|
| `CALENDAR["Crypto-Only"] = 252` | **21 passed** |
| Delete the `lag < 1` guard in `fusion_signal` | **21 passed** |
| `FAMILY_CAPS["Crypto-Only"] = 0.10` | **21 passed** |

The first two are rules 1 and 2 in my own `CLAUDE.md`, described there as
non-negotiable. The calendar one is the worst: it would have inflated every
Crypto-Only Sharpe by √(365/252) = 1.20× on the next re-run, and nothing would
have gone red — the tests never re-run the pipeline, and the app reads the
committed CSV rather than the constant. It is the same defect class as the
allocation-blend bug earlier in this session, which I fixed **in the app and never
pinned in the engine**.

Five tests added; all six mutations now fail. The suite is 26.

## What the assistant got wrong — four errors inside an audit about correctness

- **It omitted a finding from its own audit report.** It noticed on its first read
  that `_solve_long_only` is annotated `-> np.ndarray` but returns
  `tuple[np.ndarray, bool]`, said so in its working, and then left it out of the
  write-up it gave me. It only surfaced when I asked "so like everything is clean
  now?" — so the gap was in its *reporting*, not its analysis, which is the harder
  kind to notice from the outside.
- **It broke my own quote-the-CSV rule while enforcing it.** It wrote the VADER
  neutrality numbers into `OUTLINE.md` from its own scratch script — 47.99%,
  50,549 neutrals, 34,602 rescued, 7,506 terms. When the pipeline ran, the saved
  CSV said **48.09%, 50,654, 34,662, 7,502**. Cause: the scratch run scored the
  baseline with the separately-installed `vaderSentiment` package, while the
  pipeline uses finVADER's own analyser class (nltk's VADER, 7,502 terms) so that
  the comparison isolates the lexicon rather than the implementation. It caught
  this only because it re-read the saved file afterwards. The whole Phase 8b lesson
  was "quote the CSV, never a transcript", and the thing enforcing that rule
  violated it in the same session.
- **It put a non-ASCII identifier in my hand-in checker.** Editing
  `check_handin.py` it wrote `докс = ...` — Cyrillic — instead of `docx`. Ruff did
  not catch it, because I deliberately ignore RUF001 so the prose en-dashes in my
  figure titles pass. It caught it on re-read and I verified zero non-ASCII
  identifiers remain, but a Cyrillic variable in a submitted script would have been
  a strange thing for a marker to find.
- **It clipped two figures it was in the middle of fixing.** Adding the missing
  sample period and axis information pushed both subtitles past what `ft_header`
  can fit — that function is the frozen Part A port and does not wrap — so
  `sentiment_index.png` rendered "…so the thinnest sec" and `co_crash_panel.png`
  "…out of 753 out-o", cut off at the canvas edge. Invisible in the code, obvious
  in the PNG. It found them by rendering and looking, which is the same lesson as
  the 100× bug two sections up: **the render layer only fails on inspection.**

## What I decided

**Fix everything mechanical first; write the report, deploy, and rewrite the README
myself.** I said this at the start and held to it. Two of those three are my own
work under the course AI policy anyway, and I did not want to be drafting prose
while still wondering whether a number underneath it was wrong. Sequencing, not
delegation.

**Delete one figure, not the three it offered.** It listed `cost_sensitivity.png`,
`weights_stacked_min_cvar.png` and `co_crash_panel.png` as technically unused, and I
took only the first. Every value that figure plotted is a column of
`performance_metrics.csv` which I print in full as Table A1 — a figure duplicating a
table earns nothing. I **kept** `weights_stacked_min_cvar.png` on purpose: the
brief's weights requirement reads two ways, and that figure is the one that covers
"portfolio weights over time" rather than one asset's weight across methods. Cheap
insurance on a *required* exhibit is worth an appendix slot. `co_crash_panel.png`
was never a candidate — Section 4 is built on it.

**I was wrong about what deleting achieves, and I would rather record that than
quietly drop it.** I asked which exhibits to cut "to short a bit of the main text
page count". Deleting an artifact saves zero pages: the page count follows what is
*printed*, and a file that nothing prints costs nothing. The reallocation had already
banked the saving before I started asking about deletion. If I had not been
corrected I would have kept cutting things for no benefit and lost evidence doing it.

**Body cut to 7 figures + 4 tables.** All seven brief-required exhibits stay,
plus the co-crash panel. Everything else goes to the appendix or into prose. My rule
for the split: if two or three numbers carry the argument, print no table — name the
file and quote them.

**Rebuild Table 1 so one table does two jobs.** It is now
`performance_metrics.csv` joined to a holdings count, which satisfies the required
metrics table *and* all six fact-sheet elements for all twelve funds at once. Worth
noting how that came up: the old plan spread those six elements across four tables,
and its body table was **missing growth of $1 and holdings entirely** — so the
fact-sheet requirement was still only half-met by the plan I had rewritten earlier
the same day specifically to fix it. Table A13 retired as a third copy; Table A5
condensed from 236 printed rows to 12.

**Keep the thin-sector floor and the COVID-week drift in the report.** Both make my
work look slightly worse. Both stay. The whole argument of Section 4 is that I report
what the data did rather than what I hoped, and I cannot make that argument while
quoting two of three event movements.

## The pattern, now four for four

I have now done this four times and it has worked four times: point the project at a
**different artifact** and it finds something. The screen instead of the code. Widget
states instead of the defaults. The brief instead of my own plan. And this time,
injected defects instead of the passing test output. Re-reading the same document
more carefully has not once found anything.

That is the honest version of my Section 6 argument, and it is now an observation
with four instances rather than a slogan: a test can only fail on the dimension it
observes, so "all checks pass" tells me how much my checks cover, not whether the
work is right. The 21 green tests were true and the calendar rule was untested at the
same time, and there was no way to see that from the test output.

**Final state:** `ruff` clean with no flags, 26/26 tests, `check_handin.py` 22/22.
A full pipeline re-run left **26 of 27 artifacts bit-identical**; the only changes
were the four figures whose captions I deliberately fixed, two additive columns in
`sentiment_coverage.csv` (every pre-existing column proven identical against a
pre-edit copy), one new CSV, and one deleted figure. Requirement sweep: **42 of 42**
brief requirements traceable in `OUTLINE.md`.
