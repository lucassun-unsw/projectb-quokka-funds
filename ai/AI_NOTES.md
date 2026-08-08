# AI notes — how I used AI on Part B (z5594806)

## Tool and setup
- Assistant: Claude Code, opened only on my `z5594806_projectA` and
  `z5594806_projectB` folders — never the whole `fins-agent` repo, never
  another student's folder.
- My instructions live in `CLAUDE.md` (and a short `AGENTS.md` pointer),
  adapted from my Part A version and extended with the Part B-specific traps
  (fund calendar mismatch across three asset families, sentiment lag, the
  EWMA-covariance rule, the `.gitignore` cache trap I found the hard way — see
  `prompt_log_01_partB_plan.md`).

## How I direct and check it
- I lock the plan in `report/OUTLINE.md` before writing code — same discipline
  as Part A's `OUTLINE.md`-first approach, which worked well there.
- I push back on proposals I'm not convinced by rather than accepting the
  first answer — the planning session (`prompt_log_01`) is mostly a record of
  me asking "does this repeat Part A?", "is this actually safe?", "which
  option is genuinely better?" until the plan held up, not of a plan I
  accepted as given.
- I keep the interpretation writing to myself — the assistant drafts code and
  report *structure* only, never the analysis prose I submit.
- Before treating a ported or generated module as done, I ask for a live
  check against real data, not just an import check — see `prompt_log_01` for
  the source-port verification (reproduced Part A's exact frozen row counts).
- I re-read Part A's own `ai/AI_NOTES.md` before starting Part B specifically
  to carry its costly late-caught mistakes forward as upfront checklist items
  instead of rediscovering them (`report/OUTLINE.md`'s "Verification
  checkpoints" section).

## About these logs
The prompt logs are drafted by the assistant at the end of each task, at my
direction, and I review and edit them — that is itself AI use and I am
disclosing it. Facts in the logs (prompts, outputs, defects, numbers) come
from the session transcripts; the checks described ran in my sessions and I
reviewed their output. The judgments and decisions recorded as mine are mine.

## Running log of what AI got wrong / what I fixed
- Planning session: the assistant's first EVT (POT/GPD) proposal repeated a
  finding Part A's `dependence.py` already established (Gaussian vs empirical
  ES) under a new name; I caught the overlap by asking directly, not because
  the assistant flagged it. Dropped. (see prompt_log_01)
- Planning session: an ARIMA-as-app-feature idea was framed as safe because
  it wouldn't touch the backtest; it took me raising "no model predicts the
  true value" before the real risk — a misleading point forecast shown
  confidently to a retail user — was named plainly. Dropped in every form.
  (see prompt_log_01)
- Planning session: EWMA was picked for the fund covariance on engineering-
  robustness grounds without first checking whether it was something I'd
  actually studied and could defend; I made the call myself after weighing it
  against GARCH, and cut the standalone GARCH diagnostic too once it was
  clear it wouldn't feed anything required. (see prompt_log_01)
- Planning session: I had conflated the co-crash stress-test panel with a
  third optimisation method; clarified it's an evaluation panel applied to
  funds, not a way of constructing one — the required two-method minimum
  stays max-Sharpe + min-variance. (see prompt_log_01)
- Source port: verified `.gitignore`'s `!results/**` negation would have
  silently committed a scoring cache placed at `results/.cache/` (the
  assistant's own earlier suggestion) — caught by asking it to actually check
  the file rather than assume. Moved the cache to project-root `cache/`.
  (see prompt_log_01)
- Source port: `etl.py`/`features.py`/`text_panel.py`/`ft_style.py`/
  `dependence.py` ported from Part A were verified against a live run, not
  just an import check — reproduced equity 50,300×9, crypto 14,610 rows
  post-cap, and a 60,360-row combined panel, matching Part A's frozen facts
  exactly. (see prompt_log_01)
- Housekeeping session: pushed for a real isolation test rather than trusting
  an earlier "it's independent" claim at face value — copied the whole folder
  to a location with no Part A nearby and ran it cold; held up. Also caught
  that `report/OUTLINE.md`'s Folder layout section had gone stale (still
  described already-finished files as TODO) and fixed it. (see prompt_log_02)
- Follow-up: I'd flagged the finvader/vaderSentiment install as verified only
  in the shared repo `.venv`, a weaker check than the isolation-tested source
  port. Pushed for the same rigor - built a genuinely empty venv, installed
  both requirements files into it, and ran the actual `build_finvader()`
  merge end to end (not just imports). Passed; noted finvader resolved to a
  different patch version (1.0.0 vs the shared venv's 1.0.2), both satisfying
  the `>=1.0` pin.
- Sentiment construction: the previous session's plan cited week 9's
  `daily_index` pattern for the sector aggregation, but that function
  flat-averages headlines, not tickers - it doesn't actually implement the
  brief's "equal-weight the tickers" wording. Caught this by checking the
  brief's exact phrasing against the cited code before writing anything, then
  confirmed with real data that the two aggregation orders diverge materially
  (one ticker holds >=70% of a sector-day's headlines 9.9% of the time), not
  just in theory. Fixed the spec before any code was written. (see
  prompt_log_03)

- Fund parameters: the assistant's first round of options (EWMA span, CVaR
  level, weight cap) came with no external grounding, so I asked it to look up
  what standard practice actually is. That changed two answers — the weight cap
  gained a real justification (the UCITS 10%-per-issuer rule) and the CVaR level
  became a constraint-driven choice rather than a default (Basel's 97.5% ES is
  the regulatory benchmark but our 252-day window leaves only 6.3 tail
  scenarios there, so 95% is what the data supports). (see prompt_log_04)
- Fund parameters: I questioned whether a fund should hold every stock and asked
  the assistant to confirm against the brief. Honest answer: the brief is silent
  — it only says "choose your own constraints". Testing it showed pre-filtering
  the universe would have *hurt* (12.45% realised vol on all 60 assets vs
  12.65–13.72% pre-filtered), and that the long-only optimiser already drops
  most names anyway (min-CVaR held 4 of 60). (see prompt_log_04)
- Fund parameters: **a real bug survived every per-parameter check and was only
  caught by running all 12 funds together.** The locked 10% weight cap is
  degenerate for Crypto-Only — p=10 assets × 10% = 1.00 exactly, so the cap
  forces equal weight and all four Crypto-Only funds came out byte-identical
  (Sharpe 0.9124). Fixed with a family-specific 25% crypto cap, which I asked to
  see run before accepting. Exactly the "individually fine, jointly broken"
  failure the Verification checkpoints warn about. (see prompt_log_04)
- Fund parameters: nobody had tested EWMA against a plain static covariance —
  the comparison the whole "time-series anchor" claim rests on. It wins by only
  0.33pp of annualised vol at ~9× the turnover, and its *return* advantage flips
  sign across years (+0.63 / +2.19 / −1.73pp). Narrowed the report claim to the
  volatility reduction only, and demoted span 126 from "robustness alternative"
  to "tested and rejected". (see prompt_log_04)
- Fund parameters: the assistant's own pre-run hypothesis — that a short EWMA
  span would make the 60-asset covariance singular — was wrong, and the data
  said so. Rank is full at every span; the real cost is conditioning and weight
  instability. Recording it because the diagnostic existed to test a hypothesis
  the data then rejected. (see prompt_log_04)

- Co-crash panel: **the assistant recommended a headline claim two sessions
  running, then its own test disproved it.** It told me to lead Section 4 with
  "min-CVaR wins the worst single crash day in all six family × threshold
  combinations"; when I asked it to actually run the bootstrap, the claim
  collapsed — bootstrapping a minimum is a known failure case, so the interval's
  upper bound is just the point estimate and the comparison rests on effectively
  one observation per fund. It did not flag this when proposing the bootstrap,
  only when reading the output. Retracted. (see prompt_log_05)
- Co-crash panel: a second claim was wrong the other way — the plan said
  min-CVaR "loses" to min-variance on mean crash-day return at q=10%, but the
  paired bootstrap gives a gap of −0.076pp with CI [−0.188, +0.041], straddling
  zero. Neither fund wins; I had been about to report a loss that isn't there.
  Replaced both with the result that does survive resampling: the protective
  pair beats the exposed pair by 0.9–2.2pp per crash day, CIs excluding zero.
  (see prompt_log_05)
- Process fix from the above: added a **claim ledger** to `report/OUTLINE.md`
  listing every number the report may quote as verified / unverified /
  **retracted**, specifically so a later session can't quietly resurrect a claim
  already disproved. (see prompt_log_05)
- Plan review: the assistant judged my innovation "thin" without having read the
  rubric closely. When I asked for a proper check against the brief, the HD
  wording says "any one suffices", credit is for "evidenced original work, not
  for outperformance", and "a careful extension with a negative result,
  explained, still earns this band" — by which the co-crash panel alone is
  HD-shaped. It corrected itself, but only after I asked it to check rather than
  opine. (see prompt_log_05)
- Concept checks: I made a point of asking what the cap, q, the EWMA span and
  the bootstrap actually meant before letting them into the report. Two changed
  how I'll write things up — q is a *joint* threshold on two series and is not
  the same object as β inside the min-CVaR optimiser, and the EWMA span is a
  decay rate (half-life 87 days) not a 252-day window, which collides
  numerically with the 252-day burn-in. Both now flagged in the plan.
  (see prompt_log_05)

- Phase 2-5 build: **a previous session's "verified" cache-location decision
  failed the first time the artifact actually existed.** The plan locked
  project-root `cache/` after checking the `.gitignore` trap — but
  `check_handin.py` scans the filesystem, not git, and failed the hand-in on
  the perfectly-gitignored cache. Verification of one enforcement mechanism
  didn't transfer to the other. Cache moved outside the project
  (`~/.cache/fins3645_z5594806_projectB/`). (see prompt_log_06)
- Phase 2-5 build: the plan's multi-word lexicon install (week 8's
  SPECIAL_CASES two-step) was built on the wrong package's internals —
  runtime inspection showed finvader vendors *nltk's* VADER class, which has
  no such dicts. Revised to single-token installs, hyphenated tokens for
  multi-word ideas, stated openly. Also caught: finvader's convenience
  function rebuilds the whole analyser per call (unusable over 105k
  headlines), and an old plan note had the wrong neutral value ("0.5/50" is
  a 0-100 convention; compound neutral is 0.0). (see prompt_log_06)
- Phase 2-5 build: the claim-ledger discipline paid off — all nine Phase 2
  ledger metrics reproduced to 4 decimals on first run, and the honest
  fusion result (negligible gross, zero-to-negative net of 20 bps at every
  k) was recorded without post-hoc k tuning. The four deliberately-planted
  ambiguous lexicon candidates were all caught by the SD/mean filters — a
  designed filter test that passed. My review of
  `results/tables/lexicon_candidates.csv` is the pending human step.
  (see prompt_log_06)

- App + audit: **the full audit found four defects no automated check had
  caught** — two only visible by opening the PNGs (truncated subtitle,
  ambiguous repeated colours), two by reading the brief/plan against the file
  inventory (fund-name drift vs the locked display-name convention; the
  required current-holdings artifact missing entirely). All fixed and
  re-verified. Also recorded a near-miss: a figure title asserting "the podium
  never reorders" was drafted before the claim was checked — the check then
  confirmed it, but title-first is the risky pattern. (see prompt_log_07)
- Verification sweep: **caught a wrong-object quote before any report prose
  existed** — event-validation percentiles staged for the report were the
  post-lexicon-extension values (OXY 0.055) where the saved CSV holds the
  base-index values (0.074/0.183/0.235). The exact Part A figure-vs-table
  failure mode, caught by the sweep instead of during editing. Also: the
  isolation re-test passed with all 14 CSVs bit-identical from a cold run in
  a projectA-free location, with the honest caveat that the deterministic
  scoring cache (outside any project) was reused. (see prompt_log_07)
- Hand-in checker behaviour, second instance: it greps literal text — the
  app's own docstring *saying* "never imports nltk" tripped the nltk check.
  Reworded. Same lesson as the cache: the checker reads strings and
  filesystems, not imports and git. (see prompt_log_07)

- Pre-writing audit: **the number at the centre of my Section 4 argument was in
  no file at all.** The plan quoted "risk parity loses ~1pp per crash day, CI
  [+0.73, +1.16]", but the saved bootstrap only ever compared funds against
  min-variance. Recomputing showed the interval belonged to the risk-parity
  **vs min-CVaR** pairing — the comparison my recommendation actually needs,
  since min-CVaR is the recommended fund — and that the lower bound was wrong
  as well (0.71). Now a saved row: **−0.94pp, CI [−1.16, −0.71]**.
  (see prompt_log_08)
- Pre-writing audit: **the assistant's own audit finding was itself a
  wrong-object error, the same class it was reporting.** It called "1,106
  headlines" a transcription slip because the CSV says 1,097. Re-running showed
  both are real: 1,106 headlines *contain* an installed term, 1,097 *changed
  score*. It was right that the sentence was wrong and wrong about why. I only
  learned that by running the pipeline — reasoning about it produced a
  confident, incorrect diagnosis. Both counts now have their own CSV columns.
  (see prompt_log_08)
- Pre-writing audit: a figure title claimed the opposite of its own panel — the
  fusion figure said "free lunch gross" while its right-hand bars show
  min-variance at −0.0107 gross, the largest of the four. The exact title-first
  pattern I logged as a near-miss in prompt_log_07; that one survived checking,
  this one did not. Retitled. (see prompt_log_08)
- Pre-writing audit: `CLAUDE.md` rule 9 still said "zero transaction costs"
  eight phases after I built the cost model that is one of my innovation
  strands. My own file says to flag drift against `OUTLINE.md`; nothing did,
  and it is a graded artifact a marker reads. Rewritten. (see prompt_log_08)
- Pre-writing audit: several Section 1 and Section 4 numbers were quoted from
  session transcripts rather than from `results/`, against my own rule. Moved
  into saved tables, and **four changed once reproduced** under the locked
  parameters (static vol 12.78→12.79%, EWMA/static turnover 256/29→263/30%,
  closest method pair 0.066–0.107→0.076–0.150, "48 solves"→520). I did not
  accept the new turnover figure until it was justified — what settled it was
  that `performance_metrics.csv` had held the same 262.5% all along, so the old
  number would have contradicted my own Section 2 table. Two numbers I could
  not reproduce are now marked as prompt-log diagnostics rather than quietly
  kept. (see prompt_log_08)
- Pre-writing audit, second pass over the new code: `method_separation.csv`
  **saturates** — three of six pairs per family land exactly on the weight cap,
  because one method at the cap against another holding zero makes the maximum
  difference equal to the cap by construction. Quoted raw it would read as a
  measured distance rather than a ceiling. Added `at_family_cap` so the artifact
  says so, and quote the closest unsaturated pair instead. A reminder that a
  table can pass every numeric check and still be easy to misread.
  (see prompt_log_08)
- Pre-writing audit: **dropped the four convention citations instead of
  verifying them** — an open loose end since Phase 2. No claim of mine rests on
  a source's authority, so each is now an unattributed convention justified by
  its own evidence. Deleting an unverifiable citation is honest; keeping an
  unverified one is not. (see prompt_log_08)

- Full re-verification after the fixes: **my writing guide gave the wrong reason
  for a retracted claim.** It said the bootstrap "disproved" both retractions;
  in fact it is *invalid* on a minimum, so the worst-day claim was never tested —
  and min-CVaR beats min-variance on that point estimate in 6 of 6 combinations,
  so the claim looks true. Writing "the bootstrap disproved it" would have
  misstated my own method. Each retraction now carries its own correct reason.
  (see prompt_log_08)
- Full re-verification: a no-look-ahead test appeared to fail (1.8e-04 instead of
  zero) and the honest diagnosis took longer than a fix would have. Not
  look-ahead — the optimiser's window was bit-identical; a pandas `.loc` scramble
  changed the array's memory layout, changing the BLAS reduction order, moving the
  covariance by ~1e-18, which a flat min-variance objective amplified. Layout
  fixed, all four methods return exactly 0.00e+00. Kept as a numerical caveat and
  a permanent test rather than quietly rewritten. (see prompt_log_08)

- App design pass: it reported a CSS fix as live and told me to refresh —
  **twice** — for a change a refresh cannot apply. `CSS` is a module-level
  constant, so a Streamlit rerun serves the old string from memory; only a
  server restart picks it up. Worse, the "verification" was an assert run in a
  *fresh subprocess*, which proves the file on disk changed and says nothing
  about the running app. A check that passes regardless of the thing it claims
  to test is not a check. (see prompt_log_09)
- App design pass: asked it to **change the sidebar back**; it reverted, then
  after I said nothing changed it trimmed the sidebar *below* Streamlit's
  default. I kept that — it looks better — but it is a third design, not the old
  one restored, and it arrived without being named as a new decision.
  (see prompt_log_09)
- App design pass: brightening the theme **broke a panel that had been fine**.
  Lightening `greenColor` against a near-white `textColor` collapsed the
  contrast Streamlit derives for `st.success`, and the "hosted data, live" box
  rendered as an empty rectangle. Overriding half a design-token set leaves
  every framework-derived component computing contrast from inputs nobody
  checked together. Fixed by drawing the banner with explicit colours, the way
  every other panel in the app already does — which is why nothing else broke.
  The root cause is **inferred, not observed** (it could not see my screen), and
  it said so instead of claiming the fix worked; a second, provable cause — a
  cached loader with `show_spinner=False` leaving the panel blank for ~3s — was
  fixed alongside it. (see prompt_log_09)

- Full app audit: **every percentage in every table rendered 100x too small, and
  two of my own verification passes could not have caught it.**
  `st.column_config`'s `format` is printf, not a percent directive, so `"%.1f%%"`
  on the stored 0.0826 printed "0.1%". Eleven of the twelve funds showed "0.1%"
  annual return; the co-crash panel — my Section 4 headline — read −0.02% instead
  of −1.85%, contradicting its own caption; the page header said +8.26% while the
  table below said 0.1%. Phase 7 ("AppTest 0 exceptions") and Phase 8 (wiring to
  6.3e-15) both passed throughout, because **AppTest asserts the script runs, not
  what the screen shows**, and the values passed in were correct all along. The
  bug lived only in the render layer, the one layer neither check touched.
  (see prompt_log_10)
- Full app audit: the direct cause was that nobody had looked. The assistant had
  no screen access through Phase 7 and the log 09 design pass and reasoned about
  the UI from source; given a browser it found this in the first screenshot. It
  also found "16 of 60" quoted for families that pick from 50 and 10, and the
  allocation blend annualising a crypto-only portfolio with sqrt(252) — my own
  rule 2, understating its volatility by a fifth. (see prompt_log_10)
- Full app audit: two of its own steps were checks built so they could not fail —
  the same shape as log 09's fresh-subprocess assert. It guessed 35px table rows
  and produced a table padded with blank rows (fixed by measuring the DOM: 28px),
  and its first fragment benchmark returned ~2,527 ms for every variant because
  the number was its own `wait_for_timeout(2500)`. It caught both from the
  output looking wrong, not from the check failing. (see prompt_log_10)
- Lint sweep: 39 Ruff findings cleared, but three sat in `src/data_access.py`
  (provided) and `src/etl.py` (frozen). Took narrow, commented per-file ignores
  in a new `ruff.toml` rather than reformatting files whose whole value is being
  unchanged. For the other 36 — in the files that generate every number I quote —
  I required a full `run_part_b.py` re-run and a checksum diff: **all 14 CSVs and
  9 PNGs bit-identical**. (see prompt_log_10)
- Tabs converted to `st.fragment` and the gain **measured, not claimed**: a fund
  switch went from 8 figure renders to 5 (page load unchanged at 6). Partial, and
  recorded as partial. Added `tests/test_app.py` so the display layer is tested
  on displayed values — the missing test class is the actual fix.
  (see prompt_log_10)

- Asked "so the app is all good now?" and got three more defects instead of a
  yes — it tested the widget states it had not reached rather than answering from
  what it had just fixed. Dragging every allocation slider to 0 (reachable: they
  bottom out at 0) printed **Sharpe "nan"**. `co_crash_bootstrap.csv` was loaded
  and never used while the caption beside it quoted **"1.0–2.1pp" as typed prose**
  — breaking my own "every percentage in prose must be a literal value in a saved
  CSV" rule, and wrong: the file spans **0.94–2.22pp**. The same stale range sits
  in `OUTLINE.md`'s ledger and is now flagged there for Section 4.
  (see prompt_log_10)
- **Third instance of a check that could not fail.** One of the new tests used
  the shared module fixture; an earlier test renames the sliders it was setting,
  so it set nothing and passed against a normal page. Mutating tests now build
  their own app instance. The pattern across logs 09 and 10 — a fresh-subprocess
  assert, a benchmark timing its own sleep, a test disarmed by fixture order — is
  that a passing check means nothing until you have confirmed it can fail.
  (see prompt_log_10)

- Narrow-viewport pass (390/768/1280px) found three more, one of them a
  **regression introduced earlier the same day**: `initial_sidebar_state=
  "expanded"` was added for a good desktop reason, but below ~768px Streamlit
  overlays the sidebar rather than pushing the page, so on a phone it covered the
  tab strip and **all four non-default tabs were unreachable**. Also: the
  four-column stat grid pushed its fourth column's *values* off-panel (labels
  with no numbers), and `st.columns(len(chosen))` gave ~100px sliders when all
  twelve funds were blended — a desktop bug found only by testing a full basket.
  (see prompt_log_10)
- The pattern across three rounds of "is it all good?": eight defects, then
  three, then three. Each round tested a dimension the previous one had not —
  default screens, then widget states, then viewport widths. **None of it was
  found by re-reading the code.** Worth stating plainly in Section 6: my
  verification kept passing because it kept measuring the same dimension.

- Asked it to add my name/zID to the app and whether that was even needed. It
  checked the brief and `SUBMISSION_CHECKLIST.md` first and said plainly that
  neither requires it — then raised a better reason than the one I had: the app
  deploys **publicly** and reads as a live retail product (wordmark, "OUR PICK",
  growth-of-$1, an allocation builder), so a stranger has no way to know it is a
  university exercise on a frozen dataset. Attribution is a marking convenience;
  **"not investment advice" is the part that matters on a public URL.** Added as
  a byline plus a standing sidebar note and a fuller statement in *About & data*.
  I dropped "Project Part B" from the byline — the course code is enough.
  (see prompt_log_10)
- Same task: Ruff caught an undefined name (`SURFACE`/`AMBER` used in the new
  sidebar disclaimer, never imported) that the assistant had not noticed. On the
  deployed app that is a blank page in a branch nobody renders locally — a
  concrete payoff for the `ruff.toml` added earlier the same session.
  (see prompt_log_10)

- Fixing the app's crash-day caption exposed the **same wrong range sitting in
  `OUTLINE.md`'s claim ledger** — so the report would have
  inherited it even with the app corrected. Two errors, not one: **1.01 was the
  q=10% figure transcribed into the q=5% slot** (q=5% is 1.23), and the ledger
  quoted the **vs-Min-Variance** pairing inside the sentence recommending
  **Min-CVaR** — the same wrong-object trap Phase 8b caught. Correct ranges:
  **0.94–2.22pp vs Min-CVaR**, 1.01–2.13pp vs Min-Variance. Rewritten from the
  CSV and machine-checked: 8 of 8 CI triples in `report/` matched, 0 mismatches.
  **Fixing a number in one place is not fixing it** — the app, the ledger and the
  writing guide each held a copy and only the app had a test. (see prompt_log_10)

- Checking `OUTLINE.md` against `PROJECT_BRIEF.md` found **a required
  deliverable with nothing behind it**: the brief names six fact-sheet elements
  per fund and **growth of $1 was in no CSV** — only inside the app, which
  recomputes it live. Twelve fact sheets would have meant twelve hand-computed
  numbers, breaking my own rule. Added `growth_of_one` to
  `performance_metrics.csv` at the source and proved it additive (only that file
  changed, only by gaining the column; 25 other artifacts bit-identical; column
  matches an independent cumprod to 2.3e-14). The guide had also called holdings
  for 11 of 12 funds "optional" when the brief requires all of them, and told me
  to write that the app shares the report's FT style — **it does not**, it is a
  separate dark surface importing no `ft_style`, and the same wrong claim was in
  `OUTLINE.md`. (see prompt_log_10)
- Kept Section 6 at **700 words** rather than the 820 proposed: P2b is funded by
  trimming the other paragraphs. The lecturer is flexible on length, but a budget
  that grows whenever new material appears is not a budget. My call, recorded as
  mine.
- **Three for three:** pointing the project at a *different artifact* — the
  screen instead of the code, widget states instead of defaults, the brief
  instead of the plan — found something every time. Re-reading the same document
  more carefully never did. That is the Section 6 thesis in one line.

- **A number in my own code was simply wrong, and it was mine to catch.** I asked
  for a clean-slate re-audit of the whole folder. `portfolios.py` and `OUTLINE.md`
  both claimed pandas' `bias=False` EWMA covariance differs from mine by **6.75%**.
  It is **0.40%** — the factor `1/(1-sum(w^2))`, which at span 252 is 1.00399.
  6.75% is that factor at a span of about **17**, so a short-span number from the
  RiskMetrics exploration had migrated into the span-252 note and sat there through
  three earlier verification passes. Nothing in `results/` was affected; had I
  quoted it, the report would have carried a wrong number attributed to my own
  code. (see prompt_log_10, Follow-up 6)

- **Reproducible is not the same as quotable.** Two condition-number claims only
  reproduce at settings I had not written down: "850 at span 252" is the *first*
  rebalance window (median 1.4e3, full panel 658), and the "227x shrinkage
  reduction" needs **intensity delta = 0.2, span 32**. Both now carry their
  setting. My guide said there were two Provenance notes; there are four.

- **Mutation testing beat reading the tests.** I had 21 passing tests and a green
  lint. Instead of reviewing them, the assistant injected six deliberate defects
  and re-ran. **Three passed clean** — setting the Crypto-Only calendar to 252,
  deleting the sentiment lag guard, and restoring the degenerate crypto cap. The
  first two are rules 1 and 2 of my own `CLAUDE.md`, described there as
  non-negotiable. The calendar one would have inflated every Crypto-Only Sharpe by
  sqrt(365/252) = 1.20x on the next re-run with nothing going red, because the
  tests never re-run the pipeline and the app reads the committed CSV rather than
  the constant. **It is the same defect class I had fixed in the app that morning
  and never pinned in the engine.** Five tests added; all six mutations now fail;
  suite is 26. (see prompt_log_10, Follow-up 6)

- **The assistant made four errors inside an audit about correctness.** Recording
  them because they are the most useful thing in this log: (1) it found the
  `_solve_long_only` return-type mismatch on its first read and **left it out of
  its own write-up** — the gap was in its reporting, not its analysis, which is the
  hard kind to spot from outside; (2) it wrote VADER-neutrality numbers into
  `OUTLINE.md` from a scratch script (47.99% / 34,602) that disagreed with the
  saved CSV (**48.09% / 34,662**) because the scratch run used a different VADER
  lexicon — **it broke my quote-the-CSV rule while enforcing it**; (3) it wrote a
  Cyrillic identifier `докс` into `check_handin.py`, which Ruff cannot catch
  because I deliberately ignore RUF001 for my figure prose; (4) it clipped two
  figure subtitles past the canvas edge while fixing those same figures, visible
  only by rendering the PNG. Every one was caught by checking output rather than
  by reasoning about it.

- **I had reported the flattering half of two findings.** The lexicon extension
  sharpens OXY and BCH but the **COVID week drifts the wrong way, 0.2346 ->
  0.2386**, and no doc mentioned it. And "the thinnest sector averages 2.84 of 5
  tickers" is true while `min_tickers` is **1 for nine of ten sectors** —
  RealEstate rests on one ticker on **16.2%** of its covered days. Both now stated.
  In a report whose credibility comes from volunteering results that went against
  me, quoting two of three movements was the one place Section 4 could fairly have
  been called cherry-picked.

- **A silent-degradation path I had built myself.** `lexicon.py`'s review-file path
  was the one relative path in the codebase. Run the pipeline from any other
  directory and it writes a fresh all-"pending" file elsewhere, finds zero keeps,
  and **falls back to `PROVISIONAL_ai_only`** — flipping the `mode` column my
  report cites as "human-reviewed" while installing the identical 28 terms. A wrong
  provenance label that no gate would have caught. Anchored to the project root.

- **The brief had already told me the answer to a question I never recorded.** It
  warns that "about half of finance headlines score neutral with plain VADER".
  Measured on all 105,330 distinct headlines: **48.09% under plain VADER against
  16.00% under finVADER**, with **34,662 of 50,654** silent headlines rescued. The
  strongest justification for my model choice, confirming the brief's own warning
  on my own data, and it existed nowhere. Now `sentiment_neutrality.csv`.

- **Exhibits: I cut one artifact, not the three offered.** Deleted
  `cost_sensitivity.png` because every value it plotted is a column of
  `performance_metrics.csv` that I print as Table A1 — a figure duplicating a
  table. **Kept** `weights_stacked_min_cvar.png`: the brief's weights requirement
  reads two ways and that figure covers the stricter reading, which is cheap
  insurance on a *required* exhibit. The assistant also corrected my premise —
  deleting artifacts saves **zero** pages, since page count follows what is
  printed, not what exists. Body is now 7 figures + 4 tables, and body Table 1 was
  rebuilt to carry all six fact-sheet elements for all twelve funds; the previous
  plan spread them across four tables and its body version was **missing growth of
  $1 and holdings entirely**. (see prompt_log_10, Follow-up 6)

- **Four for four.** Every time I pointed this project at a *different artifact* it
  found something: the screen instead of the code, widget states instead of
  defaults, the brief instead of the plan, and injected defects instead of passing
  test output. Re-reading the same document more carefully has never once found
  anything. That is the Section 6 thesis, and it is now an observation with four
  instances rather than a slogan.

- **On this log.** The assistant drafted these entries and Follow-up 6 of
  `prompt_log_10` from the session transcript; I reviewed them, corrected the
  framing, and the decisions recorded are the ones I actually made. Same division
  of labour I use for the lexicon: it proposes, I decide, and the decision is
  written down as mine.

- **CSS fails silently, and my whole test suite is blind to it.** Restyling the
  app against a documented token system, the assistant wrote a pinned
  frosted tab strip, reported it delivered, and passed `ruff` and **26/26 tests**.
  It did not stick at all. A `position: sticky` element can only travel inside its
  parent's box, and that parent measured 53.72px — the strip's own height — so it
  scrolled straight off. No exception, no warning, nothing a test can assert on.
  Found only by screenshotting a real browser *after scrolling*, and fixed by
  querying the computed style of every ancestor instead of guessing twice. **Fifth
  instance of the pattern**: point the project at a different artifact and it finds
  something. The same screenshot pass also caught a rendering defect that has
  presumably always been there and that my Phase 8c app audit missed entirely —
  Streamlit floats each dataframe's hover toolbar, with no background, straight
  through the panel caption underneath it. (see prompt_log_11)

- **It offered me a rollback that does not exist.** While recommending changes to
  my one working app, the assistant said `git checkout` would revert them.
  `z5594806_projectB/` is not tracked by the repo and has no `.git` of its own. It
  discovered this later, by accident. A confident safety net that is not there is
  worse than being told there is none, and it is the reason I now take a file
  snapshot before any pass that touches the app.

- **I made it prove two claims rather than accept them.** The
  `prefers-reduced-motion` block was reported as working: I had it measured in a
  real browser under both settings, transition duration `0.22s` → `1e-05s`.
  Regenerating one figure label meant re-running the whole pipeline: I had
  `results/` checksummed before and after, and exactly one of 29 files changed.
  Both are the Phase 8d lesson applied to a cosmetic pass — an unfalsified check
  is not a check. (see prompt_log_11)

- **It gave my design system a source that did not survive checking.** My
  planning docs, my own `app_theme.py` and `OUTLINE.md` all said the app's
  surface came from "a published, citable design language", naming a technology
  company, and told me to write that in Section 5. Asked to verify what was
  actually citable, it found every distinctive token came verbatim from a
  third-party GitHub reconstruction of that company's *marketing site*, a file
  self-declaring "version: alpha" — and the company publishes adaptive semantic
  tokens, not fixed hex values, so the palette was never theirs to cite. Same
  failure as Part A's cited tickers that did not exist: a specific,
  checkable-sounding attribution nobody had checked. A full app audit and an
  independent re-audit both missed it because both asked whether the *code* was
  right, never whether a *source* was real. **Sixth instance of the pattern** —
  the different artifact this time was the citation, not the screen.

- **I deleted the claim rather than citing it weakly.** The honest fix was to
  cite the reconstruction for what it is; I chose instead to strip every brand
  name from the project and describe the system on its own terms. Nothing about
  the app changed, only the claim. The rubric wants "an original design system",
  and the borrowed palette was never the part that earned it — hue = method,
  dash = family (twelve pairs pinned by a test), colour never derived, the accent
  decoupled from every series, reduced-motion measured. Dropping the attribution
  made Section 5 easier to defend, not weaker.

- **It built the whole product and left out the business.** Asked whether the app
  met the brief's description of an investment product, it found five of seven
  items present and two missing outright: **no management fee anywhere** in the
  app, code or CSVs, and no statement of the market gap that
  `PROJECT_BRIEF.md` line 101 requires. I had modelled transaction costs
  carefully and mistaken that for modelling the business — transaction cost is
  what the fund pays to trade, a management fee is what my company charges the
  user. Eight phases of verification asked "is this number right?", never "is
  this product a business?".

- **I set the fee myself and took the cheap version deliberately.** Of three
  options I chose display-only at **0.35% p.a.** — charged in the app, never
  inside `oos_backtest`, so `results/` is unchanged and still the right object
  for comparing strategies; a fee is a platform charge on the investor, not a
  cost the strategy incurs. Deducting it in the backtest would have invalidated
  every quotable number in `OUTLINE.md` for no analytical gain. 0.35% sits
  above a broad-index tracker (~0.20%) and below an active crypto mandate
  (~0.50%). Drag: −1.04% on the 252-day funds, −1.15% on Crypto-Only.

- **The fee reintroduced the calendar trap somewhere none of my tests looked.** A
  fee is a rate per *year*, so it accrues at f/252 or f/365 — charging 252
  everywhere overcharges a crypto fund by ~45%, the same √252-vs-√365 rule I
  already had three tests for. Three new tests cover it and I did not trust them
  green: deleting the fee turned 2 red, hardcoding 252 turned 1 red, then I
  restored. Suite 26 → **29**. Phase 8d again — a check nobody has seen fail is
  not yet a check.

- **Its sweeps were narrower than the word "verified" implied.** Told the `ai/`
  pack was aligned with my rewritten `OUTLINE.md`, I asked it to check properly:
  it then found a section reference four files point at, `CLAUDE.md` included,
  that had not existed since the section was renamed. Twice more the first sweep
  reported clean and missed things — a pattern searching for "design *language*"
  where the text said "design *system*", and a brand sweep that only covered the
  names it expected. The lesson is about my prompts as much as its answers: "is
  this clean?" is not the same question as "what did you actually search for?".

- **It deleted four real exhibits while removing a planning marker.** Drafting the
  report body, the assistant cleared a section's marker with a "delete everything
  between the two headings" step that also removed Figures 1–4 and Table 1's
  caption — real embedded figures, not just the marker. No test caught it; I found
  it only by having the document's raw structure dumped. Recovered from the source
  images still in `results/figures/` and re-inserted with the same Word field
  pattern. After that I required the structure verified and the exhibit inventory
  re-counted before every save, and no paragraph-range deletes in a document that
  mixes markers with real exhibits. (see prompt_log_12)

- **It diagnosed my equations from flattened text and was wrong twice.** Reading
  the equations as plain concatenated characters — which drops every fraction
  bar, bracket and accent — the assistant claimed the turnover equation had lost
  its absolute-value bars and that the tilt equation was circular. The real OMML
  showed both were there: the `|·|` bars were present and the tilt's left side
  carried an accent distinguishing it from the base weight. Only two equation
  problems were real, a dropped closing parenthesis in the Min-CVaR denominator
  and a mix of ω and w for weights. You cannot judge an equation from the text it
  flattens to — you have to read the structure. (see prompt_log_13)

- **The CSV number-check caught an overstatement I would have shipped.** My
  Section 2 draft said a Risk Parity investor accepts "Max-Sharpe-like
  drawdowns". Pulled from `performance_metrics.csv`, Risk Parity's max drawdown
  is −20.5%, not near Max-Sharpe's −34.6% — its real trade-off is weaker
  crash-day protection. It also caught a theory slip in Section 1 where I called
  Equal Risk Contribution "allocates weights evenly", which is 1/N, not risk
  parity. Both were mine; both are why the content read is worth doing on prose,
  not just numbers. (see prompt_log_13)

- **A full-document audit caught two structural faults no section check saw.**
  After all six sections were in, a whole-report pass found that two body-table
  captions still cross-referenced the old appendix numbering ("Table A5", "Table
  A4") — pointing at tables that no longer existed after I renumbered to a
  continuous 1–14 sequence — and that three appendices (E, H, I: the full
  co-crash bootstrap, the fusion k-grid, the lexicon tables) had no reference
  anywhere in the body, which my own rule calls dead weight. Fixed the stale refs
  and added a cross-reference to each. Same shape as the render bug: the numbers
  were right and the exhibits were real; what was wrong was whether the document
  connected them. On the app section it also caught a five-vs-four tab miscount
  (the disclosure lives in the fifth tab) and a missing deployment sentence.
  (see prompt_log_13)

- **A design claim is only safe once it is code-provable, and one of mine was a
  wording trap.** Writing Section 5, I had the assistant read the app source to
  confirm every design claim before it reached prose — the interaction accent,
  the 5.6:1 contrast, the 300/400/600/700 weight ladder with 500 deliberately
  absent, the measured reduced-motion transition — because a design system
  described from memory is the same kind of checkable-sounding, unchecked claim
  that produced the brand-attribution failure two sessions earlier. It also
  caught a trap of my own: I had listed the tested viewport widths
  (390/430/768/1280/1600px) as if they were the CSS breakpoints, which are
  actually 900px and 520px, so I restated the widths as "verified at those
  widths" and kept the breakpoints as their own fact. The five-vs-four tab
  miscount and the missing deployment sentence from the same app pass are in the
  audit note above. (see prompt_log_13)

- **A live deploy failed in a way no local test could see.** The Streamlit
  Cloud build resolved a different `streamlit` version than my pinned local
  `.venv`, and the deployed tab strip rendered plain underline tabs instead of
  the pills `app_theme.py` styles — the CSS selector targets Streamlit's
  internal DOM, which changes between releases. Pinned `requirements.txt` to
  the exact version the app was visually audited against. Also lost half a
  `gh repo create` command to a terminal line-wrap and did not notice the
  repo was empty until checking GitHub directly. (see prompt_log_14)
- **I fixed Figure 9 and the fix did not take.** I inserted a screenshot for
  the deployed-app figure and exported `report.pdf`, believing it done. A hash
  check of the embedded image against the one flagged earlier in the same
  session showed it was byte-identical — I had not actually replaced it, and
  both the docx and the exported PDF still showed the wrong tab (*Compare
  funds*, not the *Fact sheet* tab the caption promises). Caught only because
  the check compared the image's actual content against the caption's
  specific claim, not by re-reading the document. (see prompt_log_14)

## Individual prompt logs
See the `prompt_log_*.md` files in this folder, one per task.
