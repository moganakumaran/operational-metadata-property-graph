# Final technical audit

Read of `paper.tex`, the Figure 1 TikZ source, Table 1, Table 2,
`evaluation/schema.cypher`, `synthetic_data.cypher`, `q1`–`q7.cypher`,
`derive_feeds.cypher`, `results.json`, `capability_matrix.json` and the
artefact README, before any edit. Scope limited to the issues in the brief.

Severity: **A** must fix (the paper states something false) · **B** weakens a
claim · **C** wording.

---

## 1. Figure 1 vs Table 1 vs schema — **A**

Table 1 and `schema.cypher` agree **exactly**: same 14 labels, same 16
endpoint signatures, nothing in one and not the other. The defect is isolated
to **Figure 1**.

| | Figure 1 draws | Model says |
|---|---|---|
| `owns` #1 | Principal → **Pipeline** | ✅ correct |
| `owns` #2 | Principal → **Consumer** | ❌ **no such relationship exists** |
| `owns` #3 | *(absent)* | ❌ **Principal → Dataset is missing** |

So Figure 1 simultaneously **invents** `Principal → Consumer : owns` and
**omits** `Principal → Dataset : owns`. Every other edge is correct.

`QualityAssertion → Pipeline` does **not** appear — that suspicion is clear.

**Why this survived.** `consistency.py` compares edge *label* sets between
figure and table. Both bogus and correct edges are labelled `owns`, so the
name-set check passed. The checker must compare **endpoints**, not names.

## 2. Edge-count terminology — **A**

Counted from `schema.cypher`:

| | Count |
|---|---|
| Node labels | **11** |
| Stored relationship labels | **13** (`reads, writes, has_schema, declares, derives_from, instance_of, produced, evaluates, asserts_on, consumes, owns, governed_by, affects`) |
| Stored typed endpoint signatures | **15** (`asserts_on` ×2, `owns` ×2) |
| Derived relations | **1** (`feeds`, Dataset→Dataset) |

The manuscript says **"fifteen edge types"**, conflating labels with
signatures. The brief's proposed wording matches the data and should be
adopted verbatim.

## 3. Q5 excludes pipeline owners — **A**

`q5.cypher` traverses only `feeds` and matches only
`(pr:Principal)-[:owns]->(od:Dataset)`. **`Pipeline` appears zero times in the
query.** Because `feeds` collapses `Dataset ← reads — Pipeline — writes →
Dataset` into a single hop, the pipeline is erased from the path, so a
principal owning a pipeline can never be returned.

Consequence for the paper's own claim: the `owns: Principal → Pipeline`
signature **serves no query**, contradicting *"no element is present that
serves no query."*

## 4. Two further orphaned elements the brief did not list — **A**

A usage audit of all seven queries against the schema found:

| Element | Used by | Status |
|---|---|---|
| `evaluates` (AR → QA) | **nothing** | **orphaned** |
| `reads` (P → D) | `derive_feeds.cypher` only | legitimate, but not by a *query* |
| `owns` (Pr → Pipeline) | **nothing** | orphaned (item 3) |

`evaluates` is the serious one. §3 justifies it — *"Q7 asks whether an
assertion exists and Q3 whether one failed; collapsing them leaves one
unanswerable"* — and §4.1 repeats it. But `q3.cypher` reaches
`AssertionResult` via `produced` and tests `ar.outcome` **directly**; it never
traverses `evaluates` to the `QualityAssertion`. The stated justification is
contradicted by the implementation.

`reads` is fine but the traceability argument must say it is exercised by the
**derivation** of `feeds`, not by a query.

## 5. Q7 has no evaluation time — **A**

Q7 decides whether an assertion covers the schema *"in force"*, but takes only
a criticality threshold `k` as input. `q7.cypher` hard-codes
`timestamp('2026-09-21 02:14:00')` and tests only `valid_to >`, never
`valid_from ≤`. Since `has_schema` is bitemporal, Q7 needs an explicit
evaluation time `t` and the full interval test.

## 6. Unity Catalog capability cells — **pending research**

Three cells to re-derive from current Databricks documentation, not carried
forward:

- **quality assertions = N.** Must be re-checked against Data Quality
  Monitoring / `system.data_quality_monitoring.*`, distinguishing an
  assertion *definition* (≈ `QualityAssertion`) from *result* state
  (≈ `AssertionResult`).
- **run history = P**, justified by *"no documented join"* between
  `system.lakeflow.job_run_timeline` and lineage. Verify; if no mapping is
  found, the wording must become *"we found no documented identifier
  mapping"* rather than *"there is no join"*.
- **recursive CTE = Y on all six expressiveness rows.** Re-verify per
  operation rather than as a block claim.

If any changes, Table 2(c) must **regenerate** via Eq. (7), never be edited.

## 7. Artefact availability language — **B**

§8 says the artefact is *"released with this paper."* The repository
(`moganakumaran/operational-metadata-property-graph`) exists and builds from a
clean clone, but is **private**. Either publish it and cite the URL, or change
the wording to a commitment about the final version.

## 8. Minimality language — **C, currently correct**

§6.2 already says necessity is *"exhibited rather than proved"* and §6.4
repeats it. No overclaim found. Preserve, and make it true again by fixing
items 3 and 4.

---

## Disposition

Items 1–5 are internal contradictions fixable from the artefacts. Item 6 needs
external research. Items 7–8 are wording.

Two guards to add so this class of defect cannot recur:
- endpoint-level figure/table/schema comparison in `consistency.py`
- a model-consistency test asserting every stored signature is exercised by a
  query or by the documented derivation
