# Final revision report

Focused technical pass. The central argument, organisation, tone and
contribution are unchanged; what changed is the evidence behind them and three
places where the manuscript said something the implementation did not support.

Gate state: **nine of ten pass.** The exception is the page count, 13 against
the CfP's 8–10, which was already open before this pass.

---

## 1. Figure/model corrections

**Figure 1 contained a relationship the model does not have, and omitted one it
does.**

| | Figure 1 drew | Model |
|---|---|---|
| `owns` | Principal → **Consumer** | ❌ no such signature |
| `owns` | Principal → Pipeline | ✅ |
| `owns` | *(absent)* | ❌ Principal → **Dataset** missing |

`QualityAssertion → Pipeline` was checked for and does **not** appear. Table 1
and `schema.cypher` were already in exact agreement — the defect was confined
to the figure.

**Why it survived.** `consistency.py` compared edge *label* sets. Both the
bogus and the correct edge are labelled `owns`, so the check passed while the
figure was wrong.

**Fixed:** the figure now draws both real `owns` signatures, and draws them
**heavier**, because after the Q5 correction the answer depends on which owned
node is nearer the incident. A new endpoint-level test
(`evaluation/test_model_consistency.py`) compares figure, table and schema by
*endpoint* and was negative-tested: reintroducing the original bug fails two
checks, naming both the spurious edge and the missing one.

## 2. Relationship-count correction

The manuscript said **"fifteen edge types"**, conflating labels with
signatures. Counted from `schema.cypher`:

| | Count |
|---|---|
| Node labels | **11** |
| Stored relationship labels | **13** |
| Stored typed endpoint signatures | **15** (`asserts_on` ×2, `owns` ×2) |
| Derived relations | **1** (`feeds`) |

Adopted wording: *"eleven node labels, thirteen stored relationship labels
spanning fifteen typed endpoint signatures, and one derived dataset-dependency
relation."* Reconciled in the abstract, contributions, §3, Table 1 caption,
Figure 1 caption and the conclusion. `fifteen edge types`, `44 nodes` and
`65 edges` no longer appear anywhere.

## 3. Q5 correction

**Old:** traversed only the derived `feeds` relation and matched
`(pr:Principal)-[:owns]->(od:Dataset)`. `Pipeline` appeared **zero times**.
Because `feeds` collapses `Dataset ← reads — Pipeline — writes → Dataset` into
one hop, a principal owning a pipeline could never be returned — and
`owns: Principal → Pipeline` therefore served no query, contradicting the
paper's own *"no element is present that serves no query."*

**New:** Q5 is defined over the alternating dependency path, now Eq. (8):

```
d0 <-reads- p1 -writes-> d1 <-reads- p2 -writes-> ...
```

with position interleaved — dataset *k* at 2*k*, the pipeline realising hop
*k* at 2*k*+1 — and ownership resolved over **both** node kinds. The ranking
logic is unchanged: most critical consumer, ties by name, shortest path,
nearest owned node, ties by principal name.

The alternating path is *recovered* rather than traversed: no engine in common
use supports variable-length traversal over a composite pattern, so each
`feeds` hop is expanded back through `via_pipeline`, which Eq. (3) records.
This is lossless and the paper says so.

**Fixture changed so pipeline ownership decides the answer.** `orders_clean`
is now deliberately unowned and a new `revenue_oncall` principal owns the
`agg_revenue` pipeline.

| | Old expected | New expected |
|---|---|---|
| Escalation point | `orders_clean` (Dataset, pos 0) | **`agg_revenue` (Pipeline, pos 1)** |
| Principal | `data_platform_team` | **`revenue_oncall`** |

Traversing only `feeds` would now page the wrong team, which is the
demonstration the model element needed.

## 4. Q7 temporal correction

**Old:** input was criticality threshold `k` alone, while the query judged
coverage against the schema "in force"; `q7.cypher` hard-coded a timestamp and
tested only `valid_to >`, never `valid_from ≤`.

**New:** input is `(k, t)`. The schema in force at `t` satisfies
`valid_from ≤ t < valid_to` — the full interval, Eq. (1) — and coverage is
judged against the fields *that* version declares. The existing decision that
coverage means **existence, not outcome** is now stated explicitly: a failing
assertion still counts, because Q7 asks what is unwatched and Q3 asks what is
broken. Expected result unchanged (`pricing_service`, `fx_rates`), now for the
right reason.

## 5. Unity Catalog reassessment

Researched against current Databricks documentation.

**Quality assertions: N → P.** `system.data_quality_monitoring.table_results`
records freshness and completeness **results** per table (status, observed and
predicted values) — this corresponds to `AssertionResult`. But the
documentation shows **no companion table of check definitions**: anomaly
detection is *inferred from a table's own history rather than authored*,
enabled per schema or catalog rather than declared per check, and
**table-scoped with no column-level checks** (completeness slicing by column
group is Beta). Nothing corresponds to `QualityAssertion`. Under the rubric
that is **P** — result state exists, the definition object the model
distinguishes does not, and the scope is narrower than the field-level
assertions Q7 admits.

**Run history: P, reason corrected.** The claim *"no documented join to
lineage records"* was too strong. Confirmed: `job_run_timeline` documents
joins only to `lakeflow.jobs`, `billing.usage` and `compute.clusters` on
`workspace_id`/`job_id`/`run_id`, and none to the lineage tables. **But** a
table-to-job association does exist elsewhere —
`table_results.upstream_jobs` carries `job_id` and `workspace_id` beside the
table identity, which are exactly those join keys. Verdict unchanged, but now
because that path requires anomaly detection enabled and covers only monitored
tables, not because no mapping exists.

**Recursive CTE: Y retained, now per-operation.** Re-verified: `WITH
RECURSIVE` from DBR 17.0, default 100 recursion levels, one-million-row bound.
Each of the six operations now carries its own reason in the matrix rather
than resting on a block claim — closure and reverse traversal by join
direction; path-local fold because a recursive CTE carries columns forward;
path selection because depth is an ordinary column; temporal predicates as
ordinary SQL in the recursive step; negation because `NOT EXISTS` applies to
the materialised result.

## 6. Capability matrix changes

| Cell | Old | New |
|---|---|---|
| UC · quality assertions | N | **P** |
| UC · run history | P | P *(reason rewritten)* |
| UC · per-hop latency | N | N *(reason now addresses DQM freshness)* |
| UC · all six expressiveness rows | Y | Y *(per-operation reasons)* |

Derived by Eq. (7), **not edited**:

| | Old | New |
|---|---|---|
| UC · **Q3** Root-cause candidates | N | **P** |
| UC · **Q7** Coverage gaps | N | **P** |

Unity Catalog moves from Y=2 P=0 N=5 to **Y=2 P=2 N=3**. Every headline claim
survives: max answered still 3, three systems still answer none outright, the
Q4 row is still uniformly absent, per-hop latency still represented by none.

## 7. Artefact/reproducibility changes

- §8 no longer says the artefact is *"released with this paper."* The
  repository exists and builds from a clean clone but is **private**, so the
  wording is now *"will be made publicly available with the final version."*
  No URL or DOI is claimed.
- `requirements.txt` added, pinning `kuzu==0.11.3`; README gives Python
  version, install, exact command, expected `[PASS] Q1…Q7` output, and states
  the non-zero exit on mismatch.
- `evaluation/test_model_consistency.py` added — 28 checks, wired into
  `check.py`.
- README documents why Q5 returns a Pipeline and why that makes
  `Principal → Pipeline` load-bearing.

## 8. Numerical consistency check

31 claims re-derived from the artefacts, all passing: 11 node labels, 13
stored labels, 15 signatures, 1 derived relation, **45 nodes**, **64 edges**,
14 edge tables, 4 derived `feeds` edges, 4 paths into `daily_revenue` totalling
36/16/16/4, SLA 30 breached, 7/7 matched, Q5 returning a Pipeline at position
1, max answered 3, three systems answering none, Q4 row absent throughout,
per-hop latency absent in all six.

Counts moved (44→45 nodes, 65→64 edges) because the Q5 fixture added the
`revenue_oncall` principal and reallocated ownership. Every occurrence in the
manuscript was updated.

## 9. Manuscript claims changed

- Counting language throughout (§2 above).
- §4.1 Q5 — rewritten around Eq. (8); new paragraph explaining why Q5 is the
  exception that keeps the Pipeline while Q1/Q3/Q4/Q7 use `feeds`.
- §4.1 Q7 — evaluation time added; existence-not-outcome made explicit.
- §4.1 Q3 — now traverses `evaluates` to **name** the failing assertion. This
  fixed a genuine orphan: `evaluates` was justified in §3 and §4.1 by Q3, but
  `q3.cypher` never traversed it, so the stated justification was false.
- §6.2 — Q5's worked reading rewritten; Q7's reading now references the
  evaluation time.
- §6.3 — new Unity Catalog paragraphs on data-quality monitoring and the
  run/lineage association; per-hop latency paragraph now acknowledges DQM
  freshness and explains why it still is not an edge quantity; summary line
  notes UC's two partials.
- Abstract, discussion and conclusion re-checked sentence by sentence against
  the new matrix. **All survived**; only the counting clause changed.

## 10. Remaining limitations

- **13 pages against an 8–10 limit.** This pass added roughly a page
  (Eq. (8), the Q5 rationale, the UC evidence). The length question was
  already open and is unresolved.
- The artefact repository is private, so the reproducibility claim is a
  commitment rather than a link.
- Q5's alternating path is recovered from `feeds.via_pipeline` rather than
  traversed natively. Lossless, but it is a workaround for an engine
  limitation and the paper says so.
- Unity Catalog's `downstream_impact` and `root_cause_analysis` structs are
  Beta; the assessment does not rely on them, but they may change the picture.
- Minimality remains **exhibited, not proved** — every element is now
  exercised by a query or by the documented derivation of `feeds`, which is
  the strongest claim the evidence supports.
- `reads` is exercised only by `derive_feeds.cypher`, not by any query
  directly. Legitimate, and now stated rather than glossed.
