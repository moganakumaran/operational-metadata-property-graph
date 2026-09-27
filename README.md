# Operational Metadata as a Property Graph

Manuscript and reproducibility artefact for *Operational Metadata as a Property
Graph: A Reference Model and Query Workload for Data Platform Reliability*.

Formatted for an **IEEE conference** (`IEEEtran`, two-column, US Letter).

The manuscript was originally written for the *Datenbank-Spektrum* special
issue "New Trends in Data Management for Property Graphs and Knowledge Graphs"
using Springer's `sn-jnl` class; that build is on the `main` branch of this
repository and is superseded. The IEEE build is the live one.

> **Status: under preparation, not yet submitted.** Findings and capability
> verdicts may still change.

## What the paper argues

Data platform reliability questions — which consumers a schema change breaks, why a
table is stale, which upstream change preceded an incident, who to page — are
graph traversals. The metadata to answer them is widely captured, so the real
question is whether what a system *represents* and what its interface can *ask*
together suffice. The paper uses a seven-query reliability workload as a
requirements instrument, and assesses six metadata systems on those two axes
separately.

Main findings: field-level lineage is comparatively mature; no system answered
more than three of the seven; the binding constraint differs by system — Apache
Atlas is limited by a query interface with no traversal construct despite
storing its graph in a graph database, while Unity Catalog exposes all six
query-operation classes through recursive SQL but several workload-specific
metadata elements are absent or only partially represented; and per-hop
latency, which freshness propagation needs, is represented by none of them.

OpenLineage receives no workload verdict: it defines no query layer, so the
answerability rule does not apply to it.

## Layout

| Path | What it is |
|---|---|
| `paper.tex`, `references.bib` | the manuscript (single file) |
| `paper.pdf` | current build, named |
| `paper_anon.tex`, `paper_anon.pdf` | blinded build for anonymous review, **generated** by `make_anon.py` from `paper.tex` — never hand-edit |
| `make_anon.py` | generates the blinded manuscript and refuses to write if any identifying string survives |
| `evaluation/` | executable reference implementation and the capability assessment data — see its own `README.md` |
| `check.py` | all submission gates; exit 0 = submittable |
| `consistency.py` | checks tying the manuscript to its artefacts |
| `evaluation/test_model_consistency.py` | endpoint-level figure/table/schema agreement, orphan detection, `via_pipeline` witness validity |
| `verify_refs.py` | reference verification against OpenAlex and Crossref |
| `backfill_dois.py` | finds a DOI for each reference lacking one; writes nothing unless title, year and first author all agree |
| `SCOPE.md` | venue facts and format findings |
| `GAP_ANALYSIS.md` | first-pass research notes behind the capability assessment |
| `REVISION_AUDIT.md`, `REVISION_REPORT.md` | pre-revision defect audit, and what the revision changed |
| `SUBMISSION_CHECKLIST.md` | current state and what remains |

`IEEEtran.cls` and `IEEEtran.bst` are **not** vendored: they are on CTAN and
tectonic fetches them from the TeX Live bundle. See `TEMPLATE_PROVENANCE.md`.

## Reproducing

Building the paper needs [tectonic](https://tectonic-typesetting.github.io/):

```bash
python3 check.py          # build + all gates
python3 consistency.py    # manuscript vs artefacts
```

Running the reference implementation needs Python ≤ 3.12 (Kùzu publishes no
3.13+ wheels):

```bash
python3.12 -m venv .venv && .venv/bin/pip install kuzu
.venv/bin/python evaluation/run_validation.py   # expect 7/7
```

The Kùzu database is not committed — `run_validation.py` rebuilds it from
`evaluation/schema.cypher` and `evaluation/synthetic_data.cypher` each run.

## How claims are kept honest

The mechanisms matter more than the results, and are reusable:

- **The capability table is generated, not typed.** It comes from
  `evaluation/capability_matrix.json`, where every cell carries a verdict, a
  one-line reason and a source URL. `make_tables.py` refuses to emit a cell
  without a citation key.
- **Answerability is derived, not judged.** Group (c) of the paper's
  capability table is
  computed from the two assessed layers, so a disputed verdict traces to a
  specific representation or expressiveness finding.
- **Expected results are fixed before the run.** `run_validation.py` holds the
  answer for each query; printing whatever the engine returned would show only
  that a query parsed.
- **A DOI is never taken from a search ranking.** `IEEEtran.bst` does not
  print DOIs, but the `.bib` carries them as the record a reader follows to the
  source, and the obvious way to supply them — accept Crossref's top hit — is
  how this project previously acquired two wrong references. `backfill_dois.py`
  requires title, year *and* first-author surname to agree before it writes,
  and on its first run that rule rejected a candidate offering the *European
  Ground Motion Service* in place of Hellerstein's *Ground*. Five references
  keep no DOI because CIDR, MLSys, DBPL and BTW register none; each is named
  in `check.py` rather than tolerated by a blanket exception.
- **`consistency.py` pins prose to data** — figure edges against the edge table
  against the executed schema, the stated path count against the enumeration
  the run produced, and the "no more than three of seven" claim against the
  computed matrix. Several of these exist because the corresponding error
  actually occurred during writing.

## Third-party files

None are redistributed. The build fetches `IEEEtran.cls` and `IEEEtran.bst`
from CTAN through tectonic; see `TEMPLATE_PROVENANCE.md`.

Springer's call for papers — the venue the manuscript was first written for —
is *not* included: it is their document and carries no redistribution licence.
`SCOPE.md` records its URL and the facts taken from it.

## Data

The running example is synthetic. No operational data, system names or
incidents from any organisation appear in this repository.

## Author

Mogana Kumaran Sivaraman — moganakumaran@ieee.org

(The blinded build `paper_anon.pdf` carries no author or affiliation; see
`make_anon.py`.)
