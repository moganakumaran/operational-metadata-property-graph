# Revision audit

Read of the complete manuscript (`paper.tex`, 616 lines, 9 pages) before any
edit. Every item below is a defect in the paper as it stands, with the line
reference and what a reviewer would say.

Severity: **A** = must fix, the paper is wrong or indefensible as written ·
**B** = should fix, weakens the contribution · **C** = polish.

---

## 1. Undefined graph elements

| # | Sev | Issue |
|---|---|---|
| 1.1 | **A** | **`feeds` is undefined.** Listing 1 (Q4) matches `(:Dataset)-[:feeds*]->(d:Dataset)`. No `feeds` edge appears in Table 1, Figure 1, or the formal model. The paper's single executable artefact uses a relationship the model does not contain. |
| 1.2 | **A** | **`lag_minutes` is undefined.** Listing 1 reads `r.lag_minutes` off each relationship. No edge property of that name is defined anywhere, and the paper never says what latency it denotes (expected? observed? SLA?). |
| 1.3 | **A** | **`of` (AssertionResult → QualityAssertion) is drawn in Figure 1 but absent from Table 1.** Table 1 claims to be exhaustive ("an edge serving no query is not in the model"), so the figure and the model contradict each other. Q3 and Q7 both need this edge to get from a run to what was asserted. |
| 1.4 | **A** | **Transaction time is never represented.** §3 and Q6 argue that incident analysis needs valid time *and* transaction time, and §5 marks systems down for having only write time. But the reference model defines only `valid_from`/`valid_to`. The paper demands of others a capability its own model does not specify. This is the single most serious defensibility hole. |
| 1.5 | **B** | **Node properties are used but never defined.** `criticality` (Consumer), `max_staleness` (SLA), run `status`/`started`/`ended`, assertion `severity`/`threshold` all appear in prose or are implied by queries; none is formally declared. |
| 1.6 | **B** | **Incident carries no time.** Q6 asks "which change was in force just before incident time $t$", but the model gives Incident only an `affects` edge and no timestamp property. |
| 1.7 | **B** | **No Field→Dataset membership edge.** A field belongs to a dataset only via `Dataset -[:has_schema]-> SchemaVersion -[:declares]-> Field`. That is defensible but never stated, and it means field membership is itself schema-version-dependent — which the paper should say explicitly because it affects Q2 and Q7. |
| 1.8 | **C** | `SLA` is in the model "for Q4", but Listing 1 never references SLA or `max_staleness`, so the edge's stated justification is not demonstrated. |

## 2. Internal inconsistencies

| # | Sev | Issue |
|---|---|---|
| 2.1 | **A** | **`asserts_on` endpoint disagreement.** Table 1 lists `A → D †` (Assertion→Dataset, dagger for the alternative); Figure 1 draws QualityAssertion→**Field**. Table and figure disagree on the primary endpoint. |
| 2.2 | **A** | **Q4's aggregation is described wrongly.** Table 2 calls the requirement "path aggregation ($\max$ over a path)". Listing 1 actually does `reduce(+)` *along* each path and then `max` *across* paths. Those are two different operations at two different scopes; the paper's own summary of its own key query is incorrect. |
| 2.3 | **B** | **Figure 1's temporal box excludes `has_schema`.** The dashed box fits SchemaVersion and Field, so it encloses `declares` and the `derives_from` loop. But §3 says `has_schema` is the edge carrying `valid_from`/`valid_to`, and that edge sits outside the box. Caption and figure disagree with the text. |
| 2.4 | **B** | **Table 1 says `instance_of` serves "Q3, Q4".** Q4 as implemented never touches Run or `instance_of`. |
| 2.5 | **B** | **Letter collision on "S".** Table 1's legend uses **S** for SchemaVersion; Table 3 uses **S** for "specification only". Two tables, same letter, different meanings. |
| 2.6 | **B** | **The intro's four questions never map to Q1–Q7.** The opening lists four questions, then re-describes them in a different order ("The first is a reachability query...the fourth is a shortest path"), covering roughly Q1, Q3/Q6, Q4, Q5 — Q2 and Q7 appear from nowhere in §4. The motivating narrative and the workload are not connected. |
| 2.7 | **A** | **Direct self-contradiction on the central claim.** §1: "These systems are *catalogs with a graph index*, not graph databases." §2: "Apache Atlas is built on a graph database." The paper refutes its own headline framing two pages later. |

## 3. Unsupported or over-absolute claims

| # | Sev | Issue |
|---|---|---|
| 3.1 | **A** | "no system can aggregate along a path" (abstract), "Path aggregation is supported by nobody" (§5), "Path aggregation is available nowhere" (§7). Universal quantification over all systems from a sample of six, under one set of interfaces, at one point in time. |
| 3.2 | **A** | "Column-level lineage is settled" / "which we report as a solved problem". Four of six, two with connector- or rename-scoped caveats. Not "settled". |
| 3.3 | **A** | "bitemporal validity is implemented in exactly one system". Must be scoped to the six evaluated. |
| 3.4 | **A** | **"Every ingredient for Q4 is stored in at least one system"** (§5). Nothing in the paper shows that any system stores a per-edge latency. DataHub's `FRESHNESS` assertion is a per-dataset schedule, not an edge latency, so the claim is not supported by the cited evidence. |
| 3.5 | **B** | "The gap is one of adoption rather than invention" — asserted three times as established fact; it is an interpretation. |
| 3.6 | **B** | "we would expect the Q4 row to survive any reasonable variation" — speculation; acceptable only if marked as such. |
| 3.7 | **B** | "five of the seven queries" (§6) is arithmetic over a claim, not over evidence; needs to be shown. |

## 4. Methodology gaps

| # | Sev | Issue |
|---|---|---|
| 4.1 | **A** | **Y/P/N/S have no definitions.** Nothing in the paper says what distinguishes Y from P. The central table is therefore not reproducible by another researcher — the most damaging single criticism available to a reviewer. |
| 4.2 | **A** | **Representation and query expressiveness are conflated.** Q2 ("column-level lineage") is a *representation* property; Q4 ("path aggregation") is a *query* property. They share one matrix and one scale, so a P can mean "data missing" or "query surface missing" — opposite problems with opposite remedies. |
| 4.3 | **A** | **No versions or interfaces recorded in the paper.** Which Atlas? Which DataHub? Which interface — REST, GraphQL, SQL, UI? `GAP_ANALYSIS.md` has some of this; the manuscript has none. |
| 4.4 | **A** | **Unity Catalog was scored without considering recursive SQL.** The working notes acknowledge closure "needs a hand-written recursive CTE", but the paper never evaluates whether recursive SQL over `system.access.table_lineage` / `column_lineage` can express Q1/Q4/Q5/Q7. Scoring a SQL-queryable system N for traversal without testing SQL recursion is not defensible. |
| 4.5 | **A** | **No evaluation.** §7 states this outright. Every requirement claim rests on assertion; the reference model is never shown to express the workload it was designed for. |
| 4.6 | **B** | No traceability from queries back to model elements, so the "minimal model" claim ("an edge serving no query is not in the model") is asserted rather than demonstrated. |

## 5. Product-version and citation risk

| # | Sev | Issue |
|---|---|---|
| 5.1 | **A** | **Atlas is cited at version 2.0.0** (`atlas.apache.org/2.0.0/...`), released 2019. Three separate findings rest on it, including the load-bearing "`path` and `loop` clauses are no longer supported". Must be rechecked against current Atlas. |
| 5.2 | **B** | **Web citation keys read as placeholders** — `atlassearch`, `atlassource`, `datahubmodel`, `openmetadatalineage`. With no author field, the rendered bibliography has no organisational attribution. Should carry corporate authors (Apache Software Foundation, LF AI & Data, Databricks, …). |
| 5.3 | **B** | Web entries carry `year = {2026}`, which is the access year, not a publication year — misleading in a numbered bibliography. |
| 5.4 | **C** | `armbrust2020delta` and `deutsch2022gql` use `and others`; verify the rendered "et al." is correct for Springer's style. |
| 5.5 | **C** | `hogan2021knowledge` returned 2024 from Crossref on one run and 2021 from OpenAlex. Settled as 2021 (ACM CSUR 54(4)); record the DOI to make it exact. |

## 6. Framing

| # | Sev | Issue |
|---|---|---|
| 6.1 | **A** | The "catalogs with a graph index" claim conflates three distinct layers — physical storage, logical metadata model, and user-facing query surface. Atlas stores in a graph database and still cannot express Q4; that is an *interface* finding, not an architecture one, and stating it as architecture makes it both weaker and contradicted (see 2.7). |
| 6.2 | **B** | Novelty is stated correctly in §2 ("the workload-driven lens") but the abstract leads with the property-graph model, inviting "metadata as a graph is not new". |
| 6.3 | **B** | Related work does not distinguish this paper from data-observability products or lineage-visualisation tools, the two nearest neighbours a practitioner reviewer will raise. |

---

## Disposition

Phases 2–5 fix §1 and §2 (model completeness, bitemporality, formal query
semantics). Phase 6–7 fix 4.5 by building an executable validation on Kùzu
0.11.3 (embedded property-graph DBMS with Cypher; Python 3.12 venv — no Docker
or Neo4j available in this environment, so Kùzu is the honest substitute and
the paper will name it). Phases 8–11 fix the methodology gaps, including the
representation/query split and the Unity Catalog recursive-SQL question.
Phases 12–13 scope the claims and reframe 2.7/6.1. Phase 22 fixes citations.

Two items change the paper's findings rather than its wording, and must be
allowed to do so: **4.4** (Unity Catalog may be able to express more than
currently scored) and **3.4** (the "every ingredient is stored" claim looks
unsupportable and may have to be withdrawn).
