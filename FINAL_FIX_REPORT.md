# Final fix report

Correction pass only. No restructuring, no new contribution. Ten gates, nine
pass; the exception is the page count, which was already open.

---

## via_pipeline correction

Q5 relied on `via_pipeline` to rebuild the alternating Dataset–Pipeline–Dataset
path, but the model never defined it — Eq. (3) was purely existential, so the
sentence claiming Eq. (3) *recorded* the witness was unsupported.

**Eq. (3)** now derives one edge per witness pipeline,
`d1 --feeds[p]--> d2`, and a new **Eq. (4)** defines
`via_pipeline(e) := p`. The text states explicitly that the bracketed *p* is
**not a third endpoint** — `feeds` stays an ordinary Dataset→Dataset edge and
*p* is retained as an edge property.

**§3.2** now explains why the witness is preserved: the rest of the workload
needs only dataset-to-dataset dependency, but ownership attaches to datasets
*and* pipelines, so Q5 alone must reconstruct the node Eq. (3) otherwise
hides. The latency equation now says latency and witness refer to the same
pipeline by construction.

**Table 1** lists the derived row's properties as `via_pipeline,
latency_minutes`, and the caption says `via_pipeline` identifies the witnessing
Pipeline.

**Schema** already declared the property; **Q5** now points at Eq. (4) rather
than Eq. (3).

## Q5 validation

Expected result unchanged, as the brief required — the fixture already
supported it:

| | |
|---|---|
| Most critical consumer | `pricing_service` (criticality 1) |
| Escalation point | **`agg_revenue`, a Pipeline, at position 1** |
| Principal | **`revenue_oncall`** |

`orders_clean` is unowned, so the nearest owned node is the pipeline writing
the next dataset — nearer than `daily_revenue`'s owner at position 2.
Traversing only `feeds` would collapse that pipeline out of the path and page
the wrong team, which is what makes `owns: Principal → Pipeline` load-bearing
rather than decorative.

## Wording corrections

| Where | Was | Now |
|---|---|---|
| Abstract, Unity Catalog | "can express every required operation in recursive SQL but **lacks the metadata** to feed it" | "exposes the required query operations through recursive SQL, but several workload-specific metadata elements are **absent or only partially represented**" |
| §6.3, zero answers | "three answered **none**" | OpenLineage now explicitly **receives no workload verdict** because it defines no query layer, so Eq. (8) does not apply; reading that as *answers nothing* would confuse a specification with an implementation |
| §6.3, ranking | "Egeria's three Y and two P are **at least as strong a showing as** DataHub's" | "DataHub and Egeria each answer three queries natively, but not the same three… **We draw no ranking**" |
| §6.3, query surface | "the **strongest** query surface in the set" | "Among the evaluated executable interfaces, Databricks SQL is the one that **exposes all six query-operation classes** the workload uses" — verified: all six UC expressiveness cells are Y |
| §7, UC gap | "**four of the five** unanswerable queries would become answerable" | "**all five** … are bound by representation rather than by recursive SQL" — recomputed; every one of Q2, Q3, Q4, Q6, Q7 is representation-bound, none expressiveness-bound |

**One further discrepancy found while checking §14.** Q6's prose said it
examined *"the affected dataset"*, but `q6.cypher` examines `orders_raw` —
which is *upstream* of the affected dataset (`orders_clean`) and never
traverses `affects`. Corrected in both: Q6 takes a dataset plus the two times,
and the worked example uses an upstream candidate surfaced by Q3. Q3 narrows,
Q6 attributes.

## Numerical consistency

All verified from the artefacts, no literals duplicated by hand:

| | |
|---|---|
| Node labels | 11 |
| Stored relationship labels | 13 |
| Stored endpoint signatures | 15 |
| Derived relations | 1 |
| Synthetic nodes / edges | 45 / 64 |
| Derived `feeds` edges | 4 |
| Workload queries | 7 |
| Query-operation classes | 6 |
| Compared systems | 6 |

Confirmed absent: `44 nodes`, `65 edges`, `14 edge types`, `fifteen edge
types`, `affected dataset`, `strongest query surface`, `at least as strong`,
`three answered none`, `four of the five`, `released with this paper`.

## Capability matrix

**No verdict changed in this pass.** The matrix was already correct from the
previous revision; this pass only corrected prose that had drifted from it.
Re-confirmed against the JSON as source of truth:

- representation — quality assertions **P**, run history **P**, field-level
  lineage **P**, schema versions **N**, per-hop latency **N**, valid time
  **N**, transaction time **P**
- answers — Q1 **Y**, Q2 **N**, Q3 **P**, Q4 **N**, Q5 **Y**, Q6 **N**,
  Q7 **P**

Table 2 regenerated from `capability_matrix.json`; `make_tables.py --check`
was negative-tested by flipping a cell and confirming it reports `STALE`.

## Tests

| | |
|---|---|
| Q1–Q7 | **7/7 PASS** |
| Model consistency (endpoints, orphans, witness) | **PASS**, 0 failures |
| Capability-table vs JSON | **PASS**, negative-tested |
| Witness validity | **PASS** — 0 invalid `via_pipeline`, 0 latency mismatch |
| Manuscript self-consistency | **PASS**, 0 failures |
| References | 23 verified + 6 web, 0 to check |

New checks added this pass, both negative-tested:

- Every derived `feeds` edge must carry a `via_pipeline` that genuinely reads
  the source and writes the target, and whose latest successful run supplies
  `latency_minutes`. Corrupting the witness produces 4 invalid edges **and**
  drops Q5 to failing — the coupling the check exists to protect.
- The model test now asserts the schema declares `via_pipeline`, the paper
  formally defines it, and Q5 uses it.

Traceability re-verified mechanically — every stored relationship is
exercised: `affects` Q3/Q5, `asserts_on` Q7, `consumes` Q1/Q5/Q7, `declares`
Q7, `derives_from` Q2, `evaluates` Q3, `governed_by` Q4, `has_schema` Q6/Q7,
`instance_of` Q3, `owns` Q5, `produced` Q3, `writes` Q3, and `reads` by the
documented derivation of `feeds`. Q4 does read the SLA
(`governed_by`, `max_staleness_minutes`).

## Remaining limitations

- **14 pages against the CfP's 8–10.** This pass added roughly a page (Eq. (4),
  the witness rationale, the reworded UC paragraphs) and I trimmed part of it
  back. Page 14 carries only 38 words of overflowing references; chasing that
  further is not worthwhile while the paper is over the limit anyway. The
  length decision remains open and unresolved.
- The artefact repository is still private, so §8's wording remains a
  commitment rather than a link. Replace it with the URL once public.
- Q5's alternating path is recovered from `via_pipeline` rather than traversed
  natively, because no common engine supports variable-length traversal over a
  composite pattern. Lossless, now formally grounded in Eq. (4), and stated.
- Unity Catalog's `downstream_impact` and `root_cause_analysis` structs are
  Beta; the assessment does not rely on them.
- Minimality remains **exhibited, not proved**.
- `reads` is exercised only by the derivation of `feeds`, not by a query
  directly — stated rather than glossed.
