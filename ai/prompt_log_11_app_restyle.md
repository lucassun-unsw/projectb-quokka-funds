# Prompt log — app restyle (tokens, motion, prose)

## What I wanted
The app was finished and working, but its look was my own invention rather than
anything with a stated design language behind it. I wanted to restyle it against
one documented token system rather than per-widget choices, and I cared most
about the parts you feel rather than see: the transitions, the press feedback,
the way the chrome behaves when you scroll. I also wanted the notation and the
wording tidied: proper subscripted risk-free rate, and no dashes interrupting
sentences.

## Prompt(s)
- "now back to Project B, I want to do some change of the UI of the apps"
- "I will tell you what to do, nothing for now, just know what is the app now"
- "or if possible like we do the style again? this is nothing about ft_style,
  that is for the report, we are focusing on apps. I want to do something like
  a proper product style for the apps, like its transition, style something
  like that"
- "give me advice before you actually do it"
- "so what is your recommendation?"
- "go ahead with pass 1"
- "fix everything and then go to pass 2, no need to write the 'Choose a section ↓'
  looks not good"
- "and all the rf=0 to proper r small f = 0 not just rf"
- "fix the rf in run_part_b.py too, and also delete the square outside that 5
  selection button, and also I will take your recommendation of 'I'd leave it'"
- "also bring a little bit down of that five button"
- "also make sure all the wording and text and sentence in the apps are fluent
  with no '-'"

## What the assistant produced
- Surveyed several documented product design systems, and reported that my app
  had already independently arrived at the standard trading-surface model — deep
  canvas, surface ladder, single accent, green-up/red-down as text colour never
  fill. It recommended against a wholesale reskin and listed five specific gaps
  instead.
- **Pass 1 (tokens).** `src/app_theme.py` and `.streamlit/config.toml` moved to
  a dark-tile ladder: `BG` `#12151D`→`#000000`, `SURFACE`
  `#1C2029`→`#1D1D1F`, `SURFACE_HI` `#2A303D`→`#2A2A2C`, blue-tinted greys
  swapped for warm neutrals at equal-or-greater brightness, `ACCENT`
  `#6BA3FF`→`#2997FF` (a bright on-dark link blue), a documented radius scale, a
  separate `DISPLAY_STACK` for large text, negative tracking on the quote value,
  and the 300/400/600/700 weight ladder with 500 removed everywhere.
- **Pass 2 (motion).** `scale(0.96)` press feedback on tabs, buttons, dataframe
  toolbar icons and multiselect chips; a frosted sticky tab strip
  (`saturate(180%) blur(20px)`); hover transitions; slider handle grow-on-hover;
  smooth scroll; and a `prefers-reduced-motion` block.
- Notation and prose: `r<sub>f</sub> = 0` in the four app locations, `$r_f = 0$`
  mathtext in `scripts/run_part_b.py`, and 29 dash-punctuated sentences rewritten.
- A headless-Chromium screenshot harness (kept outside the project, in scratch)
  that captures all five tabs at 1600px and 430px.

## What was wrong or risky

- **The sticky tab strip did nothing at all, and every check I had was green.**
  The assistant wrote `position: sticky` on `div[data-baseweb="tab-list"]`,
  reported pass 2 as delivered, and `ruff` plus **26/26 tests** passed. The strip
  scrolled straight off the screen. A sticky element can only travel inside its
  parent's box, and that parent is sized to the strip exactly (53.72px measured),
  so it had nowhere to go. CSS fails silently: no exception, no warning, nothing
  for a test to catch. It was only found because I made it screenshot a real
  browser *after scrolling*, and the fix (move sticky up to the wrapper, whose
  own parent spans the 1234px tabs component) came from querying the computed
  style of every ancestor rather than from guessing again.

- **It told me `git checkout` would revert the work. There is no git here.**
  `fins2026/z5594806_projectB/` is not tracked by the repo and has no `.git` of
  its own. The assistant offered that as a safety net while recommending a change
  to my one working artifact, and only discovered it was false later, by
  accident, while checking something else. A confident rollback story that does
  not exist is worse than no rollback story.

- **It proposed an animation that would have fought my own architecture.**
  The first motion plan included fade-and-rise entrance reveals. Those key off
  render, and the cost slider deliberately sits *outside* the tab fragments so it
  reruns the whole page — so every drag of that slider would have re-animated
  the entire app. That constraint is written in a comment in my own
  `streamlit_app.py`, which the assistant had read. It caught this itself before
  building, but only when I asked for advice rather than for code.

- **The rule it recommended turned out to be unachievable, and it said so only
  afterwards.** It argued for decoupling `ACCENT` from Min-CVaR's series colour
  so one hex stops meaning both "click me" and "this fund" — sound, and I took
  it. It then discovered that Streamlit draws every `ProgressColumn` bar in the
  theme's primary colour with no override, so the accent is still in the data
  regardless. The stated principle was never fully reachable in this framework.

- **A rendering defect had survived every previous pass, including the audit in
  `prompt_log_10`.** Streamlit floats each dataframe's hover toolbar above the
  table with no background, so on the fact sheet its icons printed straight
  through the panel subtitle: "Cap: 10% per asset (⊙⇩🔍⛶ 25% — a 10-asset
  universe…". It has presumably always done that. Nothing found it before because
  nobody had looked at a rendered screenshot with the cursor over that table.

## What I changed and why

- **Dark, not light.** The reference system is mostly white and parchment, and
  the assistant offered that as an option. I refused it. My report
  and both module docstrings argue the app is dark *because* it is a trading
  surface rather than a newspaper page, which is the whole reason two visual
  systems in one submission is a choice and not an inconsistency. Going light
  would have made prose I have not written yet false before I wrote it.

- **I split the system rather than adopting it.** Its spacing philosophy is one
  tile per viewport with 80px section padding, because on a marketing site the
  product photograph is the protagonist. I have a twelve-row fund table and three
  dataframes on one tab. I took the motion, geometry, type and press feedback and
  explicitly left the spacing and density behind.

- **No entrance reveals.** Once the rerun problem was on the table I dropped them
  entirely rather than trying to scope them. The motion budget went to things
  that fire on intent — press, hover, the pinned nav — which is also the more
  disciplined answer.

- **I deleted the "Choose a section ↓" hint** rather than restyling it. It was
  scaffolding for a tab strip that did not look clickable; the pills do that job,
  and labelling your own navigation is an instruction a working design does not
  need. I had the helper deleted too, not left unused.

- **I removed the container box around the five pills** and had its tint keyed to
  the page floor instead of the panel colour, so it is invisible at rest and only
  resolves into a frosted band once content scrolls under it. That keeps the
  pinned behaviour without putting a card back around the navigation.

- **I kept `ProgressColumn` and had the reasoning written into the code.** In a
  table the bar length means "how big"; in a chart the colour means "which fund".
  Rebuilding those tables by hand to unify them would cost the dataframe's
  sorting and toolbar, which is trading real function for palette purity. The
  comment in `app_theme.py` now says so, with an explicit instruction not to
  "fix" it later.

- **I made it prove the accessibility claim instead of asserting it.** The
  `prefers-reduced-motion` block was reported as done. I had it measured in a
  real browser under both settings: transition duration `0.22s` → `1e-05s` and
  `scroll-behavior` `smooth` → `auto`. Same discipline as the mutation testing in
  Phase 8d — a check nobody has seen go red is not yet a check.

- **I made it prove the pipeline re-run was safe.** Fixing the `rf` label in
  `scripts/run_part_b.py` meant regenerating exhibits. I had `results/`
  checksummed before and after: exactly one file changed
  (`performance_sharpe_bar.png`), the other 28 byte-identical. That is the
  determinism claim in my README tested rather than repeated.

- **On the dashes, I kept what is not a dash.** Hyphenated compounds
  (`Min-CVaR`, `out-of-sample`, `Crypto-Only`), numeric ranges (`2020–2023`,
  `0.94–2.22pp`) and the en dash in `Rockafellar–Uryasev` all stay, because those
  are correct typography rather than the punctuation habit I wanted gone. The 29
  rewrites are real connectives, not swaps: "stay gross — only the net columns
  were precomputed" became "stay gross, because only the net columns were
  precomputed".

- **What this pass could not touch.** It reads no data and computes nothing. The
  only file outside the app it changed is two label strings in
  `scripts/run_part_b.py`, and the checksum diff bounds that to one PNG.

## Verification run at the end
`ruff` clean · **26/26 tests** · `scripts/check_handin.py` 23 checks, one expected
reminder (no `report.pdf`) · five tabs screenshotted at 1600px and 430px in
headless Chromium and read for prose · sticky measured (strip top 221.6px →
43.9px after a 1400px scroll, then held) · reduced-motion measured under both
settings · `results/` checksum-diffed against its pre-run baseline.

---

*Drafted by the assistant from this session's transcript, same division of labour
as the earlier logs: it records what happened, the decisions recorded are mine.
Review and correct the framing before hand-in.*
