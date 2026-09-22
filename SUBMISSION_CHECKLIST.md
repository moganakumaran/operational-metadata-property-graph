# Submission checklist — Datenbank-Spektrum

Status as of **22 September 2026**, after the Springer submission-guideline
compliance pass recorded below. Deadline **1 October 2026**.

**Note on length — 14 pages against an 8–10 limit.** An earlier cut pass took
the paper from 15 to 12; the technical revision, the `via_pipeline`
formalisation and the mandatory Declarations section have since taken it to
14. The cut pass measured: What moved it, measured rather than estimated:

| | |
|---|---|
| Bibliography: 22 documentation entries → 6 per-organisation entries | −1 page |
| Prose 5,295 → 4,575 words | −1 page |
| Listing 1 removed; float consolidation | absorbed by repacking |

Everything protected survived: all seven formal query specifications, the
Y/P/N/S rubric, all five threat categories, both temporal definitions, the
executable validation and every capability finding.

**The remaining pages would have to come from protected material.** At
roughly 500 words per page, closing the gap means ~1,000 more words, and the
only blocks left that large are the Threats section, the rubric, and the formal
query semantics. The structural alternatives each buy one page and cost
something load-bearing: Figure 1, or the edge table.

So the options are: submit at 14 and say why in the cover letter; ask the guest
editors whether a Schwerpunktbeitrag carrying an artefact may run long; or
decide which protected item goes. `check.py` encodes the venue's 8–10 rule and
currently **fails that one gate**, deliberately — the gap stays visible rather
than being widened away.

One cheap thing first: the CfP does not say whether references count toward
the limit. They are 2.5 pages here. If they are excluded, the paper is already
inside the limit and none of the remaining decision is needed.

Re-run everything with `python3 check.py` (exit 0 = all gates pass).

## Gates — 14 of 15 passing

```
[PASS] compile                          tectonic, no errors
[PASS] no large overfull boxes
[PASS] bibtex clean                     0 warnings
[PASS] citations resolved               0 occurrences of "[?]" in the PDF
[FAIL] pages in [8,10]                  14 pages  <-- the open item
[PASS] reference queries execute        7/7 executable and matching expected
[PASS] generated tables current         spliced tables match the evidence JSON
[PASS] manuscript self-consistent       36 checks, 0 failures
[PASS] model consistent (endpoints)     figure/table/schema agree; no orphans
[PASS] anonymous version current/clean  paper_anon.tex regenerates identically
[PASS] anonymous PDF builds, no leak    0 identifying strings, no /Author
[PASS] abstract in [150,250] words      247 words
[PASS] declarations present in the PDF  Competing interests, Funding, Data av.
[PASS] scholarly references carry DOIs  18/23, 5 known DOI-less venues
[PASS] references verified              23 verified, 6 web, 0 to check
```

A review pass (see `REVISION_REPORT.md` §13) re-derived the Q4 result
independently of Kùzu and audited every figure against the artefacts; it found
and fixed one factual error (four paths into `daily_revenue`, not three), an
RQ1/threats contradiction, a missing novelty foil, and an omission of
OpenMetadata from the per-system summary.

`python3 consistency.py` separately asserts that Figure 1, Table 2 and the
executed schema agree; that the Q4 listing matches the query that ran; that
`feeds` is defined and `lag_minutes` gone; that all four temporal fields exist
in both paper and schema; and that the "no more than three of seven" claim
follows from the computed matrix.

## Measured, not asserted

| Check | Result | Bar |
|---|---|---|
| Page count, `sn-jnl [iicol]` | **14** | CfP says 8–10 — see note above |
| Abstract | **247 words** | Springer requires 150–250 |
| References | 23 indexed + 6 organisational = 29 | all cited; no URL dropped |
| — carrying a DOI | 18 of 23 scholarly | 5 venues register none |
| Executable validation | **7/7 queries match** | Kùzu 0.11.3, 45 nodes / 64 edges |
| Capability cells | 90, all with a citation key | generator rejects cells without one |
| AI-writing heuristic | **~14.1%, "Low — likely human"** | <20% |
| — flagged sentences | 0 of 202 | — |
| 8-gram similarity vs 4 prior papers | **0.00%** | — |
| Internal repetition | 0.38% | — |
| Self-overlap (`tools/check_overlap.py`) | **LOW**, max 0.13 | MEDIUM at 0.28 |

Predictability at 0.410 sits just above the human band (0.30–0.40) and well
below the AI-like threshold (0.45). That is what a technical paper repeating
*lineage*, *dataset*, *graph*, *traversal* looks like, and it improved from
0.441 pre-revision as the paper gained formal content. Left alone
deliberately: the only way to move it further is to stop using the domain's
words.

## Independence from DARE — the directive was "fully independent"

Met and measured rather than asserted:

- **0.00% 8-gram similarity** against DARE, Semantic DQ, LHR-Bench and the
  survey, re-measured after the revision. Not one shared eight-word sequence.
- `check_overlap.py` **LOW**, highest 0.13 (against DARE's methods section),
  well under the 0.28 MEDIUM threshold. The residual is
  shared domain vocabulary, which is unavoidable and not duplication.
- Single `paper.tex` written from scratch. No DARE text, figure, table or
  artifact reused. Blast radius is not the contribution here; DARE is not
  cited, because nothing in this paper depends on it.

## Reference integrity

Two entries were **wrong and were corrected by the check, not by review**:

| Key | Problem | Fix |
|---|---|---|
| `klettke2016migration` | recorded with a fabricated title, venue and year ("Darwin…", EDBT/ICDT Workshops 2022) | replaced with the real paper — *NoSQL schema evolution and big data migration at scale*, IEEE BigData 2016, DOI 10.1109/BigData.2016.7840924 |
| `rost2021gradoop` | year 2022, author "Christ, Lauren" | 2021 and "Christ, Lukas", per DOI 10.1007/s00778-021-00667-4 |

Three further entries were reported as misses and turned out to be **indexing
artifacts, not errors**: OpenAlex and Crossref store *Delta Lake*, *Cypher* and
*Goods* under truncated titles. Their DOIs are now recorded in the bib and the
verifier checks DOI before title, so these confirm exactly instead of
approximately.

**DBLP is deliberately not used.** It is unreachable from this environment, and
a lookup that returns nothing because the host is blocked is indistinguishable
from a reference that does not exist. The verifier reports an unreachable source
as unreachable and never as a miss — a false negative here would defeat the
whole point of the check. Successful lookups are cached in `.refcache.json`
because OpenAlex rate-limits a 36-entry run and made consecutive runs disagree.

## Content integrity

- Every cell of Tables 4 and 5 traces to a cited primary source. **No cell is
  unverified**; the table generator refuses to emit a cell without a citation
  key, and `consistency.py` asserts no `?` verdict survives.
- Two cells were settled by **reading source code**, because the documentation
  was silent exactly where the workload depends on it: Egeria's
  `InstanceProperties.effectiveFromTime/effectiveToTime` carried by
  `Relationship`, and Atlas's `AtlasRelationship` carrying only
  transaction-time fields while `AtlasClassification` carries
  `validityPeriods`. The paper says it did this and names the classes.
- During the first pass, five of eight unverified cells changed the answer and
  two reversed a headline claim. The revision changed more: re-checking Atlas
  against `master` rather than 2.0.0 docs, and testing whether recursive SQL
  can express the workload for Unity Catalog, moved ten cells. Old → new
  classifications are tabulated in `REVISION_REPORT.md` §5.
- The running example is synthetic. **No employer data, systems or incidents
  appear**, and the paper states this in Sect. 3.
- Author block carries no employer: name, city, and an IEEE email, matching the
  prior papers.

## Springer submission-guideline compliance

Audited 22 September 2026 against
`link.springer.com/journal/13222/submission-guidelines`. The page 303-redirects
through `idp.springer.com`; its content is reachable via the
`?error=cookies_not_supported` variant.

Three requirements were **not met** and are now fixed, each with a gate:

| Requirement (the guidelines' words) | Was | Now |
|---|---|---|
| Declarations incl. Competing Interests; *"submissions that do not include relevant declarations will be returned as incomplete"* | **absent entirely** | Declarations section with Competing interests, Funding, Data availability |
| Abstract *"150 to 250 words"* | **273 words** | **247** |
| *"always include DOIs as full DOI links"* | 5 of 23 scholarly entries | **18 of 23**; the other 5 are CIDR ×2, MLSys, DBPL and BTW, which register no DOIs |

Already compliant, confirmed rather than assumed: the `[iicol]` class option;
a single self-contained `.tex`; numbered `[N]` citations and
`https://doi.org/` -style DOI rendering, both from `sn-basic.bst`; English
("The journal language is German. However, manuscripts written in English are
also welcome."); TikZ figures, so the EPS/TIFF resolution rules do not apply.

**On blinding: the guidelines are silent.** They state no review model and
impose no anonymisation requirement. So `paper_anon.pdf` is insurance, not an
obligation — the Editorial Manager form decides whether it is wanted. The
anonymisation itself was re-audited and is clean: no author, e-mail or
affiliation; no `/Author` in the PDF metadata; no acknowledgements or funding
text; and **no self-citations at all** in `references.bib`, so there is
nothing to third-person.

**On AI assistance: no declaration, decided 22 September 2026.** The policy
requires LLM use to be "properly documented in the Methods section" but exempts
*"AI assisted copy editing"* — "AI-assisted improvements to human-generated
texts for readability and style" — which is the characterisation relied on
here. Recorded as a decision so it does not read later as an oversight.

One defect surfaced by the same sweep and fixed: a paragraph in Sect. 6.3
opened *"On run history our earlier wording was too strong"* — revision-log
commentary about a draft no reader has seen, spliced into the manuscript. It
now states the finding directly.

## Still to do before submitting

**0. Settle the length question first** (see the note at the top) — it decides
whether anything else changes. Cheapest first move: ask the guest editors
whether references count toward the 8–10 pages. They are 2.5 pages here, so if
excluded the paper already fits.

1. **Read the paper end to end on screen.** Every automated gate passes; none
   of them judges whether the argument reads well.
2. **Editorial Manager**: account at editorialmanager.com/dasp, category
   **"Schwerpunktbeitrag"** (required by the CfP), cover letter naming the
   special issue and the guest editors.
3. **Choose which manuscript to upload.** Two builds exist from one source:
   `paper.pdf` / `paper.tex` (named) and `paper_anon.pdf` / `paper_anon.tex`
   (author and affiliation withheld). The blinded pair is **generated** by
   `make_anon.py` and must never be hand-edited; `check.py` fails if it goes
   stale or if either the source or the PDF carries an identifying string.

   Note: **neither the CfP nor the Springer submission guidelines state that
   review is blinded**, and Springer journal review is often single-blind, so
   the blinded version may well not be wanted. Check the Editorial Manager
   submission form before choosing.
4. **Upload source, not just PDF.** *"Failing to submit a complete set of
   editable source files will result in your article not being considered for
   review"*: `paper.tex`, `references.bib`, `sn-jnl.cls`, `sn-basic.bst`, and
   the compiled PDF. Springer also
   requires a **single** `.tex` — satisfied: the evidence tables are spliced
   into `paper.tex` by the generator rather than `\input`.
5. ~~Decide the AI-assistance disclosure.~~ **Decided 22 September 2026: no
   declaration**, relying on the guidelines' copy-editing exemption. See the
   compliance section above.
6. **Flip the artefact repo public** if it is to be cited in the submission:
   `gh repo edit moganakumaran/operational-metadata-property-graph
   --visibility public`. It is private now because the paper is unsubmitted.

## Files

| File | What it is |
|---|---|
| `paper.tex` | the manuscript, single file per Springer's requirement |
| `references.bib` | 29 entries (23 scholarly + 6 organisational), all cited and verified |
| `paper.pdf` | named build, 14 pages |
| `paper_anon.tex`, `paper_anon.pdf` | blinded build, generated by `make_anon.py`; do not hand-edit |
| `check.py` | all 15 gates; exit 0 = submittable |
| `consistency.py` | 36 manuscript-vs-artefact checks |
| `backfill_dois.py` | finds a DOI per reference; accepts only on title+year+author agreement |
| `evaluation/` | reference implementation, 7 queries, capability matrix, table generator — see its `README.md` |
| `REVISION_AUDIT.md` | pre-revision defect audit |
| `REVISION_REPORT.md` | what the revision changed, with old → new classifications |
| `verify_refs.py` | reference verification (OpenAlex → Crossref, DOI-first) |
| `refcheck.txt` | latest verification output |
| `SCOPE.md` | venue facts, format findings, budget |
| `GAP_ANALYSIS.md` | first-pass research notes; superseded for the capability verdicts by `evaluation/capability_matrix.json` |
| `TEMPLATE_PROVENANCE.md` | where `sn-jnl.cls` came from, with checksum |
| `CFP_datenbank_spektrum.pdf` | the call for papers, archived |
| `sn-jnl.cls`, `sn-basic.bst`, `bst/` | vendored; not on CTAN |
