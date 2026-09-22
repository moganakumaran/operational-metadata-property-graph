// Q4 Freshness propagation.
// Input : target dataset d ('daily_revenue')
// Output: implied staleness, and whether it breaches the governing SLA
// Capability: (i) variable-length traversal, (ii) path-LOCAL aggregation of
//   per-hop latency, (iii) aggregation ACROSS candidate paths. Three distinct
//   requirements -- not "max over a path".
//
//   L(P)                = sum of latency_minutes over the hops of path P
//   ImpliedStaleness(d) = max over all paths P ending at d of L(P)
//
// Kuzu has no reduce(); list_sum(list_transform(rels(p), ...)) is the
// equivalent path-local fold.
MATCH p = (src:Dataset)-[:feeds*1..10]->(d:Dataset)
WHERE d.name = 'daily_revenue'
WITH d, src,
     list_sum(list_transform(rels(p), r -> r.latency_minutes)) AS path_latency
WITH d, max(path_latency) AS implied_staleness
MATCH (d)-[:governed_by]->(s:SLA)
RETURN d.name AS dataset, implied_staleness,
       s.max_staleness_minutes AS sla_limit,
       implied_staleness > s.max_staleness_minutes AS sla_breached;
