# Reference implementation and capability assessment

Artefact for *Operational Metadata as a Property Graph: A Reference Model and
Query Workload for Data Platform Reliability*.

Two independent things live here:

1. An **executable reference implementation** of the paper's model, with the
   seven workload queries and a runner that checks each against an expected
   result fixed before the run. This supports Sect. 6.2–6.3.
2. The **capability assessment data** — one record per cell, each with a
   reason and a citation — from which the paper's capability table
   (Table 2, three row groups) is generated. This supports Sect. 5 and 6.4.

## What this is not

It is **not a benchmark**. No timings are recorded and none should be inferred.
The graph is 44 nodes, chosen so that every expected answer is derivable by
hand; that is the point. A capability shown to be *expressible* here may be
impractical on a catalog-sized graph, and the paper says so in Sect. 6.5.

## Running it

**Python 3.12 or earlier** — Kùzu publishes no wheels for 3.13+.
**Kùzu 0.11.3**, pinned in `../requirements.txt`.

```bash
cd <repo root>
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python evaluation/run_validation.py
```

Expected output:

```
  [PASS] Q1  2 row(s)   transitive closure over typed edges
  [PASS] Q2  2 row(s)   column-level lineage closure with schema versioning
  [PASS] Q3  2 row(s)   reverse traversal with a temporal predicate
  [PASS] Q4  1 row(s)   variable-length traversal + path-local aggregation ...
  [PASS] Q5  1 row(s)   path selection over the alternating dataset-pipeline ...
  [PASS] Q6  2 row(s)   two independent temporal dimensions on one edge
  [PASS] Q7  1 row(s)   negation applied under a transitive closure

  7/7 queries executable and matching expected results
```

**Exit code is non-zero** if any query fails to execute or returns anything
other than its stated expectation, so this works unmodified as a CI gate.
`../check.py` runs it alongside the LaTeX build.

To check the model itself rather than the queries:

```bash
python3 evaluation/test_model_consistency.py
```

That compares Figure 1, Table 1 and `schema.cypher` **by endpoint**, and fails
if any stored relationship signature is left unexercised by every query. Both
matter: an earlier draft drew `owns: Principal → Consumer`, which the model
does not contain, and a label-level check passed it.

## Files

| File | Role |
|---|---|
| `schema.cypher` | The formal model: 11 node tables, 15 edge tables, plus the derived `feeds` table. Because Kùzu requires typed tables, this file *is* a machine-checked statement of the model. |
| `synthetic_data.cypher` | The synthetic retail lakehouse and the modelled 02:14 incident. |
| `derive_feeds.cypher` | Materialises the derived dependency relation from `reads`/`writes` per Eq. (3) of the paper. Run after the data. |
| `q1.cypher` … `q7.cypher` | The seven workload queries, one file each, with the semantics recorded in comments. |
| `run_validation.py` | Loads the graph, executes Q1–Q7, compares against `EXPECTED`, writes `results.json`. |
| `capability_matrix.json` | The assessment: rubric, systems and versions, per-cell verdict + reason + citation key, and the per-query requirement mapping. |
| `make_tables.py` | Generates the paper's capability table, splices it into `paper.tex`, and writes `SUPPLEMENTARY.md`. `--check` verifies both are current. |
| `test_model_consistency.py` | Endpoint-level agreement between figure, table and schema, plus orphan detection. |
| `results.json` | Output of the last validation run. |
| `SUPPLEMENTARY.md` | Generated. Three tables relocated from the manuscript to meet the venue page limit: requirement-to-model traceability, systems/versions/evidence, and per-query validation detail with interpretations. |

## Why the expected results are in the script

`EXPECTED` in `run_validation.py` holds the answer for each query, written
before the run. Printing whatever the engine returned would demonstrate only
that a query parsed. Three of the seven are worth deriving by hand to check us:

- **Q4** should return 36 against an SLA of 30. **Four** paths reach
  `daily_revenue`, totalling 36, 16, 16 and 4; the 36 is
  `fx_rates → fx_rates_smoothed → orders_clean → daily_revenue`
  (20 + 12 + 4). A per-dataset freshness number would not surface the breach,
  and neither would reachability. The full enumeration is written to
  `results.json` as `q4_paths`, and `../consistency.py` pins the paper's prose
  to it.
- **Q6** should return *both* schema versions with opposite verdicts: v2 valid
  at 02:14 but not yet recorded at 02:00, v1 recorded at 02:00 but no longer
  valid. That divergence is the reason the model is bitemporal.
- **Q7** should return exactly one pair: `pricing_service` (tier 1) and
  `fx_rates`, three hops upstream, carrying no assertion at the 02:14
  evaluation time under the schema version valid at that instant.
- **Q5** should return a **Pipeline**, not a dataset: `agg_revenue` at
  position 1, owned by `revenue_oncall`. The incident dataset
  `orders_clean` is deliberately unowned, so the nearest owner is the
  pipeline that writes the next dataset. Traversing only the derived `feeds`
  relation collapses that pipeline out of the path and returns the wrong
  principal — which is why `owns: Principal → Pipeline` is in the model.

## Kùzu dialect notes

Relevant if you port the queries to Neo4j or another engine.

- No `reduce()`. The path-local fold in Q4 is
  `list_sum(list_transform(rels(p), r -> r.latency_minutes))`.
- `SHORTEST` requires a lower bound of 1, so Q5 cannot ask for a zero-length
  shortest path; the zero-hop case is covered because `nodes(sp)` includes the
  start node.
- A node produced by `UNWIND` cannot be rebound as a node pattern, so Q5
  resolves ownership by primary key rather than by node identity.
- `ORDER BY` after `RETURN DISTINCT` must use the output aliases, not the
  node variables they came from.
- `interval('60 minutes')`, not `INTERVAL '60' MINUTE`.

None of these change which operations the workload requires; they change only
how the operations are spelled.

## Regenerating the paper's tables

```bash
python3 make_tables.py          # rewrite the tables inside ../paper.tex
python3 make_tables.py --check  # fail if they are stale
```

The paper carries all four generated tables. `SUPPLEMENTARY.md` keeps only the
per-query prose readings of the validation results, which are commentary rather
than evidence.

The manuscript is a single `.tex`, so the tables cannot be `\input`. They are
spliced between `% BEGIN GENERATED <name>` / `% END GENERATED <name>` markers
instead, which keeps `paper.tex` self-contained while keeping every capability
claim generated from `capability_matrix.json` rather than transcribed. Editing
inside a marked span by hand will be overwritten.

The generator refuses to emit a cell that has no citation key, which is the
mechanism behind the paper's claim that every verdict is traceable to a source.

## Amending the assessment

These systems are actively developed and some cells will age. To correct one,
edit its entry in `capability_matrix.json` — verdict, reason and citation key
— then run `make_tables.py` and rebuild. Group (c) of the capability table,
workload answerability, is *derived* from groups (a) and (b) by the rule in
Eq. (7), so it follows automatically and is never edited directly.

If a correction changes which queries a system can answer, check the prose in
Sect. 6.4, which names specific systems, and `../consistency.py`, which
asserts the paper's "no more than three of seven" claim against the computed
matrix and will fail if that stops being true.
