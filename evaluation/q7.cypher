// Q7 Coverage gaps.
// In : criticality threshold k = 1, evaluation time t = 2026-09-21 02:14:00
// Out: critical consumers with at least one unasserted dataset upstream
//
// Q7 needs an explicit evaluation time because `has_schema` is bitemporal:
// which fields a dataset declares is a function of when you ask. Earlier
// versions took only k and tested `valid_to >` alone, which silently assumed
// "now" and ignored valid_from. The schema in force at t is the one with
//
//     valid_from <= t < valid_to
//
// and coverage is judged against the fields THAT version declares.
//
// "Unasserted at t" is defined as: no QualityAssertion asserts_on the dataset,
// AND none asserts_on any Field declared by the dataset's schema version valid
// at t. Four readings were available -- no assertion of any kind, none
// currently valid, none passing, or none covering the relevant field. We take
// the first, refined to the schema in force. Existence, not outcome: a
// FAILING assertion still counts as coverage, because Q7 asks what is
// unwatched, not what is broken. Q3 asks the outcome question.
//
// Capability: negation applied UNDER a transitive closure, with a temporal
// predicate selecting the schema version.
MATCH (c:Consumer)-[:consumes]->(d:Dataset)
WHERE c.criticality <= 1
MATCH (up:Dataset)-[:feeds*0..10]->(d)
WHERE NOT EXISTS { MATCH (:QualityAssertion)-[:asserts_on]->(up) }
  AND NOT EXISTS {
        MATCH (up)-[e:has_schema]->(:SchemaVersion)-[:declares]->(f:Field)
        WHERE e.valid_from <= timestamp('2026-09-21 02:14:00')
          AND e.valid_to   >  timestamp('2026-09-21 02:14:00')
          AND EXISTS { MATCH (:QualityAssertion)-[:asserts_on]->(f) } }
RETURN DISTINCT c.name AS critical_consumer, c.criticality AS criticality,
       up.name AS unasserted_upstream
ORDER BY critical_consumer ASC, unasserted_upstream ASC;
