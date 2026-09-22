// Q5 Escalation routing.
// In : incident i ('inc_0214')
// Out: the Principal to page, and the node it owns on the dependency path
//
// Ownership may attach to a Dataset OR a Pipeline, so Q5 must consider the
// explicit alternating dependency path
//
//     D0  <-reads- P1 -writes->  D1  <-reads- P2 -writes->  D2  ...
//
// and not only the derived Dataset->Dataset `feeds` relation, which collapses
// the pipeline out of the path and would make a pipeline owner unreachable.
// This is the one query needing the intermediate Pipeline node; Q1, Q3, Q4
// and Q7 are content with `feeds`.
//
// The alternating path is RECOVERED rather than traversed directly: no engine
// in common use supports variable-length traversal over a composite
// (D <-reads- P -writes-> D) pattern. We take the shortest `feeds` path and
// expand each hop back to the pipeline that realised it, which
// `feeds.via_pipeline` records. This is lossless: via_pipeline is exactly the
// p of Eq. (3).
//
// Position interleaves the two node kinds -- dataset k at position 2k, the
// pipeline realising hop k at position 2k+1 -- so "nearest" is the minimum
// position from the incident. Ranking, fixed for determinism:
//   1. criticality is a total order on integers, lower is more critical
//   2. target consumer c* = reachable consumer of minimum criticality, ties
//      broken by name ascending
//   3. among nodes of a shortest dependency path from d0 to c*'s dataset,
//      take the one at minimum position carrying an `owns` edge
//   4. if several principals own it, the lexicographically first
MATCH (i:Incident)-[:affects]->(d0:Dataset)
WHERE i.incident_id = 'inc_0214'
MATCH (d0)-[:feeds*0..10]->(dc:Dataset)<-[:consumes]-(cx:Consumer)
WITH d0, dc, cx ORDER BY cx.criticality ASC, cx.name ASC LIMIT 1
MATCH sp = (d0)-[:feeds* SHORTEST 1..10]->(dc)
WITH cx, list_transform(nodes(sp), n -> n.name) AS dnames,
        list_transform(rels(sp),  h -> h.via_pipeline) AS pnames
UNWIND range(0, size(dnames) + size(pnames) - 1) AS position
WITH cx, dnames, pnames, position,
     CASE WHEN position % 2 = 0 THEN dnames[position / 2 + 1]
          ELSE pnames[(position - 1) / 2 + 1] END AS node_name,
     CASE WHEN position % 2 = 0 THEN 'Dataset' ELSE 'Pipeline' END AS node_kind
// untyped endpoint: this is where BOTH owns signatures are exercised
MATCH (pr:Principal)-[:owns]->(o)
WHERE o.name = node_name
WITH cx, position, node_name, node_kind, pr.name AS owner
ORDER BY position ASC, owner ASC LIMIT 1
RETURN cx.name AS most_critical_consumer, cx.criticality AS criticality,
       node_name AS escalation_point, node_kind AS escalation_point_kind,
       position AS position_from_incident, owner AS page_this_principal;
