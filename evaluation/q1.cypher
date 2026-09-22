// Q1 Downstream impact.
// Input : dataset d0 ('orders_clean')
// Output: consumers reachable downstream, with criticality, ranked
// Capability: transitive closure over typed edges (variable-length traversal)
MATCH (d0:Dataset)-[:feeds*0..10]->(d:Dataset)
WHERE d0.name = 'orders_clean'
MATCH (c:Consumer)-[:consumes]->(d)
RETURN DISTINCT c.name AS consumer, c.criticality AS criticality, d.name AS via
ORDER BY criticality ASC, consumer ASC;
