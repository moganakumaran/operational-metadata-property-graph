# Scope

> **Venue changed, 26 September 2026.** The paper now targets an **IEEE
> conference** (`IEEEtran`, `conference` option, two-column US Letter, target
> 10--12 pages) and the Datenbank-Spektrum submission is abandoned. Everything
> below the "Toolchain" heading was written for that earlier venue and is kept
> as the record of why the paper is shaped the way it is; the facts in it about
> Springer's template, `[iicol]`, the 8--10 page limit, the 1 October deadline
> and the Editorial Manager portal **no longer apply**.

## Venue facts

| | |
|---|---|
| Format | IEEE conference, `\documentclass[conference]{IEEEtran}` |
| Length | 10--12 pages, two column, US Letter |
| Bibliography | `IEEEtran.bst`, numeric |
| Blinding | `paper_anon.pdf` is generated and clean; whether it is needed depends on the venue chosen |
| Engine | tectonic; `IEEEtran` is fetched from CTAN, nothing vendored |

## Previous venue (superseded)

### Toolchain, verified 21 Sep 2026

- `sn-jnl.cls` is **not** on CTAN and **not** in tectonic's bundle. Downloaded
  from Springer's official template (v3.1, Dec 2024) and vendored into this
  directory with `bst/`. Source and checksum in `TEMPLATE_PROVENANCE.md`.
- Compiles clean under `tectonic -X compile` with TikZ, booktabs and BibTeX:
  no errors, no undefined references.
- Three traps found while testing:
  - `sn-basic` defaults to **author-year**, and a hand-written
    `thebibliography` then fails with *"Bibliography not compatible with
    author-year citations."* Use `[pdflatex,sn-basic,Numbered,iicol]` and a real
    `.bib`.
  - The shipped demo fails on `fig.eps` — tectonic has no PostScript support.
    Irrelevant here: all figures are TikZ.
  - `sn-jnl.cls` ships as a single line with no newlines, so line-based `grep`
    over it returns the whole file. Split on `%` when inspecting it.
- **Springer requires a single `.tex` file** ("Please do not use `\input{...}`
  to include other tex files"). So this paper does **not** follow the DARE
  `sec_*.tex` layout. One `paper.tex`. This also avoids the flattening bug that
  damaged the DARE short build.

### CfP facts, read from the CfP itself

Verified by extracting `CFP_datenbank_spektrum.pdf` (archived in this
directory), not from secondary summaries. Title, deadline, page limit, category,
portal, publication date and guest editors are all as tabulated above. The CfP
explicitly invites "technical papers, case studies, survey articles, and
position papers".

Topics of interest this paper lands on, in the CfP's own words: *graph modeling
and processing*; *graph data versioning and provenance*; *dynamic, temporal, and
evolving graphs*; *validation and verification techniques for graph data
processing*; *domain-specific graph analytics*; *practical implementations and
use cases*.

One risk the CfP raises directly: **"The journal language is German"** per
Springer's guidelines page, while the CfP says contributions are accepted in
both German and English. The CfP governs, so English is fine — but the cover
letter should name the CfP explicitly.

## The paper

**Operational Metadata as a Property Graph: A Reference Model and Query
Workload for Data Platform Reliability**

Thesis: the questions reliability engineers ask of a lakehouse — what breaks if
this changes, why is this table stale, who do I page — are *graph traversals*.
The metadata systems that hold the answers model their data as catalog records
with lineage attached, which makes some of those traversals inexpressible and
others expensive. The paper says what the graph must contain, states the
workload it must serve, and shows which of the queries today's systems can
actually answer.

### Contributions

1. **A reference property-graph model** for lakehouse operational metadata, with
   two commitments that distinguish it from catalog-style models: schema
   evolution carried as **temporal edges** rather than attributes, and
   **column-level lineage as first-class edges** rather than a dataset-level
   approximation.
2. **A seven-query reliability workload**, each query paired with the *structural
   property of the graph* it depends on — so the workload doubles as a
   requirements list.
3. **A capability gap analysis** of six open metadata systems against that
   workload, derived from their published metadata models.

### Out of scope, deliberately

No new benchmark, no performance measurements, no new system. This is a
Schwerpunktbeitrag with ten days of runway; an evaluation bolted on would be
thin, and thin is worse than absent. The paper states this in its own words
rather than leaving a reviewer to notice.

## The reference model

**Node labels.** `Dataset`, `SchemaVersion`, `Field`, `Pipeline`, `Run`,
`QualityAssertion`, `AssertionResult`, `Consumer`, `Principal`, `SLA`,
`Incident`.

**Edge types.**

| Edge | From → To | Carries |
|---|---|---|
| `READS` / `WRITES` | Pipeline → Dataset | dataset-level lineage |
| `DERIVES_FROM` | Field → Field | column-level lineage, `transform` property |
| `HAS_SCHEMA` | Dataset → SchemaVersion | `valid_from`, `valid_to` — **temporal** |
| `DECLARES` | SchemaVersion → Field | |
| `INSTANCE_OF` | Run → Pipeline | `started`, `ended`, `status` |
| `ASSERTS_ON` | QualityAssertion → Dataset \| Field | `kind`, `threshold`, `severity` |
| `PRODUCED` | Run → AssertionResult | |
| `CONSUMES` | Consumer → Dataset | consumer `criticality` tier |
| `OWNS` | Principal → Dataset \| Pipeline | |
| `GOVERNED_BY` | Dataset → SLA | `max_staleness` |
| `AFFECTS` | Incident → Dataset | |

## The query workload

Each query names the structural property it needs. That pairing is the point:
it turns "nice to have" into a testable requirement.

| | Query | Structural property required |
|---|---|---|
| **Q1** | Downstream impact: every Consumer reachable from a Dataset, ranked by criticality | transitive closure over typed edges |
| **Q2** | Breaking-change detection: which downstream Fields derive from a Field this schema change removes or retypes | **column-level** lineage + schema versioning |
| **Q3** | Root-cause candidates: upstream Datasets whose latest Run failed, or whose assertion failed, inside a window | temporal Run state on reverse traversal |
| **Q4** | Freshness propagation: implied staleness of a Dataset given the slowest upstream path | **path aggregation** (max over path), not mere reachability |
| **Q5** | Escalation routing: nearest Principal owning any node on the path from failure to the most critical affected Consumer | ownership in-graph + shortest path |
| **Q6** | Change attribution: which upstream schema or pipeline change became valid just before incident time *t* | **bitemporal** validity |
| **Q7** | Assertion coverage gaps: critical Consumers whose upstream closure contains an unasserted Dataset | **negation** over a traversal |

Q4, Q6 and Q7 are the discriminating ones — reachability alone does not answer
them, and they are where catalog-shaped models are expected to fail.

## Systems in the gap analysis

OpenLineage, Apache Atlas, DataHub, OpenMetadata, Egeria, Unity Catalog.

Rule for this table: **every cell traces to that system's published metadata
model, cited.** No capability asserted from memory, and a cell we could not
verify is marked unverified rather than guessed. Notes accumulate in
`GAP_ANALYSIS.md` with a source URL per claim.

## Independence from DARE

- Single `paper.tex` written from scratch; no shared text, figures or tables.
- No use of the DARE artifact, testbed or results.
- Blast radius is *not* the contribution here. DARE consumes a blast-radius
  number inside a decision procedure; this paper is about the graph and workload
  that make such a query expressible. DARE is cited as related work, third
  person.
- `check_overlap.py` against both DARE and Semantic DQ before submission; the
  measured figure is recorded in this directory, not asserted.

## Outline and page budget

Prose target **~4,000 words**, seven floats, nine pages.

| § | Section | Words | Floats |
|---|---|---|---|
| 1 | Introduction — the three questions, and why they are traversals | 600 | — |
| 2 | Background and related work — catalogs, lineage standards, provenance | 550 | — |
| 3 | The reference model | 800 | Fig. 1 (model), Table 1 (edges) |
| 4 | The query workload | 900 | Table 2 (queries ↔ properties), 1 query listing |
| 5 | Gap analysis of six systems | 750 | Table 3 (systems × queries) |
| 6 | Discussion — what the gaps cost, and what to change | 300 | — |
| 7 | Limitations and conclusion | 250 | — |
| | **Total** | **~4,150** | 6–7 floats |

If this overruns, the cut order is: the second query listing, then §2 (compress
to a dense paragraph per theme), then §6. **Not** §7 — the limitations are the
part that keeps the paper honest about having no evaluation.

## Verification

- **Page count 10–12 under `IEEEtran [conference]`**, asserted by a build
  check on the compiled PDF.
- Compiles clean under tectonic: no errors, no undefined citations or refs.
- Every gap-analysis cell cited to a primary source; unverified cells marked.
- References verified against live APIs (Crossref/DBLP), as on DARE.
- `check_overlap.py` LOW against DARE and Semantic DQ, figure recorded.
- No confidential employer material — the running example is synthetic and the
  paper says so.

## Stop rule

If the gap analysis is not substantially done by 25 September, stop and target a
later issue. A thin paper in the GI community journal costs more than no paper.
