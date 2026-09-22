// Q6 Change attribution, bitemporal.
//
// Input is a DATASET plus the two times, not an incident. In the worked
// example that dataset is orders_raw -- an upstream candidate Q3 surfaces --
// not the incident dataset orders_clean. Q3 narrows, Q6 attributes.
// Input : incident time t = 02:14, belief time b = 02:00
// Output: the schema version that was VALID at t, and the one the catalog
//         BELIEVED at b -- which are different, and that difference is the
//         finding the query exists to surface.
// Capability: two independent temporal dimensions on the same edge
//
//   valid time  [valid_from, valid_to)      true in the operational world
//   system time [recorded_from, recorded_to) held by the metadata store
//
// orders_raw@v2 became valid at 01:50 but was recorded only at 02:10, so a
// pipeline running at 02:00 read v2-shaped data while the catalog still
// answered v1. A single-dimension version history cannot represent this.
MATCH (d:Dataset)-[e:has_schema]->(s:SchemaVersion)
WHERE d.name = 'orders_raw'
RETURN s.version_id AS schema_version,
       (e.valid_from <= timestamp('2026-09-21 02:14:00')
        AND e.valid_to > timestamp('2026-09-21 02:14:00'))   AS valid_at_incident,
       (e.recorded_from <= timestamp('2026-09-21 02:00:00')
        AND e.recorded_to > timestamp('2026-09-21 02:00:00')) AS believed_at_0200
ORDER BY s.ordinal ASC;
