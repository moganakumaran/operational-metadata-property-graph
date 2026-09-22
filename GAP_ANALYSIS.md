# Gap analysis: six metadata systems against the reliability workload

**Rule for this file: every cell cites a primary source. A cell we could not
verify is marked `?` and says so in the paper.** Guessing here would destroy the
only thing that makes this paper more than opinion.

Research dates: 21 September 2026. Versions noted where the docs state one.

Legend: **Y** supported · **P** partial, with the qualification stated ·
**N** not supported · **?** not verified

---

## Summary matrix

| | OpenLineage | Atlas | DataHub | OpenMetadata | Egeria | Unity Catalog |
|---|---|---|---|---|---|---|
| **Q1** closure | S | P | Y | Y | Y | P |
| **Q2** breaking change | S | P | Y | Y | Y | **P** |
| **Q3** root cause | S | P | Y | Y | P | P |
| **Q4** freshness propagation | **N** | **N** | **N** | **N** | **N** | **N** |
| **Q5** escalation routing | N | P | P | P | P | P |
| **Q6** change attribution | P | **N** | P | P | **Y** | **N** |
| **Q7** coverage gaps | S | N | P | P | P | P |

**Every cell is resolved; no `?` remains.** Two were settled by reading source
rather than documentation, because the docs were silent exactly where the
workload depends on them.

**S** = the *data* is modelled by the specification, but the project ships no
query layer, so the traversal is the consumer's problem. OpenLineage is an
event-emission spec, not a store; scoring it on query expressiveness would be a
category error, and the paper should say so rather than give it an N.

---

## The three findings that carry the paper

### 1. Column-level lineage is largely a solved problem

This is worth stating plainly because it is the thing practitioners still treat
as the hard part. Four of six model it natively, and OpenLineage's facet is the
most expressive of them.

### 2. Path aggregation (Q4) is supported by nobody

**This is the cleanest result in the paper: a whole column of `N`.**

Not one system can answer "what is the implied staleness of this dataset given
the slowest path upstream". Freshness is modelled **per dataset** (DataHub has a
`FRESHNESS` assertion type) but never **along a path**. Reachability is not
enough: the answer is a `max` over a path, which is a semiring aggregation, and
no system in the set exposes one.

### 3. Valid time exists in exactly one system, and not the lakehouse-native ones (Q6)

**This finding was corrected during research and the correction matters.** The
first draft claimed no system models valid time. That is false:

- **Egeria does.** `effectiveFrom` / `effectiveTo` properties "control the time
  period that a specific element is visible on normal queries", and the
  `effectiveTime` retrieval parameter "specifies the time that elements must be
  effective in order to be returned on the request", with null disabling the
  filter. That is valid-time semantics, and it is the strongest temporal model
  in the set.
  <https://egeria-project.org/parameters/overview/>
- **DataHub has time-windowed lineage**, via `LineageFlags` carrying
  `startTimeMillis` and `endTimeMillis` — transaction time, applied at query
  time.

So the honest statement is narrower and more interesting than the one we
started with:

> Valid time is modelled by **one** system in the set, the one that is a
> governance framework rather than a lakehouse catalog. The systems that
> actually sit in front of lakehouse data — Unity Catalog, OpenMetadata,
> DataHub — version metadata by **write time** only. DataHub's versioned
> aspects and OpenMetadata's `major.minor` entity versions both record when the
> metadata changed, not when the schema was in force. **No system in the set
> combines both time dimensions.**

The distinction bites during a late-arriving or retro-corrected change, which
is precisely the case an incident investigation is about: "what did this
pipeline believe the schema was at 02:14?" is a valid-time question, and a
write-time version history answers a different one.

#### Egeria on edges: verified from source, and it is bitemporal

The open question was whether effectivity reaches **relationships**, since the
workload needs a `DERIVES_FROM` edge that was true last month and is not true
now. The prose documentation does not say. The source does:

- `InstanceProperties` declares `private Date effectiveFromTime` and
  `private Date effectiveToTime`, documented as *"Date/Time when the instance
  should be used"* and *"Date/Time when the instance should no longer be
  used"*.
- `Relationship` declares `private InstanceProperties relationshipProperties`.

So **relationships carry valid time**. Separately, `InstanceAuditHeader` — which
both `EntityDetail` and `Relationship` inherit through `InstanceHeader` —
carries `createTime`, `updateTime` and a monotonic `version`, i.e. transaction
time. Egeria therefore models **both time dimensions, on both nodes and edges**.

Source, `repository-services-apis`, `…/properties/instances/`:
`InstanceProperties.java`, `Relationship.java`, `InstanceAuditHeader.java`
(<https://github.com/odpi/egeria>).

This makes the finding sharper rather than weaker, and it is the better paper:

> The temporal modelling the reliability workload needs **already exists and is
> already specified** — in Egeria, a governance framework from the
> standards-and-interoperability lineage. It is absent from every system that
> actually sits in front of lakehouse data. The gap is not one of invention but
> of **adoption**: the lakehouse catalogs converged on column-level lineage and
> stopped, while the capability that answers incident-time questions sat
> unadopted in a neighbouring project.

Methodological note for the paper: this cell was **read from source, not from
documentation**, because the documentation was silent on the exact point the
workload depends on. Where the paper does this, it says so and cites the class
and field — a claim about a metadata model should be checkable against the
model.

### The structural cause, which is the paper's thesis

These are **catalogs with a graph index, not graph databases**. The query
surface is keyword search plus fixed-depth lineage expansion. Atlas is the
clearest evidence: its DSL is explicitly SQL-shaped ("the syntax loosely
emulates the popular Structured Query Language"), Gremlin is used internally but
**not exposed to end users**, and the `path` and `loop` clauses are
*"no longer supported"* — a traversal capability that was **removed**.

So Q4, Q5 and Q7 fail for one shared reason: the data is often present, but the
query layer cannot express path aggregation, path selection, or negation over a
traversal.

DataHub is the partial counterexample and the paper should say so rather than
flatten it. Its `LineageFlags` expose `entitiesExploredPerHopLimit`,
`ignoreAsHops` and a time window, and `searchAcrossLineage` /
`scrollAcrossLineage` / `searchAcrossLineageCounts` are real multi-hop
operations. That is genuine graph querying — but it is *filtered reachability*,
parameterised rather than programmable. It still cannot aggregate along a path
or negate over one.
<https://docs.datahub.com/docs/graphql/queries>

---

## Per-system notes

### OpenLineage (specification, not a store)

- Core entities **Job**, **Run**, **Dataset**; events are `RunEvent`,
  `JobEvent`, `DatasetEvent`.
  <https://openlineage.io/docs/spec/object-model>
- Dataset facets include `schema`, `dataSource`, `lifecycleStateChange`,
  `version`, `dataQualityMetrics`, `dataQualityAssertions`,
  `outputStatistics`. Run facets include `nominalTime`, `parent`,
  `errorMessage`, `sql`.
- **`columnLineage` facet** is the most expressive column-lineage model in the
  set: `fields` maps each output column to `inputFields`, each carrying
  `transformations` with `type` (`DIRECT` / `INDIRECT`), `subtype`
  (`IDENTITY`, `TRANSFORMATION`, `AGGREGATION`; `JOIN`, `GROUP_BY`, `FILTER`,
  `SORT`, `WINDOW`, `CONDITIONAL`), `description`, and a `masking` boolean.
  <https://openlineage.io/docs/spec/facets/dataset-facets/column_lineage_facet>
- The `DIRECT`/`INDIRECT` distinction is worth borrowing into the reference
  model: a filter column affects an output without deriving it, and
  breaking-change analysis needs both.
- No query language, no store, no ownership/consumer/SLA modelling.

### Apache Atlas

- Type system: `Referenceable` → `Asset` (name, description, **owner**) →
  `DataSet` and `Process`. Types support inheritance and arbitrary references.
  <https://atlas.apache.org/2.0.0/TypeSystem.html>
- **Column lineage since 0.8-incubating** via `ColumnLineageProcess`, a
  subclass of `Process` relating an output column to input columns, with
  dependency kind `SIMPLE` / `EXPRESSION` / `SCRIPT`. Caveat for the paper:
  this arrives through the **Hive bridge** (`hive_column`, `hive_process`), so
  it is connector-specific rather than a property of the core model.
  <https://atlas.apache.org/2.0.0/Hook-Hive.html>
- **DSL**: `FROM`-`WHERE`-`SELECT` with `GROUPBY`, `ORDERBY`, `LIMIT`,
  aggregates (`sum`, `min`, `max`, `count`), `LIKE`, `HAS`, classification
  filters. **Single-hop** property navigation only.
  **`path` and `loop` clauses are "no longer supported."** Gremlin is used to
  execute DSL internally but is not exposed.
  <https://atlas.apache.org/2.0.0/Search-Advanced.html>
- Classification propagation traverses lineage edges, with per-edge propagate
  flags and per-classification blocking — a traversal capability, but fixed to
  one purpose rather than queryable.
  <https://atlas.apache.org/2.0.0/ClassificationPropagation.html>
- No data-quality model. Temporal validity on relationships: **not verified**.

### DataHub

- Model is **Entities** (URN-identified) composed of **Aspects**, the "smallest
  atomic unit of write", plus **Relationships** declared with `@Relationship`
  annotations and indexed in a graph for bidirectional traversal.
  <https://docs.datahub.com/docs/metadata-modeling/metadata-model>
- Two aspect kinds: **versioned** (numeric versions in a relational store —
  Ownership, GlobalTags, Status) and **timeseries** (timestamped, in the search
  index — DatasetProfile, DatasetUsageStatistics). This is the basis for the
  transaction-vs-valid-time point: versioned aspects record write order.
- `upstreamLineage` carries **`fineGrainedLineages`** for column-level lineage,
  with transformation operations and confidence scoring; `ownership` present.
  <https://docs.datahub.com/docs/generated/metamodel/entities/dataset>
- **Assertion entity** with `assertionInfo` and the timeseries
  `assertionRunEvent` (`timestampMillis`, `runId`, `status`, `result`). Six
  types: `FIELD`, `VOLUME`, **`FRESHNESS`**, `DATA_SCHEMA`, `SQL`, `CUSTOM`.
  The freshness assertion is per-dataset, cron- or interval-based — **not**
  propagated along a path, which is exactly the Q4 gap.
  <https://docs.datahub.com/docs/generated/metamodel/entities/assertion>
- Query interfaces documented: primary-key lookup (`/entities`), search
  (`/entities?action=search`), and relationship traversal (`/relationships`
  taking direction, URN, relationship type). Multi-hop is an expansion, not a
  traversal language.

### OpenMetadata

- Schema-first, JSON-schema-defined entities and types.
- **Entity versioning** as `major.minor` from 0.1. Backward-compatible changes
  (description, tags, ownership) bump the minor by 0.1; backward-incompatible
  changes — *"for example when a column in a table is deleted"* — bump the
  major by 1.0. Useful for the paper: schema-breaking change is already a
  first-class, detectable event, but it is versioned by **write time**.
  <https://docs.open-metadata.org/v1.12.x/connectors/ingestion/versioning>
- Lineage is an edge model: `fromEntity`, `toEntity`, `lineageDetails`.
  `columnsLineage` carries `fromColumns` (fully qualified), `toColumn`, and
  `function`. Edges also carry `sqlQuery`, `pipeline`, and `source` (Manual,
  ViewLineage, QueryLineage…).
  <https://openmetadatastandards.org/lineage/lineage/>
- Edges carry `createdAt` / `updatedAt` / `createdBy` / `updatedBy` but
  **no validity window** — confirmed from the schema, and a clean citation for
  the bitemporality gap.

### Egeria

- Lineage models: **0750** `DataFlow`, `ProcessCall`, `ControlFlow`;
  **0755** `UltimateSource`, `UltimateDestination` (end-to-end tracing);
  **0770** `LineageMapping`, `DataMapping`; **0760** `BusinessLineage`
  classification; **0737** `ImplementedBy`; **0210** `DataSetContent`.
  <https://egeria-project.org/concepts/lineage/>
- `UltimateSource` / `UltimateDestination` are notable: a *materialised*
  transitive closure as a first-class relationship, which is a different design
  answer to Q1 than on-demand traversal. Worth a sentence in the paper.
- `Promise` (not yet created) and `Memento` (removed) classifications, surfaced
  only when `forLineage` is set — a partial answer to temporal modelling.
- **Still to verify:** field/attribute-level `LineageMapping`; effectivity
  dating (`effectiveFrom` / `effectiveTo`) on relationships; process run
  instances; query interface. Egeria is the weakest-evidenced column and must
  either be verified or carry explicit `?` marks.

### Unity Catalog (Databricks)

- Lineage captured automatically **down to column level** for Spark DataFrame
  and Databricks SQL workloads; covers notebooks, jobs, pipelines, UDFs,
  dashboards as consumers.
- Retention: Catalog Explorer "indefinitely" from 1 Sep 2024; system tables
  `system.access.table_lineage` and `system.access.column_lineage` keep a
  **rolling 1-year window**.
- Stated limitations, quotable and directly on point:
  - *"Lineage is not preserved for renamed catalogs, schemas, tables, views, or
    columns"* — a rename is precisely the schema change Q2 and Q6 are about, so
    lineage is lost exactly where it is needed.
  - *"Column lineage cannot be captured if the source or target is referenced
    as path"*.
  - Column-level UDF lineage not captured; RDDs and global temp views excluded;
    `runs submit` jobs absent from lineage views.
  <https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-lineage>
- Queryable via SQL over system tables, so closure needs a hand-written
  recursive CTE — possible, but the user writes the traversal.
- No SLA model and no native assertion model in UC itself.

---

## How the unverified cells resolved

All eight originally-unverified cells are now closed. Five of the eight changed
the answer, and two reversed a headline claim. Recording the rate matters: it is
the argument for the sourcing rule at the top of this file.

| Item | Resolution | Changed the answer? |
|---|---|---|
| DataHub GraphQL traversal depth | `searchAcrossLineage`, `scrollAcrossLineage`, `searchAcrossLineageCounts`; `LineageFlags` with `entitiesExploredPerHopLimit`, `ignoreAsHops`, time window | **Yes** — REST docs alone understated DataHub |
| Egeria effectivity dating | Valid time confirmed, `effectiveFromTime`/`effectiveToTime` | **Yes** — falsified "no system models valid time" |
| Egeria effectivity on *relationships* | Confirmed **from source**: `Relationship` carries `InstanceProperties`, which declares both fields | **Yes** — made Egeria bitemporal on edges |
| Egeria column-level lineage | `DataMapping` (model 0770) "maps, typically, a schema attribute from one asset to the equivalent schema attribute of another", with `formula`, `formulaType`, `query` | **Yes** — Q2 `?` → `Y` |
| Atlas relationship temporality | Confirmed **from source**: see below | **Yes** — Q6 `?` → `N` |
| Egeria process runs | Engine Actions / Governance Action Process Steps | No — `P` |
| Egeria quality assertions | Annotations (0610), Data Profiling (0620) | No — `P` |
| OpenMetadata negation/aggregation | Visual query builder, AND/OR with "Not equal to", "Not in", "Not contain" — but no traversal | No — confirmed `P`/`N` |

### Atlas temporality, read from source

`AtlasRelationship` declares `createdBy`, `updatedBy`, `createTime`,
`updateTime`, `version`, `status` — **transaction time only**. There is no
validity window.

`AtlasClassification` *does* declare `List<TimeBoundary> validityPeriods`
(`startTime`, `endTime`, `timeZone`).

So valid time exists in Atlas, **but only on classifications** — a tagging and
governance concern — and never on the relationships that lineage queries
traverse. This is the sharpest contrast in the paper:

> Two systems from the open-metadata-standards lineage both thought carefully
> about time. Atlas put validity on *tags*; Egeria put it on *instance
> properties*, which entities and relationships both carry. Only the second
> choice makes "what did this pipeline believe the schema was at 02:14?"
> answerable, because only the second attaches time to the edges a lineage
> query walks.

Source: `intg/src/main/java/org/apache/atlas/model/instance/`,
`AtlasRelationship.java` and `AtlasClassification.java`
(<https://github.com/apache/atlas>).

### OpenMetadata: negation without traversal

Advanced search is a visual query builder with AND/OR grouping and genuine
negation operators — "Not equal to", "Not in", "Not contain" — over attributes
such as owner, tag, tier, service and schema. What it cannot do is combine that
negation with a traversal, which is exactly what Q7 asks ("critical consumers
whose upstream closure contains an unasserted dataset"). The negation is there;
the closure it must apply to is not. That is a more precise and more useful
criticism than "no negation support", and it generalises: across the set, the
missing piece is almost never the predicate, it is the traversal the predicate
needs to range over.
<https://docs.open-metadata.org/latest/how-to-guides/data-discovery/advanced>

---

## Superseded: open items

</details>
