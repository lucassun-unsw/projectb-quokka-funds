# Prompt log — Part B housekeeping: independence verification and OUTLINE.md cleanup

## What I wanted
Before writing any Station 3 code, get a definitive answer on whether the
Part B folder is genuinely self-contained (no hidden dependency on Part A),
bring `report/OUTLINE.md` up to date with what's actually done vs still
planned, and make sure a known upcoming dependency (finVADER's packages)
doesn't get forgotten when Phase 3 starts.

## Prompt(s)
- "You sure like when submitted this partb folder, it is still fine? like all
  the data and everything is independent and you copy all the result and all
  the things needed to here?"
- "Also check 3 and 4 of partb handoff, write it the OUTLINE.md is needed and
  do cleaning and updating for the OUTLINE.md... also added 'it'll need the
  finvader and vaderSentiment packages added to requirements-dev.txt'... after
  this doing a final check if we are fully happy for all the work before
  diving into the actual project... ask if you are not sure."

## What the assistant produced
- A grep across every `.py` file for `projectA`/path-escaping references
  (found only docstring provenance notes, no real dependency).
- A genuine isolation test: copied the whole `z5594806_projectB` folder to a
  location with no `z5594806_projectA` anywhere nearby, and ran the ported
  `etl -> features -> dependence` pipeline cold from there.
- A re-read of the frozen Part A facts in `report/OUTLINE.md`, and a
  cleanup pass: updated the stale "Folder layout" section (still said
  TODO/STUB/MISSING for files finished last session), checked off Phase 0/1 in
  the Status list, added an explicit §3/§4 cross-reference at the top, added a
  Phase-8 re-check item (re-run the isolation test after Phase 2-4 add code),
  and added `finvader`/`vaderSentiment` to `requirements-dev.txt` with a note
  on why they're there ahead of the code that uses them.

## What was wrong or risky
- Nothing new was found broken in this pass — the independence claim from the
  previous session held up under an actual isolation test, not just a
  by-eye check. Worth recording precisely because I asked for the test rather
  than accepting the earlier assurance at face value.
- `report/OUTLINE.md`'s "Folder layout" section had gone stale after last
  session's work (still described `etl.py` as a TODO after it had already
  been replaced) — a small but real risk: a stale plan document is worse than
  no document if I start trusting it over the actual folder state.

## What I changed and why
- Added `vaderSentiment>=3.3.2` and `finvader>=1.0` to `requirements-dev.txt`
  now, ahead of Phase 3, rather than waiting until `sentiment.py` exists —
  this is a locked decision already (finVADER, `report/OUTLINE.md`), not a
  speculative add, and installing/verifying it now means Phase 3 starts on a
  known-working environment instead of discovering an install problem mid-task.
- Updated `report/OUTLINE.md`'s Folder layout, Phase 0/1 descriptions, and
  Status checklist to match reality, and pinned the frozen Part A facts
  (data sizes, calendar rules) at the top so the plan stays traceable
  instead of drifting.
- Added a Phase 8 checklist item to re-run the isolation test after Phase 2-4
  add new code, since today's test only covers what exists right now
  (`etl`/`features`/`text_panel`/`ft_style`/`dependence`) — `portfolios.py`,
  `sentiment.py`, `fusion.py` haven't been written yet and could introduce a
  new cross-folder dependency the current test wouldn't catch.

## Verification I did myself
- Ran the isolation test personally rather than trusting a static grep alone:
  copied the folder to an unrelated path, executed the pipeline there, and
  confirmed it reproduced the exact same numbers as the real folder (equity
  50,300×9, crypto 14,610, combined panel 60,360 rows).
- Confirmed `vaderSentiment`/`finvader` actually import and their installed
  versions (3.3.2 / 1.0.2) satisfy the pins just written, rather than adding
  untested version constraints to the requirements file.
- Re-ran `scripts/check_handin.py` after every change in this session — still
  16 checks passed, no new `[FAIL]`, only the expected not-built-yet `[WARN]`s
  (funds/sentiment CSVs, report.pdf).
