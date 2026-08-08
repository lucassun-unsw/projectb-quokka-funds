# Prompt log — Phase 10, deployment and the final whole-document audit

## What I wanted
Turn `z5594806_projectB` into its own public GitHub repository independent of
the course repo, deploy the app on Streamlit Cloud, paste the live URL and
repo link into the report and README, then run one last check of everything —
the deployed app, every table in `report.docx` against `results/`, every
number in the prose, and the exported `report.pdf` — before hand-in.

## What I directed
- Deploy the app: git-init this folder as its own repo (never commit into the
  course repo, whose origin is the lecturer's), push it public, deploy on
  share.streamlit.io, and confirm the live app actually loads.
- Once deployed, put both URLs into `report.docx` and `README.md`.
- Then run the deepest check the project has had: every table cell-by-cell
  against the CSV it is drawn from, every quoted number in the prose, and the
  theory/formula statements, not just a read-through.
- After I inserted my own screenshot for Figure 9 and exported `report.pdf`,
  check both files one more time before I zip and submit today.

## What the assistant produced
- **Deployment.** Cleared `__pycache__`/`.ruff_cache`, verified no stray
  data/secrets were staged, `git init -b main`, one commit, `gh repo create
  --public --source . --remote origin --push`. Confirmed the repo was public
  and the app returned HTTP 200 on the live URL.
- **The Streamlit-version bug.** I sent two screenshots showing the deployed
  tab strip did not match my local app (plain underline tabs instead of the
  rounded pills `app_theme.py` styles). The assistant traced it to
  `requirements.txt`'s unpinned `streamlit>=1.50,<2` resolving a different
  release on the cloud build than the one installed locally, and whose
  internal tab markup my CSS selector (`button[data-baseweb="tab"]`) did not
  match. Pinned to `streamlit==1.57.0`, the exact version the app had been
  visually audited against. Cloud auto-rebuilt; tabs matched after.
- **The whole-document audit.** Extracted every one of the 14 tables from
  `report.docx` and diffed every cell against its source CSV (`performance_
  metrics.csv`, both bootstrap tables, the co-crash panel, event validation,
  fusion, parameter study, holdings, method separation, coverage, k-grid,
  lexicon candidates). Then checked prose claims not already in the claim
  ledger: NVDA held on 30 of 36 Combined rebalances (22 at the 10% cap) for
  Max-Sharpe versus zero for Min-CVaR, the per-method holdings-count ranges
  (13-16 / 13-21 / 12-18 / 53-60 at the 0.5% threshold), 5 names at the cap on
  the latest Min-CVaR rebalance, and the four dropped lexicon terms. Fixed two
  mechanical typos ("falls" to "fall", "separate" to "separates").
- **Catching the same defect twice.** Before I inserted a screenshot, the
  assistant read the embedded Figure 9 image out of the docx and reported it
  was the *Compare funds* tab, not the *Fact sheet* tab the caption promises.
  After I said I had fixed it and exported `report.pdf`, it re-extracted the
  image from the new `report.docx`, hashed it, and found it **byte-identical**
  to the flagged image from before — nothing had actually changed. It then
  rendered page 17 of the exported `report.pdf` to a PNG to confirm visually:
  same wrong tab, blue "Compare funds" pill still highlighted, no co-crash
  panel or fee line in view.

## What was wrong or risky
- **My screenshot fix did not take, and a hash check is the only way I would
  have known.** Reading the caption text or eyeballing a thumbnail would not
  have caught this: the image genuinely looks plausible as "the app,
  deployed," and only a content diff against the specific promise the caption
  makes (Fact sheet tab, fee line, co-crash panel) exposes that it is the
  wrong tab. I had exported a full `report.pdf` and moved on believing this
  was done.
- **The Streamlit version drift was invisible from the code.** `app_theme.py`
  had not changed; the CSS selector was correct for the version it was
  written against. The bug only existed in the gap between "what
  `requirements.txt` allows" and "what got installed," which no local test
  run could see, because locally the pinned dev environment always resolves
  the same version.
- **A shell line-wrap silently dropped half a command.** My first attempt at
  `gh repo create ... --remote origin --push` wrapped across two terminal
  lines; the shell ran `gh repo create --public --source .` and then choked
  on a bare `--remote` on the next line. The repo was created but empty, and
  I did not notice until checking GitHub directly and seeing nothing there.

## What I changed and why
I kept the assistant's `streamlit==1.57.0` pin with its comment explaining why
(the pill-tab CSS targets Streamlit's internal DOM, which changes between
releases) so a future package bump does not silently reintroduce the same
regression without a visual re-check. I accepted both typo fixes since they
were mechanical, not judgement calls. I have **not** yet fixed Figure 9 — the
correct next step is to open the Fact sheet tab on the live URL, frame the Key
facts block (fee line visible) and the co-crash panel together, and replace
the image in Word directly, not just insert a new one elsewhere in the
document. I am doing that now, today, before export and zip.

## The general lesson
This project's pattern across every prior log holds again: pointing the
project at a *different* artifact finds what re-reading does not. A caption
promising a specific tab, checked against the actual pixels of the embedded
image rather than against my own memory of having "already fixed it," is what
caught this. I would not have found it by reading `report.docx` in Word,
because the image renders fine — it is simply proof of the wrong claim.
