"""Load the reference graph and execute Q1-Q7, checking each against its
stated expected result.

This is an EXPRESSIVENESS validation, not a benchmark. It answers one
question: can the reference model of Sect. 3, implemented on a real property
graph engine, express all seven workload queries of Sect. 4 and return the
operationally correct answer? No timings are recorded and none should be
inferred -- the graph is deliberately tiny, chosen so that every expected
answer can be derived by hand and checked.

Engine: Kuzu, an embedded property-graph DBMS with a Cypher dialect. Chosen
because it runs in-process with no server, which keeps the artefact
reproducible from a single `pip install`. Two dialect notes matter for anyone
porting the queries to Neo4j:
  - Kuzu has no reduce(); the path-local fold in Q4 is written
    list_sum(list_transform(rels(p), r -> r.latency_minutes)).
  - Kuzu requires typed node and relationship tables, so schema.cypher is a
    machine-checked statement of the model: a query referencing an edge the
    model does not declare fails at parse time instead of silently returning
    nothing. That property is why an undefined `feeds` edge survived in the
    first version of the paper and cannot survive here.

Usage:  python run_validation.py [--db PATH] [--json OUT]
Exit code 1 if any query fails to execute or returns an unexpected result.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Expected results, written down before running. Each is derivable by hand
# from synthetic_data.cypher; the point of stating them here is that the
# script fails if the engine disagrees, rather than printing whatever it got.
EXPECTED = {
    "Q1": {
        "capability": "transitive closure over typed edges",
        "rows": [["pricing_service", 1, "daily_revenue"],
                 ["finance_dashboard", 3, "daily_revenue"]],
        "reading": "both consumers of daily_revenue are reachable downstream "
                   "of orders_clean; pricing_service ranks first at "
                   "criticality 1",
    },
    "Q2": {
        "capability": "column-level lineage closure with schema versioning",
        "rows": [["orders_clean.amount_usd", 1],
                 ["daily_revenue.revenue_usd", 2]],
        "reading": "dropping orders_raw.currency breaks amount_usd at one hop "
                   "through an INDIRECT/JOIN dependency it never projects, and "
                   "revenue_usd at two hops; a projection-only or "
                   "dataset-level analysis reports this change as safe",
    },
    "Q3": {
        "capability": "reverse traversal with a temporal predicate",
        "rows": [["fx_rates", "ingest_fx", "r_ingest_fx_01", "FAILED", None],
                 ["fx_rates_smoothed", "smooth_fx", "r_smooth_fx_01",
                  "SUCCESS", "a_smoothed_freshness"]],
        "reading": "two candidates in the 60-minute window before 02:14: a "
                   "failed ingest run with no assertion attached, and a run "
                   "that SUCCEEDED but produced a failing assertion, named "
                   "here by traversing `evaluates` to the QualityAssertion. "
                   "The second row is why AssertionResult and QualityAssertion "
                   "are separate nodes: 'some assertion failed' is not "
                   "actionable, 'a_smoothed_freshness failed' is",
    },
    "Q4": {
        "capability": "variable-length traversal + path-local aggregation + "
                      "aggregation across paths",
        "rows": [["daily_revenue", 36, 30, True]],
        "reading": "the slowest of three paths runs fx_rates -> "
                   "fx_rates_smoothed -> orders_clean -> daily_revenue and "
                   "accumulates 20+12+4 = 36 minutes, breaching the 30-minute "
                   "SLA. The two shorter paths both total 16, so reachability "
                   "or a per-dataset freshness value would not surface the "
                   "breach",
    },
    "Q5": {
        "capability": "path selection over the alternating dataset-pipeline "
                      "path, with in-graph ownership",
        "rows": [["pricing_service", 1, "agg_revenue", "Pipeline", 1,
                  "revenue_oncall"]],
        "reading": "the most critical affected consumer is pricing_service. "
                   "The incident dataset orders_clean (position 0) is "
                   "unowned; the nearest owned node is the PIPELINE "
                   "agg_revenue at position 1, owned by the revenue_oncall "
                   "rotation -- nearer than daily_revenue's owner at position "
                   "2. This is the case that makes Principal->Pipeline "
                   "load-bearing: traversing only the derived feeds relation "
                   "would collapse the pipeline out of the path and return "
                   "the wrong principal",
    },
    "Q6": {
        "capability": "two independent temporal dimensions on one edge",
        "rows": [["orders_raw@v1", False, True],
                 ["orders_raw@v2", True, False]],
        "reading": "v2 was VALID at the 02:14 incident but was NOT yet "
                   "believed by the catalog at 02:00, while v1 was believed "
                   "at 02:00 but no longer valid. The two dimensions "
                   "disagree, which is the case a single version history "
                   "cannot represent",
    },
    "Q7": {
        "capability": "negation applied under a transitive closure",
        "rows": [["pricing_service", 1, "fx_rates"]],
        "reading": "pricing_service is tier 1 and depends, three hops "
                   "upstream, on fx_rates, which at the 02:14 evaluation time "
                   "carries no assertion on the dataset and none on any field "
                   "declared by the schema version valid at that instant",
    },
}


def statements(path: str) -> list[str]:
    """Split a .cypher file into statements, dropping // comments.

    Semicolon-splitting only: no statement in these files contains a
    semicolon inside a string literal, and checking that is cheaper than
    carrying a parser.
    """
    src = open(os.path.join(HERE, path), encoding="utf-8").read()
    src = re.sub(r"^\s*//.*$", "", src, flags=re.M)
    return [s.strip() for s in src.split(";") if s.strip()]


def rows_of(result) -> list[list]:
    out = []
    while result.has_next():
        out.append(result.get_next())
    return out


def norm(rows) -> list[list]:
    """Make engine output comparable to the hand-written expectations."""
    def one(v):
        if v is None:
            return None
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return int(v)
        return str(v)
    return [[one(v) for v in r] for r in rows]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.join(HERE, ".kuzu_db"))
    ap.add_argument("--json", default=os.path.join(HERE, "results.json"))
    args = ap.parse_args()

    try:
        import kuzu
    except ModuleNotFoundError:
        print("kuzu not installed. See README.md; needs Python <= 3.12.")
        return 2

    # Kuzu may create the database as a file or a directory, and writes a
    # sibling .wal either way. rmtree alone left the .wal behind, so the next
    # run re-applied schema.cypher onto a populated catalog and failed with
    # "Dataset already exists" -- which looked like a query defect and was not.
    for path in (args.db, args.db + ".wal", args.db + ".lock",
                 args.db + ".shadow", args.db + ".tmp"):
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        elif os.path.exists(path):
            os.remove(path)
    db = kuzu.Database(args.db)
    con = kuzu.Connection(db)
    print(f"kuzu {kuzu.__version__}\n")

    for f in ("schema.cypher", "synthetic_data.cypher", "derive_feeds.cypher"):
        n = 0
        for st in statements(f):
            con.execute(st)
            n += 1
        print(f"  loaded {f:24s} ({n} statements)")

    counts = {}
    for label in ("Dataset", "SchemaVersion", "Field", "Pipeline", "Run",
                  "QualityAssertion", "AssertionResult", "Consumer",
                  "Principal", "SLA", "Incident"):
        counts[label] = rows_of(con.execute(
            f"MATCH (n:{label}) RETURN count(n)"))[0][0]
    edges = {}
    for rel in ("reads", "writes", "declares", "instance_of", "produced",
                "evaluates", "asserts_on", "consumes", "owns", "governed_by",
                "affects", "has_schema", "derives_from", "feeds"):
        edges[rel] = rows_of(con.execute(
            f"MATCH ()-[e:{rel}]->() RETURN count(e)"))[0][0]
    print(f"\n  nodes: {sum(counts.values())} across {len(counts)} labels")
    print(f"  edges: {sum(edges.values())} across {len(edges)} types "
          f"({edges['feeds']} derived)\n")

    out, failures = {}, 0
    for q in sorted(EXPECTED):
        spec = EXPECTED[q]
        sts = statements(f"{q.lower()}.cypher")
        try:
            got = norm(rows_of(con.execute(sts[-1])))
        except Exception as e:
            print(f"  [FAIL] {q}  did not execute: {str(e)[:150]}")
            failures += 1
            out[q] = {"executable": False, "error": str(e)[:400],
                      **{k: spec[k] for k in ("capability", "reading")}}
            continue
        want = norm(spec["rows"])
        ok = got == want
        failures += 0 if ok else 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {q}  {len(got)} row(s)"
              f"   {spec['capability']}")
        if not ok:
            print(f"         expected {want}")
            print(f"         got      {got}")
        out[q] = {"executable": True, "matched_expected": ok,
                  "rows": got, "expected": want,
                  "capability": spec["capability"],
                  "reading": spec["reading"]}

    # Enumerate the Q4 paths explicitly. The paper describes this set in
    # prose, and an earlier draft said "three paths" when there are four --
    # recording it here lets consistency.py pin the prose to the data.
    q4_paths = []
    for row in rows_of(con.execute("""
            MATCH p = (src:Dataset)-[:feeds*1..10]->(d:Dataset)
            WHERE d.name = 'daily_revenue'
            RETURN src.name,
                   list_sum(list_transform(rels(p),
                            r -> r.latency_minutes)) AS total,
                   length(p) AS hops
            ORDER BY total DESC, src.name""")):
        q4_paths.append({"from": str(row[0]), "total_minutes": int(row[1]),
                         "hops": int(row[2])})
    print(f"\n  Q4 paths into daily_revenue: {len(q4_paths)}")
    for q in q4_paths:
        print(f"    {q['total_minutes']:>3} min  from {q['from']} "
              f"({q['hops']} hops)")

    payload = {"engine": f"kuzu {kuzu.__version__}",
               "q4_paths": q4_paths,
               "node_counts": counts, "edge_counts": edges,
               "queries": out,
               "all_executable": all(v.get("executable") for v in out.values()),
               "all_matched": failures == 0}
    json.dump(payload, open(args.json, "w"), indent=1)
    print(f"\n  wrote {os.path.relpath(args.json, HERE)}")
    print(f"  {len(EXPECTED) - failures}/{len(EXPECTED)} queries executable "
          f"and matching expected results")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
