// Q3 Root-cause candidates.
// Input : incident i ('inc_0214'), window delta = 60 minutes
// Output: upstream datasets whose producing run FAILED, or whose assertion
//         returned FAIL, inside [detected_at - delta, detected_at]
// Capability: reverse traversal + temporal predicate on run/result state
//
// The `evaluates` edge is what turns "some assertion failed" into "THIS
// assertion failed", which is what an operator needs to act. Without it the
// AssertionResult/QualityAssertion split would be unexercised by any query.
MATCH (i:Incident)-[:affects]->(d0:Dataset)
WHERE i.incident_id = 'inc_0214'
WITH i, d0, i.detected_at AS t_end,
     i.detected_at - interval('60 minutes') AS t_start
MATCH (up:Dataset)-[:feeds*0..10]->(d0)
MATCH (p:Pipeline)-[:writes]->(up)
MATCH (r:Run)-[:instance_of]->(p)
WHERE r.ended_at >= t_start AND r.ended_at <= t_end
  AND (r.status = 'FAILED'
       OR EXISTS { MATCH (r)-[:produced]->(ar:AssertionResult)
                   WHERE ar.outcome = 'FAIL' })
OPTIONAL MATCH (r)-[:produced]->(fr:AssertionResult)-[:evaluates]->(qa:QualityAssertion)
WHERE fr.outcome = 'FAIL'
RETURN DISTINCT up.name AS upstream_dataset, p.name AS pipeline,
       r.run_id AS run, r.status AS run_status,
       qa.assertion_id AS failing_assertion
ORDER BY upstream_dataset ASC;
