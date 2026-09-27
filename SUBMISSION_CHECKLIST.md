# Submission checklist — IEEE conference build

Status as of **26 September 2026**, after converting the manuscript from
Springer's `sn-jnl [iicol]` class to `IEEEtran [conference]`. The
Datenbank-Spektrum submission is abandoned; the Springer build is on the `main`
branch of this repository.

**All 15 gates pass.** The page gate, which failed deliberately for two weeks
under Datenbank-Spektrum's 8–10 limit against a 14-page manuscript, now passes:
the paper is **10 pages** against a 10–12 target.

## Where the pages went

Nothing was cut to reach 10. The Springer build's 14 A4 pages became 9 IEEE
letter pages on format alone, and content was then *restored* to use the
budget:

| | pages |
|---|---|
| Springer `sn-jnl [iicol]`, A4 | 14 |
| → `IEEEtran [conference]`, US Letter, `IEEEtran.bst`, Declarations removed | 10 |
| → `newtxtext` (Times, correctly encoded) | 9 |
| → three evidence tables restored from `SUPPLEMENTARY.md` | **10** |

`IEEEtran.bst` is much more compact than `sn-basic.bst`; the bibliography cost
2.5 pages under Springer and roughly 1.3 here. That, plus dropping the
Springer-mandated Declarations section, is where the format saving came from.

The three restored tables — requirement-to-model traceability, systems/versions
/evidence, and per-query validation detail — had been moved out of the
manuscript purely to fit 8–10 pages. They are evidence, and an assessment paper
is stronger carrying its own. `SUPPLEMENTARY.md` now holds only the per-query
prose readings, which are commentary.

## Gate output

```
python3 check.py
  [PASS] compile
  [PASS] no large overfull boxes
  [PASS] bibtex clean
  [PASS] citations resolved
  [PASS] pages in [10,12]                 10 pages
  [PASS] reference queries execute and match        7/7
  [PASS] generated tables current
  [PASS] manuscript self-consistent                 0 failures (36 checks)
  [PASS] model consistent (endpoints, orphans)      0 failures
  [PASS] anonymous version current and clean
  [PASS] anonymous PDF builds with no identifying text
  [PASS] abstract in [150,250] words                247 words
  [PASS] artefact availability footnote in the PDF
  [PASS] scholarly references carry DOIs            18/23, 5 known DOI-less venues
  [PASS] references verified                        23 verified, 6 web, 0 to check
exit 0
```

Independence, measured with `tools/check_overlap.py` against the author's four
prior papers: **max verdict LOW**, highest score 0.13 (the survey).

## What the conversion changed, beyond the class line

Each of these is a defect the *rendered pages* exposed — none of them produced
a LaTeX error, and several passed every log-based check:

| | |
|---|---|
| **Fonts** | IEEEtran requests Times (`ptm`) shapes that are undefined under the Unicode encoding tectonic's engine uses. Every bold and small-caps run fell back silently — `\textbf` produced no bold anywhere in the paper. Fixed with `newtxtext`/`newtxmath`, loaded after `amssymb` with `\let\Bbbk\relax`. |
| **Run-in headings** | 35 `\paragraph{...}`. IEEEtran sets the title in the body font and appends a colon, so "Design decisions." rendered as "Design decisions.:" in plain roman. Replaced with a `\rih` bold run-in. |
| **Description lists** | IEEEtran's `description` uses a fixed narrow label box; "Valid time" and "\rna\ Not applicable." overprinted their own item text. Replaced with `IEEEdescription` and an explicit widest label. |
| **Table captions** | IEEEtran sets captions in small caps above the table. The two inherited captions were 10 and 14 lines. Cut to a title, detail moved to a `\scriptsize` note under the bottom rule; `make_tables.py` emits the same shape. |
| **Bibliography** | One entry listed an author as `undefined, others`, which `sn-basic.bst` hid and `IEEEtran.bst` printed as "o. undefined". Corrected to the `and others` idiom. |
| **Floats** | `stfloats` added so the four full-width `table*` floats and the full-width figure can sit at the bottom of a page instead of being deferred. |

## Tooling retargeted in lockstep

Three scripts parse `paper.tex` by literal string offset and would have failed
silently or loudly against the new front matter:

- `make_anon.py` — the spliced span was `\author*{` … `\abstract{`; both
  constructs are gone. Now `\author{` … `\maketitle`, which also strips the
  `\thanks` footnote carrying the artefact URL. That is deliberate: the URL
  names the author's GitHub account.
- `check.py` — page band 8–10 → 10–12; the abstract is read from
  `\begin{abstract}` rather than `\abstract{...}`; the Springer Declarations
  gate was replaced by one asserting the artefact-availability footnote reaches
  the rendered PDF.
- `evaluation/make_tables.py` — now generates four LaTeX tables instead of one,
  with IEEE column specs and caption notes.

`consistency.py` needed no change and still reports 36/36; it indexes
`\label{tab:edges}` and `\begin{tikzpicture}`, both of which survived.

## Before submitting

1. **Read the paper end to end on screen.** Every gate passes; none of them
   judges whether the argument reads well.
2. **Name the venue.** The build targets `IEEEtran [conference]` generically.
   A specific conference fixes the page allowance (many are 8+2, not 10–12),
   whether review is double-blind, and whether a copyright block is required
   (`\IEEEpubid` / the `\thanks` slot).
3. **Choose which manuscript to upload.** Two builds exist from one source:
   `paper.pdf` / `paper.tex` (named) and `paper_anon.pdf` / `paper_anon.tex`
   (author, affiliation and artefact footnote withheld). The blinded pair is
   **generated** by `make_anon.py` and must never be hand-edited; `check.py`
   fails if it goes stale or if either the source or the PDF carries an
   identifying string.
4. **Upload source with the PDF**: `paper.tex` and `references.bib`. Nothing
   else is needed — `IEEEtran.cls` and `IEEEtran.bst` are on CTAN and on
   Overleaf, so no class file travels with the submission.
5. **The artefact repo is public** (26 September 2026) at
   `github.com/moganakumaran/operational-metadata-property-graph`, and the
   `\thanks` footnote carries that URL. If the chosen venue is double-blind
   this is a de-anonymisation risk: `make_anon.py` strips the whole `\author`
   span, footnote included, and both `github.com/moganakumaran` and
   `operational-metadata-property-graph` are in its `FORBIDDEN` scan, so the
   blinded build is covered — but submit `paper_anon.pdf`, not `paper.pdf`.

## Files

| File | What it is |
|---|---|
| `paper.tex` | the manuscript, single file |
| `references.bib` | 29 entries (23 scholarly + 6 organisational), all cited and verified |
| `paper.pdf` | named build, 10 pages |
| `paper_anon.tex`, `paper_anon.pdf` | blinded build, generated by `make_anon.py`; do not hand-edit |
| `check.py` | all 15 gates; exit 0 = submittable |
| `consistency.py` | 36 manuscript-vs-artefact checks |
| `backfill_dois.py` | finds a DOI per reference; accepts only on title+year+author agreement |
| `evaluation/` | reference implementation, 7 queries, capability matrix, table generator — see its `README.md` |
| `verify_refs.py` | reference verification (OpenAlex → Crossref, DOI-first) |
| `refcheck.txt` | latest verification output |
| `SCOPE.md` | venue facts; the Springer material is kept as superseded record |
| `GAP_ANALYSIS.md` | first-pass research notes; superseded for the capability verdicts by `evaluation/capability_matrix.json` |
| `REVISION_AUDIT.md`, `REVISION_REPORT.md` | pre-revision defect audit, and what the revision changed — both predate the IEEE conversion |
| `TEMPLATE_PROVENANCE.md` | the class, and the two things it needed help with |
| `CFP_datenbank_spektrum.pdf` | the superseded venue's call for papers, archived, not committed |
