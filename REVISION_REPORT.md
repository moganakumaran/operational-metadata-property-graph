# Revision report

Revision of *Operational Metadata as a Property Graph: A Reference Model and
Query Workload for Lakehouse Reliability* from a conceptual workload-analysis
paper to one built on a formal model, an executable validation and a
reproducible assessment method.

Before: 9 pages, 36 references, no evaluation, single-axis capability table
with undefined verdicts. After: **14 pages, 45 references, executable
validation of all seven queries, two-layer assessment with a stated rubric and
a derived answerability matrix.** All nine build gates pass (`check.py`).

A subsequent cut pass (see §11) consolidated floats to bring the paper from 15
to 14 pages. It did not reach the CfP's 8–10; that remains open, and
`SUBMISSION_CHECKLIST.md` records the decision.

The defects driving this are enumerated in `REVISION_AUDIT.md`, written before
any edit.

---

## 1. Major structural changes

| | Before | After |
|---|---|---|
| Sections | 7 | 8, with new §5 *Assessment Method* and §6 *Evaluation* |
| Research questions | none stated | RQ1–RQ4 in §1, each answered in §6 |
| Tables | 3, all hand-written | 3 in the paper (1 generated from data) + 3 generated into the artefact |
| Equations | 0 | 8, incl. formal Q4 and the answerability rule |
| Executable artefact | none | `evaluation/`, 7 queries + runner + matrix |
| Threats to validity | one paragraph | §6.5, five named categories |
| Verdict scale | Y/P/N/S, undefined | rubric in §5.2, four levels defined |

New: `evaluation/` (schema, synthetic data, derived relation, q1–q7, runner,
capability matrix, table generator, README), `consistency.py` (32 checks),
`REVISION_AUDIT.md`, this report.

`§7 Limitations and Conclusion` no longer opens with *"This paper contains no
evaluation."*

## 2. Reference-model corrections

| Defect | Fix |
|---|---|
| **`feeds` used in the Q4 listing but defined nowhere** | Defined as a *derived* relation in Eq. (3), materialised from `reads`/`writes` by `derive_feeds.cypher`. Kept derived rather than stored, per the instruction to avoid a redundant Dataset→Dataset primitive; the paper states the derivation rule and marks the edge dashed in Fig. 1. |
| **`lag_minutes` read off an edge, never defined** | Removed. Replaced by `latency_minutes` on the derived hop, with one committed reading: observed delay against schedule of the run that materialised the downstream dataset (Eqs. 4–5). The other three candidate readings are named and rejected explicitly. |
| **`of` edge in Fig. 1, absent from the edge table** | Added as **`evaluates`** (`AssertionResult → QualityAssertion`) to the formal model, the table, the figure and the schema. §3 states why it must exist: Q7 asks whether an assertion *exists*, Q3 whether one *failed*; collapsing the two nodes makes one unanswerable. |
| **`asserts_on` endpoint disagreement** (table said Dataset†, figure drew Field) | Both endpoints now declared explicitly as two rows in Table 2 and two edges in Fig. 1 and the schema. |
| **Transaction time demanded of others, absent from our own model** | §3.1 now defines both intervals on both temporal edges; see §4 below. |
| Node properties used but never declared | Table 1 added: 11 labels with the properties the workload reads, and nothing else. |
| `Incident` had no timestamp although Q6 needs one | `detected_at` declared. |
| No Field→Dataset membership edge | Stated explicitly: membership is via `has_schema`·`declares` and is therefore schema-version-dependent, which is what lets Q2 ask about a field a *past* version declared. |
| `SLA` justified by Q4 but unused by it | Q4 now reads `max_staleness_minutes` and returns a breach flag. |
| Figure/table/schema could drift | `consistency.py` asserts figure edges == table edges == schema edge tables. |

## 3. Q1–Q7 changes

New §4.1 *Workload semantics* gives every query an input, an output and its
required operations. Specific changes:

- **Q1** unchanged in substance; explicitly labelled the control.
- **Q2** now states the `DIRECT`/`INDIRECT` distinction as the discriminating
  case and requires schema versioning to resolve the field.
- **Q3** formalised with window Δ and the disjunction *failed run OR failing
  assertion*; the second disjunct is what forces `AssertionResult` and
  `evaluates` into the model.
- **Q4** substantially rewritten. Formalised as Eq. (7): `L(P)` = sum of hop
  latency along a path, `ImpliedStaleness(d)` = max of `L(P)` over paths.
  Requirement corrected from "path aggregation (max over a path)" — which was
  simply wrong about its own query — to **three** distinct capabilities:
  variable-length traversal, path-local aggregation, and aggregation across
  paths. Listing 1 replaced with the query that actually executes.
- **Q5** ambiguity resolved in four numbered clauses: criticality ordering,
  target-consumer selection with tie-break, nearest-owner rule, and
  multiple-owner tie-break.
- **Q6** now defined over both temporal dimensions, with the two membership
  predicates given as Eqs. (1) and (2).
- **Q7** "unasserted" pinned to one of four possible readings — no assertion
  of any kind, refined to the schema in force — with the other three named and
  the choice of existence-not-outcome stated.

All seven now have executable reference queries in `evaluation/`, and the
artefact's traceability table maps each requirement to the model elements that
satisfy it.

## 4. Bitemporality

Previously the paper argued incident analysis needs valid *and* transaction
time, then specified only `valid_from`/`valid_to` — demanding of the systems a
capability its own model lacked.

Both `has_schema` and `derives_from` now carry four timestamps:
`valid_from`, `valid_to`, `recorded_from`, `recorded_to`, using SQL:2011
application-time / system-time terminology. §3.1 gives the worked divergence:
a schema change **operationally valid at 01:50** but **first recorded at
02:10**, so at the 02:14 incident the valid-time answer is v2 while the
belief-at-02:00 answer is v1. Q6 returns both, and the executed query confirms
the divergence.

## 5. Capability-matrix changes

The single table became two assessed layers plus a derived third, which is the
change that most altered the conclusions.

Originally as three tables; after the cut pass of §11 they are three row
groups of a single table:

- **(a)** metadata representation (9 properties × 6 systems)
- **(b)** query expressiveness (6 operations × 6 systems)
- **(c)** answerability, **computed** from (a) and (b) — the weakest required
  cell across both layers — not judged directly

Selected classification changes (old single-axis → new derived answerability):

| Query | System | Old | New | Why |
|---|---|---|---|---|
| Q1 | Unity Catalog | P | **Y** | recursive CTE over `table_lineage` expresses the closure |
| Q5 | Unity Catalog | P | **Y** | recursion depth + `TABLE_OWNER` |
| Q1 | Atlas | P | **N** | current DSL grammar has no traversal production at all |
| Q2 | Atlas | P | **N** | same, plus column lineage is bridge-specific |
| Q3 | Atlas | P | **N** | no run-instance modelling, no traversal |
| Q6 | Atlas | N | **P** | `validityPeriods` exists, but on classifications only |
| Q2 | Unity Catalog | P | **N** | no schema-version history |
| Q3 | Unity Catalog | P | **N** | no assertion model; run state unjoinable to lineage |
| Q7 | Unity Catalog | P | **N** | no assertion model in UC itself |
| Q4 | all six | N | **N** | unchanged verdict, but the cause is now located: a *representation* gap (no per-hop latency), not a query gap |

Summary finding replaced. Old: *"path aggregation is supported by nobody"* as
an architectural claim. New: **the binding constraint differs by system** —
Atlas is limited by expressiveness, Unity Catalog by representation — and
**none of the six answers more than three of the seven**, a figure
`consistency.py` verifies against the computed matrix.

## 6. Unity Catalog reassessment

This was the largest single change, and it went in Unity Catalog's favour on
one axis and against it on the other. Following the instruction to separate
*does it store the metadata* from *can Databricks SQL express the query*:

**Query expressiveness — upgraded to the strongest in the set.** Databricks SQL
supports `WITH RECURSIVE` from **Databricks Runtime 17.0**, with a default
recursion limit of 100 levels and a one-million-row bound. A recursive CTE over
`system.access.table_lineage` therefore expresses all six required operations:
closure and reverse traversal by join direction, a path-local fold by carrying
an accumulator down each branch, path selection by minimum recursion depth,
temporal predicates as ordinary SQL, and negation by `NOT EXISTS` over the
recursive result. The previous draft scored Unity Catalog down for traversal
without testing recursive SQL, which was not defensible.

**Metadata representation — downgraded where the data is absent.**
- `system.access.table_lineage` / `column_lineage` do carry source/target
  table and column names, `event_time`, `entity_run_id`.
- No schema-version history: `information_schema.tables` has `LAST_ALTERED`
  but no history view.
- No assertion model in Unity Catalog itself.
- Run state lives in `system.lakeflow.job_run_timeline`
  (`period_start_time`, `period_end_time`, `result_state`) — a different
  schema, with **no documented join** to lineage records.
- No validity interval on lineage rows; one-year rolling retention on the
  system tables.
- Documented limitation retained and quoted: *"Lineage is not preserved for
  renamed catalogs, schemas, tables, views, or columns."*

**Net:** Y on Q1 and Q5, N on the rest — and the reason is now recorded as
representation rather than as an inability to traverse. For four of the five
unanswerable queries, the traversal machinery is already present; only the
data is missing.

Sources: `ucrecursive`, `ucsystemtables`, `ucjobs`, `ucinfoschema`,
`unitycatalog`.

## 7. Claims softened or corrected

| Before | After |
|---|---|
| "no system can aggregate along a path" | "Per-hop latency … was represented by none of the six", and the Q4 row is attributed to a representation gap |
| "Column-level lineage is settled" / "a solved problem" | "Field-level lineage is comparatively mature … four of the six" |
| "bitemporal validity is implemented in exactly one system" | "Among the six, Egeria was the only system that satisfied our bitemporal criterion" |
| "These systems are catalogs with a graph index, not graph databases" | Removed as an architectural claim. Reframed as interface expressiveness: "Atlas stores its metadata in a graph database and still cannot express Q1, which is why the useful distinction is the interface rather than the storage engine." This also resolves a **direct self-contradiction** — §2 of the old draft stated Atlas *is* built on a graph database. |
| "Every ingredient for Q4 is stored in at least one system" | **Withdrawn.** Separating the layers showed it false: no system represents per-hop latency. §6.4 records the correction rather than dropping the claim silently. |
| "the field converged on recording lineage and stopped short of querying it" | Retained but scoped, and paired with the counter-example (Unity Catalog, which can query and lacks data) |
| Implicit suggestion that catalogs need replacing | Explicit: "We are *not* arguing that metadata platforms should be replaced by native graph databases", with Atlas as the evidence against it |
| Q4 row "would survive any reasonable variation" | Retained but marked "an expectation and not a result" |

Absolute quantifiers now scope to *the six systems examined*, *under the
interfaces and versions examined*, throughout §6 and §7.

## 8. References added / removed / corrected

**Before:** 36 entries, 13 web entries with no author, keys rendering as bare
titles. **After:** 45 entries, all cited, all verified, `verify_refs.py` exits 0.

*Added (9):* `atlasgrammar`, `atlashook`, `atlasaudit`, `datahubgraphql`,
`openmetadatasearch`, `ucsystemtables`, `ucrecursive`, `ucjobs`,
`ucinfoschema`.

*Corrected:*
- All 22 web entries given **organisational authors** — Apache Software
  Foundation, DataHub Project, OpenMetadata Project, LF AI & Data Foundation,
  Databricks, OpenLineage Project — replacing placeholder-style keys with no
  attribution.
- `atlasgrammar` and `atlassource` carry *"Inspected"* dates rather than
  *"Accessed"*, since they are source readings; `verify_refs.py` now accepts
  both.
- `ucrecursive` records the version constraint (DBR 17.0+) in its note, because
  the finding is version-dependent.
- Atlas assessment moved from **2.0.0 documentation (2019)** to the
  `master` branch ANTLR grammar. Atlas is at 2.5.0 with 2.6.0 tagged; the DSL
  was rewritten after 1.0, so the old citation predated the language it was
  being used to describe. The 2.0.0 URLs remain only where cited for the type
  system and DSL prose, which have not changed materially.

*Earlier corrections retained:* `klettke2016migration` (previously recorded
with a fabricated title, venue and year), `rost2021gradoop` (year and one
author name), and DOIs added for `armbrust2020delta`, `francis2018cypher`,
`halevy2016goods` so they verify exactly rather than by fuzzy title.

No entry was invented. Verification runs OpenAlex → Crossref, DOI-first; DBLP
is unreachable from this environment and is deliberately not used, because a
blocked host returning nothing is indistinguishable from a nonexistent
reference.

## 9. Remaining limitations

Stated in §6.5 and consolidated in §7. The ones a reviewer will press hardest:

1. **No performance evaluation of any kind.** 44 nodes; expressiveness only.
2. **The workload is seven queries from practitioner experience**, not from a
   measured incident corpus. A different seven yields a different table.
3. **Minimality is exhibited, not proved.** Table 3 shows a query for every
   model element; it does not show no smaller model exists.
4. **Expected results were written by the same author as the queries.**
5. **Six systems, one date.** Five are actively developed; the Unity Catalog
   finding depends on a capability that did not exist before DBR 17.0.
6. **Documented capability may understate internal capability**, particularly
   for the proprietary system.
7. **Several formal choices are defensible, not unique** — latency, Q7's
   "unasserted", Q5's tie-breaks. Each is flagged at the point of choice.
8. Atlas and OpenMetadata cells not re-checked against source as recently as
   the ones that were, so the same version-drift risk applies to them.

## 10. Files changed

**Modified:** `paper.tex` (substantially rewritten; 616 → 900+ lines),
`references.bib` (36 → 45 entries, all web entries rewritten),
`check.py` (5 → 9 gates, page range 8–10 → 12–16),
`verify_refs.py` (accepts inspection dates), `SCOPE.md`.

**Added:** `REVISION_AUDIT.md`, `REVISION_REPORT.md`, `consistency.py`,
`evaluation/` (`schema.cypher`, `synthetic_data.cypher`,
`derive_feeds.cypher`, `q1`–`q7.cypher`, `run_validation.py`,
`capability_matrix.json`, `make_tables.py`, `results.json`, `README.md`),
`.venv/` (Python 3.12 + Kùzu 0.11.3).

**Unchanged:** `sn-jnl.cls`, `sn-basic.bst`, `bst/`,
`TEMPLATE_PROVENANCE.md`, `CFP_datenbank_spektrum.pdf`.

---

## Acceptance checklist

| Item | State |
|---|---|
| `feeds` inconsistency resolved | ✅ derived relation, Eq. (3) |
| `lag_minutes` defined or removed | ✅ removed; `latency_minutes` defined, Eqs. (4)–(5) |
| AssertionResult→QualityAssertion defined | ✅ `evaluates`, in model + table + figure + schema |
| valid time represented | ✅ `valid_from`/`valid_to` |
| transaction/system time represented | ✅ `recorded_from`/`recorded_to` |
| Q1–Q7 precisely specified | ✅ §4.1 |
| Q1–Q7 have executable reference queries | ✅ `evaluation/q1–q7.cypher` |
| synthetic graph exercises all seven | ✅ 7/7 execute and match |
| evaluation section exists | ✅ §6 |
| Y/P/N/S methodology defined | ✅ §5.2 rubric |
| representation separated from expressiveness | ✅ Table 2 groups (a) and (b); Eq. (7) |
| all six systems revalidated | ✅ 21 Sep 2026, Atlas against `master` |
| Unity Catalog independently reassessed | ✅ §6 above |
| recursive SQL capability considered | ✅ `WITH RECURSIVE`, DBR 17.0+ |
| capability table regenerated from current evidence | ✅ generated from `capability_matrix.json` |
| absolute claims scoped | ✅ §7 above |
| abstract matches actual results | ✅ asserted by `consistency.py` |
| conclusion matches actual results | ✅ "no more than three of seven" verified against the computed matrix |
| Figure 1 and Table 2 consistent | ✅ asserted by `consistency.py` |
| references checked | ✅ 23 verified + 22 web, exit 0 |
| Springer author block corrected | ✅ `\author*` marks the corresponding author |
| limitations updated | ✅ §6.5 + §7 |
| `REVISION_REPORT.md` created | ✅ this file |

## Reproducing the checks

```bash
python3 check.py          # all nine gates; exit 0 = submittable
python3 consistency.py    # 32 manuscript-vs-artefact checks
.venv/bin/python evaluation/run_validation.py
python3 evaluation/make_tables.py --check
python3 verify_refs.py
```

---

## 11. Cut pass: floats consolidated

Run after the revision, to move toward the CfP's 8–10 pages. Outcome: **15 → 14
pages**, which is well short of the target and worth recording as a
measurement rather than a success.

| Change | Estimated | Actual |
|---|---|---|
| Merge `tab:repr` + `tab:expr` into one matrix with row groups | −1.0pp | |
| Fold `tab:answer` in as a third group of that matrix | −0.6pp | |
| Move traceability, systems/evidence and validation tables to `evaluation/SUPPLEMENTARY.md` | −1.5pp | |
| `tab:edges` full-width → single column with abbreviated node labels | −0.5pp | |
| `tab:nodes` → inline prose | −0.25pp | |
| Trim related work, capability assessment, conclusion, discussion, intro (~500 words) | −0.7pp | |
| **Total** | **−4.5pp** | **−1.0pp** |

The estimate was wrong because LaTeX was already placing the full-width floats
onto pages shared with body text; removing a float mostly removed whitespace,
not a page. Ten floats became five, and the page count moved by one.

Two side effects worth noting:

- The merged three-group matrix is **better than the two tables it replaced**.
  The derivation now reads down one page — facts, then operations, then what
  they compose to — and Unity Catalog's fully-supported expressiveness column
  sitting beside its sparse representation column makes the paper's main
  finding legible at a glance.
- Relocating three tables to the artefact required repointing every reference
  to them and weaving five orphaned citation keys into prose; the
  cited-vs-bibliography check caught that and now reports clean.

Current composition: ~11.4 pages of body, ~2.6 of references. Reaching 10 needs
roughly three more pages from content, which means the evaluation.

---

## 12. Cut pass 2: measured, not estimated

After the first cut pass moved 15 → 14 on a wrong estimate, every candidate was
compiled and measured before choosing. The measurement is the finding:

| Cut, applied alone | Δ pages |
|---|---|
| **Drop the bibliography** | **−3** |
| **Drop all of §6 Evaluation** | **−3** |
| Drop §2, or §5, or 1,000 words of prose | −2 each |
| Drop the capability table, Fig. 1, edge table, or the Q4 listing | −1 each |

**The reference list cost as much as the entire evaluation.** That lever had
been dismissed on an estimate in the previous pass, which was the wrong call.

Applied: the 22 documentation entries became six per-organisation entries
(45 → 29), with **every URL preserved** in the entries' notes and, more
importantly, the specific URL for each of the 90 capability cells appended to
that cell's reason in `capability_matrix.json` — so consolidating the
bibliography did not cost per-cell traceability. Prose went 5,295 → 4,575
words, and Listing 1 was removed with its consistency check **retargeted** to
pin `q4.cypher` to Eq. (7) rather than deleted.

Result **14 → 12 pages**, all gates green except the page gate, which now
encodes the venue's 8–10 rule and fails visibly. The remaining two pages would
have to come from the Threats section, the rubric, or the formal query
semantics.

Two false positives fixed on the way: the verifier classified web entries by
`url`/`howpublished` only, so the consolidated entries — which carry their URLs
in `note` — were looked up as if they were papers; and a `%` line-continuation
inside a `\cite{}` made the cited-vs-bibliography check report a phantom key.

---

## 13. Review pass: flow, empirical validity, novelty

A read-through checking that the argument flows, the empirical claims hold,
and novelty is claimed defensibly. The validation was re-derived independently
rather than re-read.

**Held up.** Section order is defensible, RQ1–RQ4 are each picked up later, no
dangling references, Q1–Q7 in order in the source. The Q4 result was
**re-derived in plain Python from `synthetic_data.cypher`, without Kùzu and
without the `EXPECTED` table**, and agreed: 36 minutes against a 30-minute
SLA, 44 nodes, 4 derived edges. A 13-point audit of every figure in the paper
against `results.json` and `capability_matrix.json` passed. So the headline
result is neither an engine artefact nor self-confirming.

**Five fixes applied.**

| | Issue | Fix |
|---|---|---|
| A | **Factual error.** Paper said "three distinct paths" into `daily_revenue` and "the other two total 16 each". There are **four**: 36, 16, 16, 4. | Corrected in §6.1, §6.2 and `evaluation/README.md`. The 4-minute single-hop path is now used to make the point: a dataset one hop out can look timely while the graph behind it is half an hour late. |
| B | **RQ1 contradicted §6.4.** RQ1 asked what is "minimally necessary"; §6.2 claimed to answer it; §6.4 conceded minimality is not established. | RQ1 reframed to sufficiency *plus* per-element justification. §6.2 now says necessity is **exhibited, not proved**. |
| C | **Novelty had no foil.** Nothing said how metadata systems are compared today, so "novel" had nothing to contrast with. | §2 now states that comparisons are feature inventories every candidate passes, and that we found no systematic comparison of these six against a stated workload — phrased as *an absence we did not fill by searching*, not as proof none exists. |
| D | **OpenMetadata omitted; strongest result buried.** §6.3 named three systems and skipped the one with the most partials. | Now: "none answered more than three, **and three answered none**", with OpenMetadata's four partials named and attributed to the query layer (verified: all four have representation Y, expressiveness P). Explicitly declines to rank, since Egeria's 3Y+2P is at least as strong as DataHub's 3Y+0P. |
| E | Eq. (6) was orphaned after Listing 1 was cut. | §6.2 now ties the 36-minute result back to it. |

**The path count is now data-derived.** `run_validation.py` writes the full
`q4_paths` enumeration to `results.json`, and `consistency.py` pins the paper's
prose to it — the count word, the headline maximum and the remaining totals.
Negative-tested: reintroducing the original wording makes two checks fail.
`consistency.py` is now 36 checks, all passing.
