// Reference model schema: 11 node labels, 13 edge types.
// Kuzu requires explicit typed node and relationship tables, which is useful
// here: the schema file IS the formal model, so any edge used by a query but
// absent from the model fails at load time rather than passing unnoticed.
//
// Temporal edges (has_schema, derives_from) carry FOUR timestamps:
//   valid_from / valid_to          valid time  - true in the operational world
//   recorded_from / recorded_to    system time - believed by the metadata store
// This is the application-time / system-time pair of SQL:2011.

CREATE NODE TABLE Dataset(
  name STRING, PRIMARY KEY(name));
CREATE NODE TABLE SchemaVersion(
  version_id STRING, ordinal INT64, PRIMARY KEY(version_id));
CREATE NODE TABLE Field(
  fqn STRING, data_type STRING, nullable BOOLEAN, PRIMARY KEY(fqn));
CREATE NODE TABLE Pipeline(
  name STRING, schedule_minutes INT64, PRIMARY KEY(name));
CREATE NODE TABLE Run(
  run_id STRING, scheduled_for TIMESTAMP, ended_at TIMESTAMP,
  status STRING, delay_minutes INT64, PRIMARY KEY(run_id));
CREATE NODE TABLE QualityAssertion(
  assertion_id STRING, kind STRING, severity STRING, PRIMARY KEY(assertion_id));
CREATE NODE TABLE AssertionResult(
  result_id STRING, outcome STRING, observed_at TIMESTAMP, PRIMARY KEY(result_id));
CREATE NODE TABLE Consumer(
  name STRING, criticality INT64, PRIMARY KEY(name));
CREATE NODE TABLE Principal(
  name STRING, kind STRING, PRIMARY KEY(name));
CREATE NODE TABLE SLA(
  sla_id STRING, max_staleness_minutes INT64, PRIMARY KEY(sla_id));
CREATE NODE TABLE Incident(
  incident_id STRING, detected_at TIMESTAMP, PRIMARY KEY(incident_id));

// --- structural edges
CREATE REL TABLE reads(FROM Pipeline TO Dataset);
CREATE REL TABLE writes(FROM Pipeline TO Dataset);
CREATE REL TABLE declares(FROM SchemaVersion TO Field);
CREATE REL TABLE instance_of(FROM Run TO Pipeline);
CREATE REL TABLE produced(FROM Run TO AssertionResult);
// The edge Figure 1 drew as "of" and Table 1 omitted. Q3 needs it to get from
// a failed run to what was asserted; Q7 needs it to decide coverage.
CREATE REL TABLE evaluates(FROM AssertionResult TO QualityAssertion);
CREATE REL TABLE asserts_on(FROM QualityAssertion TO Dataset,
                            FROM QualityAssertion TO Field);
CREATE REL TABLE consumes(FROM Consumer TO Dataset);
CREATE REL TABLE owns(FROM Principal TO Dataset,
                      FROM Principal TO Pipeline);
CREATE REL TABLE governed_by(FROM Dataset TO SLA);
CREATE REL TABLE affects(FROM Incident TO Dataset);

// --- temporal edges: bitemporal, four timestamps each
CREATE REL TABLE has_schema(FROM Dataset TO SchemaVersion,
  valid_from TIMESTAMP, valid_to TIMESTAMP,
  recorded_from TIMESTAMP, recorded_to TIMESTAMP);
CREATE REL TABLE derives_from(FROM Field TO Field,
  dependency STRING, subtype STRING,
  valid_from TIMESTAMP, valid_to TIMESTAMP,
  recorded_from TIMESTAMP, recorded_to TIMESTAMP);

// --- derived relation, NOT a primitive of the model.
// feeds(d1,d2) holds iff some pipeline reads d1 and writes d2. It is
// materialised by derive_feeds.cypher from reads/writes so that Q4 can use
// variable-length traversal; the paper states the derivation rule and treats
// this table as a view, not as modelled ground truth.
CREATE REL TABLE feeds(FROM Dataset TO Dataset,
  via_pipeline STRING, latency_minutes INT64);
