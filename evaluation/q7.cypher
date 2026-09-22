// Q7 Coverage gaps.
// Input : criticality threshold k = 1 (most critical tier)
// Output: critical consumers with at least one unasserted dataset upstream
//
// "Unasserted" is defined precisely as: NO QualityAssertion targets the
// dataset, AND no QualityAssertion targets any Field declared by a schema
// version of that dataset that is valid now. We use existence of an assertion,
// not its outcome -- a failing assertion is still coverage. The three other
// readings (no currently-valid assertion / no passing assertion / none
// covering the specific field) are deliberately not used, and the paper says
// which one it means.
//
// Capability: negation applied UNDER a transitive closure, not over a flat
// result set.
MATCH (c:Consumer)-[:consumes]->(d:Dataset)
WHERE c.criticality <= 1
MATCH (up:Dataset)-[:feeds*0..10]->(d)
WHERE NOT EXISTS { MATCH (:QualityAssertion)-[:asserts_on]->(up) }
  AND NOT EXISTS { MATCH (:QualityAssertion)-[:asserts_on]->(f:Field)
                   WHERE EXISTS { MATCH (up)-[e:has_schema]->(sv:SchemaVersion)
                                          -[:declares]->(f)
                                  WHERE e.valid_to > timestamp('2026-09-21 02:14:00') } }
RETURN DISTINCT c.name AS critical_consumer, c.criticality AS criticality,
       up.name AS unasserted_upstream
ORDER BY critical_consumer ASC, unasserted_upstream ASC;
