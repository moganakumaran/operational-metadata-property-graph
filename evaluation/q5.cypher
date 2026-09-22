// Q5 Escalation routing.
// Input : incident i ('inc_0214')
// Output: the Principal to page
// Definition, made explicit because "nearest owner" is ambiguous:
//   1. criticality ordering: lower integer = more critical; 1 is highest
//   2. target consumer c* = the reachable consumer with minimum criticality;
//      ties broken by name, ascending, for determinism
//   3. among datasets on a shortest feeds-path from the incident dataset to
//      c*'s dataset, take the one at minimum hop distance from the incident
//      that has an owns edge
//   4. if several Principals own that dataset, the lexicographically first is
//      returned, so the result is deterministic
// Capability: shortest-path selection + ownership resolved in-graph
MATCH (i:Incident)-[:affects]->(d0:Dataset)
WHERE i.incident_id = 'inc_0214'
MATCH (d0)-[:feeds*0..10]->(dc:Dataset)<-[:consumes]-(cx:Consumer)
WITH d0, dc, cx ORDER BY cx.criticality ASC, cx.name ASC LIMIT 1
MATCH sp = (d0)-[:feeds* SHORTEST 1..10]->(dc)
WITH dc, cx, nodes(sp) AS ns
UNWIND ns AS hop_node
WITH dc, cx, ns, hop_node.name AS hop_name,
     list_position(ns, hop_node) - 1 AS hop
MATCH (pr:Principal)-[:owns]->(od:Dataset)
WHERE od.name = hop_name
WITH cx, hop_name, hop, pr.name AS owner ORDER BY hop ASC, owner ASC LIMIT 1
RETURN cx.name AS most_critical_consumer, cx.criticality AS criticality,
       hop_name AS escalation_point, hop AS hops_from_incident,
       owner AS page_this_principal;
