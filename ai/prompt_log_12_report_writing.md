# Prompt log — Phase 9a, drafting Sections 1–3 and restructuring the exhibits

## What I wanted
Write the prose for report Sections 1–3 in my own words, from my per-section
plan in `report/OUTLINE.md`, and get it into `report/report.docx`. Alongside
that: restructure the exhibits so numbering runs continuously through the
appendix (Figures 1–9, Tables 1–14, no "A" prefix), each exhibit sits right
after the paragraph that discusses it, and the NVDA-weights figure moves to the
appendix beside its stacked-weights pair. Every quoted number has to hold to my
quote-the-CSV rule.

## What I directed
For each section I gave the assistant the points the section had to cover, wrote
the prose myself, sent it back for a numbers-and-style check, agreed or adjusted
its suggestions, then asked it to insert the agreed text into `report.docx`. The
points I directed:
- **Section 1 — the funds and the backtest design:** the four optimisation
  methods; the 10%/25% position caps and why a ten-asset crypto universe needs
  the higher one; the EWMA covariance choice justified by volatility clustering;
  and the walk-forward, no-look-ahead backtest contract.
- **Section 2 — out-of-sample results and fact sheets:** lead with the Risk
  Parity Sharpe result but flag that it misleads; interpret the metrics table
  and the growth-of-$1 and drawdown figures; the NVDA-across-methods weights
  contrast; the transaction-cost preview; and the reasoned Min-CVaR
  recommendation with its caveat.
- **Section 3 — the sentiment index:** the finVADER neutrality rescue; the
  two-step sector construction and why order matters; the three-level
  no-headline rule; the event validation with its positive control; and the
  caveats carried forward.
- **Cross-cutting instructions:** keep bullet lists where they read clearer;
  renumber the appendix onto one continuous sequence and cite appendix exhibits
  as "(Appendix X)"; and delete any number not backed by a saved CSV rather than
  write it into the report.

## What the assistant produced
- Section structure and paragraph skeletons — never the analysis prose, which I
  wrote — plus a check of every quoted number against the saved CSVs, and a
  style pass on my drafts against my own rules (banned words, British spelling,
  ISO dates, the quote-the-CSV rule).
- A `python-docx` script that renumbered 14 tables and 9 figures onto one
  continuous sequence, moved the NVDA-weights figure into the appendix, and
  interleaved each body exhibit after the paragraph citing it; then inserted my
  agreed text into `report.docx`.

## What was wrong or risky
- **It deleted four real exhibits.** While removing a section's planning marker,
  the assistant's "delete everything between the two headings" logic also removed
  **Figures 1–4 and Table 1's caption** — actual embedded figures, not just the
  marker. The test suite and an AppTest-style check would not have caught this;
  it was found only by dumping the document's raw structure afterward. Recovery
  was possible because the source images were still in `results/figures/` and the
  caption text existed earlier in the session, so the figures and caption were
  re-inserted with the same Word field pattern as the rest of the document.
- **A fabricated rubric quote** in my plan — a phrase in quotation marks
  attributed to the marking rubric that was not its actual wording.
- **Unsourced numbers** that live only in a prompt log, not a saved CSV: a
  pre-filtering volatility range (S1), a two-step sentiment worked example (S3),
  and Part A's tail and false-neutral figures (S4).
- **Code-file citations** (a test file, a source module) written into report
  prose meant for a financially-literate but non-technical reader.
- A whitespace bug: an earlier caption edit dropped `xml:space="preserve"`, which
  Word silently stripped, breaking a caption's "Figure "/"Table " prefix.

## What I changed and why

I wrote the prose for all three sections myself from the points above; the
assistant's job was structure, number-checking, and the mechanical Word edits.
Where I agreed with its suggestions I took them: the style fixes that keep the
report consistent (British spelling, ISO dates, "%" over "percent", the dropped
compound-modifier hyphens), the continuous appendix numbering, and placing each
exhibit after the paragraph that discusses it. One call went against my own
first instinct: I had asked whether to cut the app design-system material,
thinking the brief might not ask for it, but when the assistant checked the
brief it showed a custom design system is rewarded in two marking bands, so I
kept it — the decision is mine, but the check that changed my mind was worth
having.

On the numbers, I held to my every-quoted-%-must-be-in-a-saved-CSV rule and
chose to **omit** rather than cite the figures that lived only in a prompt log
(the S1 pre-filter range, the S3 two-step example): the argument stands on the
saved evidence without them.

After the exhibit-deletion incident I stopped trusting the assistant's edits by
default: I required the document structure to be re-dumped and the exhibit
inventory re-counted before every save, and no more paragraph-range deletes in a
file that mixes planning markers with real figures. Once a section's prose and
its exhibits checked out, I had the assistant insert the agreed text into
`report.docx`.
