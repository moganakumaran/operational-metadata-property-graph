// Q2 Breaking change.
// Input : field f to be removed/retyped ('orders_raw.currency')
// Output: downstream fields depending on f, with dependency kind, plus the
//         consumers ultimately exposed
// Capability: column-level lineage closure + schema versioning
// Note the INDIRECT/JOIN dependency: amount_usd never projects currency, but
// joins on it, so a projection-only analysis would call this change safe.
MATCH path = (downstream:Field)-[:derives_from*1..10]->(target:Field)
WHERE target.fqn = 'orders_raw.currency'
RETURN DISTINCT downstream.fqn AS affected_field,
       length(path) AS hops
ORDER BY hops ASC, affected_field ASC;
