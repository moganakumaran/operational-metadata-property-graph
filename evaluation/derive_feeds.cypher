// Materialise the derived dependency relation from the model primitives.
//
//   feeds(d1, d2)  iff  exists p in Pipeline : (p)-[:reads]->(d1)
//                                        and  (p)-[:writes]->(d2)
//
// latency_minutes(d1 -> d2 via p) := delay_minutes of the most recent
// SUCCESSful Run of p. This is the paper's single committed reading of hop
// latency: observed delay, against schedule, of the run that materialised the
// downstream dataset.
//
// This is a view, not a modelled fact. Keeping it derived is deliberate: a
// stored Dataset->Dataset edge would duplicate reads/writes and could drift
// from it, and part of what makes Q4 hard for real systems is precisely that
// this relation has to be computed before it can be traversed.
MATCH (p:Pipeline)-[:reads]->(d1:Dataset),
      (p)-[:writes]->(d2:Dataset),
      (r:Run)-[:instance_of]->(p)
WHERE r.status = 'SUCCESS'
WITH d1, d2, p, max(r.scheduled_for) AS latest
MATCH (r2:Run)-[:instance_of]->(p)
WHERE r2.scheduled_for = latest AND r2.status = 'SUCCESS'
CREATE (d1)-[:feeds {via_pipeline: p.name, latency_minutes: r2.delay_minutes}]->(d2);
