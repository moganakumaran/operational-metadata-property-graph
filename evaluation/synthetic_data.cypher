// Synthetic retail lakehouse. Extends the running example in the paper with
// the minimum needed to exercise all seven queries non-trivially.
//
// Timeline of the modelled incident (all 2026-09-21):
//   01:45  ingest_fx run FAILS
//   01:50  orders_raw schema v2 becomes operationally valid (currency dropped)
//   02:02  smooth_fx assertion result: FAIL
//   02:10  metadata service first RECORDS schema v2  <-- 20 min after it was true
//   02:14  incident detected on orders_clean
//
// The 01:50 / 02:10 gap is the point of the bitemporal model: at 02:00 a
// pipeline could read v2 data while the catalog still believed v1.

// ---------------------------------------------------------------- datasets
CREATE (:Dataset {name:'orders_raw'});
CREATE (:Dataset {name:'fx_rates'});
CREATE (:Dataset {name:'fx_rates_smoothed'});
CREATE (:Dataset {name:'orders_clean'});
CREATE (:Dataset {name:'daily_revenue'});

// ---------------------------------------------------------------- pipelines
CREATE (:Pipeline {name:'ingest_orders', schedule_minutes:60});
CREATE (:Pipeline {name:'ingest_fx',     schedule_minutes:60});
CREATE (:Pipeline {name:'smooth_fx',     schedule_minutes:60});
CREATE (:Pipeline {name:'clean_orders',  schedule_minutes:60});
CREATE (:Pipeline {name:'agg_revenue',   schedule_minutes:1440});

MATCH (p:Pipeline {name:'ingest_orders'}), (d:Dataset {name:'orders_raw'})
  CREATE (p)-[:writes]->(d);
MATCH (p:Pipeline {name:'ingest_fx'}), (d:Dataset {name:'fx_rates'})
  CREATE (p)-[:writes]->(d);
MATCH (p:Pipeline {name:'smooth_fx'}), (d:Dataset {name:'fx_rates'})
  CREATE (p)-[:reads]->(d);
MATCH (p:Pipeline {name:'smooth_fx'}), (d:Dataset {name:'fx_rates_smoothed'})
  CREATE (p)-[:writes]->(d);
MATCH (p:Pipeline {name:'clean_orders'}), (d:Dataset {name:'orders_raw'})
  CREATE (p)-[:reads]->(d);
MATCH (p:Pipeline {name:'clean_orders'}), (d:Dataset {name:'fx_rates_smoothed'})
  CREATE (p)-[:reads]->(d);
MATCH (p:Pipeline {name:'clean_orders'}), (d:Dataset {name:'orders_clean'})
  CREATE (p)-[:writes]->(d);
MATCH (p:Pipeline {name:'agg_revenue'}), (d:Dataset {name:'orders_clean'})
  CREATE (p)-[:reads]->(d);
MATCH (p:Pipeline {name:'agg_revenue'}), (d:Dataset {name:'daily_revenue'})
  CREATE (p)-[:writes]->(d);

// ---------------------------------------------------------------- runs
// delay_minutes = ended_at - scheduled_for, in minutes. This is the one
// defensible reading of "latency" the paper commits to: observed delay of the
// run that materialised the downstream dataset.
CREATE (:Run {run_id:'r_ingest_orders_01', scheduled_for:timestamp('2026-09-21 01:00:00'),
              ended_at:timestamp('2026-09-21 01:05:00'), status:'SUCCESS', delay_minutes:5});
CREATE (:Run {run_id:'r_ingest_fx_01', scheduled_for:timestamp('2026-09-21 01:00:00'),
              ended_at:timestamp('2026-09-21 01:45:00'), status:'FAILED', delay_minutes:45});
CREATE (:Run {run_id:'r_smooth_fx_01', scheduled_for:timestamp('2026-09-21 01:30:00'),
              ended_at:timestamp('2026-09-21 01:50:00'), status:'SUCCESS', delay_minutes:20});
CREATE (:Run {run_id:'r_clean_orders_01', scheduled_for:timestamp('2026-09-21 02:00:00'),
              ended_at:timestamp('2026-09-21 02:12:00'), status:'SUCCESS', delay_minutes:12});
CREATE (:Run {run_id:'r_agg_revenue_01', scheduled_for:timestamp('2026-09-21 02:10:00'),
              ended_at:timestamp('2026-09-21 02:14:00'), status:'SUCCESS', delay_minutes:4});

MATCH (r:Run {run_id:'r_ingest_orders_01'}), (p:Pipeline {name:'ingest_orders'})
  CREATE (r)-[:instance_of]->(p);
MATCH (r:Run {run_id:'r_ingest_fx_01'}), (p:Pipeline {name:'ingest_fx'})
  CREATE (r)-[:instance_of]->(p);
MATCH (r:Run {run_id:'r_smooth_fx_01'}), (p:Pipeline {name:'smooth_fx'})
  CREATE (r)-[:instance_of]->(p);
MATCH (r:Run {run_id:'r_clean_orders_01'}), (p:Pipeline {name:'clean_orders'})
  CREATE (r)-[:instance_of]->(p);
MATCH (r:Run {run_id:'r_agg_revenue_01'}), (p:Pipeline {name:'agg_revenue'})
  CREATE (r)-[:instance_of]->(p);

// ---------------------------------------------------------------- schema versions
CREATE (:SchemaVersion {version_id:'orders_raw@v1', ordinal:1});
CREATE (:SchemaVersion {version_id:'orders_raw@v2', ordinal:2});
CREATE (:SchemaVersion {version_id:'orders_clean@v1', ordinal:1});
CREATE (:SchemaVersion {version_id:'daily_revenue@v1', ordinal:1});
CREATE (:SchemaVersion {version_id:'fx_rates@v1', ordinal:1});
CREATE (:SchemaVersion {version_id:'fx_rates_smoothed@v1', ordinal:1});

CREATE (:Field {fqn:'orders_raw.order_id', data_type:'BIGINT', nullable:false});
CREATE (:Field {fqn:'orders_raw.amount',   data_type:'DECIMAL', nullable:false});
CREATE (:Field {fqn:'orders_raw.currency', data_type:'STRING', nullable:false});
CREATE (:Field {fqn:'fx_rates.ccy',        data_type:'STRING', nullable:false});
CREATE (:Field {fqn:'fx_rates.rate',       data_type:'DECIMAL', nullable:false});
CREATE (:Field {fqn:'fx_rates_smoothed.ccy',  data_type:'STRING', nullable:false});
CREATE (:Field {fqn:'fx_rates_smoothed.rate', data_type:'DECIMAL', nullable:false});
CREATE (:Field {fqn:'orders_clean.order_id',  data_type:'BIGINT', nullable:false});
CREATE (:Field {fqn:'orders_clean.amount_usd',data_type:'DECIMAL', nullable:false});
CREATE (:Field {fqn:'daily_revenue.day',        data_type:'DATE', nullable:false});
CREATE (:Field {fqn:'daily_revenue.revenue_usd',data_type:'DECIMAL', nullable:false});

// v1 of orders_raw declares currency; v2 does not -- that is the breaking change.
MATCH (s:SchemaVersion {version_id:'orders_raw@v1'}), (f:Field)
  WHERE f.fqn IN ['orders_raw.order_id','orders_raw.amount','orders_raw.currency']
  CREATE (s)-[:declares]->(f);
MATCH (s:SchemaVersion {version_id:'orders_raw@v2'}), (f:Field)
  WHERE f.fqn IN ['orders_raw.order_id','orders_raw.amount']
  CREATE (s)-[:declares]->(f);
MATCH (s:SchemaVersion {version_id:'fx_rates@v1'}), (f:Field)
  WHERE f.fqn IN ['fx_rates.ccy','fx_rates.rate'] CREATE (s)-[:declares]->(f);
MATCH (s:SchemaVersion {version_id:'fx_rates_smoothed@v1'}), (f:Field)
  WHERE f.fqn IN ['fx_rates_smoothed.ccy','fx_rates_smoothed.rate']
  CREATE (s)-[:declares]->(f);
MATCH (s:SchemaVersion {version_id:'orders_clean@v1'}), (f:Field)
  WHERE f.fqn IN ['orders_clean.order_id','orders_clean.amount_usd']
  CREATE (s)-[:declares]->(f);
MATCH (s:SchemaVersion {version_id:'daily_revenue@v1'}), (f:Field)
  WHERE f.fqn IN ['daily_revenue.day','daily_revenue.revenue_usd']
  CREATE (s)-[:declares]->(f);

// has_schema, bitemporal. v1 was valid until 01:50 and was believed from
// 2026-01-01. v2 became valid at 01:50 but was only RECORDED at 02:10.
MATCH (d:Dataset {name:'orders_raw'}), (s:SchemaVersion {version_id:'orders_raw@v1'})
  CREATE (d)-[:has_schema {
    valid_from:timestamp('2026-01-01 00:00:00'), valid_to:timestamp('2026-09-21 01:50:00'),
    recorded_from:timestamp('2026-01-01 00:00:00'), recorded_to:timestamp('2026-09-21 02:10:00')
  }]->(s);
MATCH (d:Dataset {name:'orders_raw'}), (s:SchemaVersion {version_id:'orders_raw@v2'})
  CREATE (d)-[:has_schema {
    valid_from:timestamp('2026-09-21 01:50:00'), valid_to:timestamp('2999-01-01 00:00:00'),
    recorded_from:timestamp('2026-09-21 02:10:00'), recorded_to:timestamp('2999-01-01 00:00:00')
  }]->(s);
MATCH (d:Dataset), (s:SchemaVersion)
  WHERE (d.name='fx_rates' AND s.version_id='fx_rates@v1')
     OR (d.name='fx_rates_smoothed' AND s.version_id='fx_rates_smoothed@v1')
     OR (d.name='orders_clean' AND s.version_id='orders_clean@v1')
     OR (d.name='daily_revenue' AND s.version_id='daily_revenue@v1')
  CREATE (d)-[:has_schema {
    valid_from:timestamp('2026-01-01 00:00:00'), valid_to:timestamp('2999-01-01 00:00:00'),
    recorded_from:timestamp('2026-01-01 00:00:00'), recorded_to:timestamp('2999-01-01 00:00:00')
  }]->(s);

// ------------------------------------------------- column-level lineage
// amount_usd depends DIRECTLY on amount and rate, and INDIRECTLY on currency
// (used as a join/filter key, never projected). The INDIRECT case is the one a
// dataset-level or projection-only analysis misses.
MATCH (a:Field {fqn:'orders_clean.amount_usd'}), (b:Field {fqn:'orders_raw.amount'})
  CREATE (a)-[:derives_from {dependency:'DIRECT', subtype:'TRANSFORMATION',
    valid_from:timestamp('2026-01-01 00:00:00'), valid_to:timestamp('2999-01-01 00:00:00'),
    recorded_from:timestamp('2026-01-01 00:00:00'), recorded_to:timestamp('2999-01-01 00:00:00')}]->(b);
MATCH (a:Field {fqn:'orders_clean.amount_usd'}), (b:Field {fqn:'orders_raw.currency'})
  CREATE (a)-[:derives_from {dependency:'INDIRECT', subtype:'JOIN',
    valid_from:timestamp('2026-01-01 00:00:00'), valid_to:timestamp('2999-01-01 00:00:00'),
    recorded_from:timestamp('2026-01-01 00:00:00'), recorded_to:timestamp('2999-01-01 00:00:00')}]->(b);
MATCH (a:Field {fqn:'orders_clean.amount_usd'}), (b:Field {fqn:'fx_rates_smoothed.rate'})
  CREATE (a)-[:derives_from {dependency:'DIRECT', subtype:'TRANSFORMATION',
    valid_from:timestamp('2026-01-01 00:00:00'), valid_to:timestamp('2999-01-01 00:00:00'),
    recorded_from:timestamp('2026-01-01 00:00:00'), recorded_to:timestamp('2999-01-01 00:00:00')}]->(b);
MATCH (a:Field {fqn:'fx_rates_smoothed.rate'}), (b:Field {fqn:'fx_rates.rate'})
  CREATE (a)-[:derives_from {dependency:'DIRECT', subtype:'AGGREGATION',
    valid_from:timestamp('2026-01-01 00:00:00'), valid_to:timestamp('2999-01-01 00:00:00'),
    recorded_from:timestamp('2026-01-01 00:00:00'), recorded_to:timestamp('2999-01-01 00:00:00')}]->(b);
MATCH (a:Field {fqn:'daily_revenue.revenue_usd'}), (b:Field {fqn:'orders_clean.amount_usd'})
  CREATE (a)-[:derives_from {dependency:'DIRECT', subtype:'AGGREGATION',
    valid_from:timestamp('2026-01-01 00:00:00'), valid_to:timestamp('2999-01-01 00:00:00'),
    recorded_from:timestamp('2026-01-01 00:00:00'), recorded_to:timestamp('2999-01-01 00:00:00')}]->(b);
MATCH (a:Field {fqn:'orders_clean.order_id'}), (b:Field {fqn:'orders_raw.order_id'})
  CREATE (a)-[:derives_from {dependency:'DIRECT', subtype:'IDENTITY',
    valid_from:timestamp('2026-01-01 00:00:00'), valid_to:timestamp('2999-01-01 00:00:00'),
    recorded_from:timestamp('2026-01-01 00:00:00'), recorded_to:timestamp('2999-01-01 00:00:00')}]->(b);

// ---------------------------------------------------- quality assertions
// fx_rates deliberately has NO assertion: that is the Q7 coverage gap.
CREATE (:QualityAssertion {assertion_id:'a_orders_raw_rowcount', kind:'VOLUME', severity:'HIGH'});
CREATE (:QualityAssertion {assertion_id:'a_amount_usd_notnull', kind:'FIELD', severity:'HIGH'});
CREATE (:QualityAssertion {assertion_id:'a_smoothed_freshness', kind:'FRESHNESS', severity:'MEDIUM'});
CREATE (:QualityAssertion {assertion_id:'a_revenue_notnull', kind:'FIELD', severity:'HIGH'});

MATCH (q:QualityAssertion {assertion_id:'a_orders_raw_rowcount'}), (d:Dataset {name:'orders_raw'})
  CREATE (q)-[:asserts_on]->(d);
MATCH (q:QualityAssertion {assertion_id:'a_smoothed_freshness'}), (d:Dataset {name:'fx_rates_smoothed'})
  CREATE (q)-[:asserts_on]->(d);
MATCH (q:QualityAssertion {assertion_id:'a_amount_usd_notnull'}), (f:Field {fqn:'orders_clean.amount_usd'})
  CREATE (q)-[:asserts_on]->(f);
MATCH (q:QualityAssertion {assertion_id:'a_revenue_notnull'}), (f:Field {fqn:'daily_revenue.revenue_usd'})
  CREATE (q)-[:asserts_on]->(f);

CREATE (:AssertionResult {result_id:'ar_smoothed_01', outcome:'FAIL',
                          observed_at:timestamp('2026-09-21 02:02:00')});
CREATE (:AssertionResult {result_id:'ar_amount_usd_01', outcome:'PASS',
                          observed_at:timestamp('2026-09-21 02:12:00')});
MATCH (r:Run {run_id:'r_smooth_fx_01'}), (a:AssertionResult {result_id:'ar_smoothed_01'})
  CREATE (r)-[:produced]->(a);
MATCH (r:Run {run_id:'r_clean_orders_01'}), (a:AssertionResult {result_id:'ar_amount_usd_01'})
  CREATE (r)-[:produced]->(a);
MATCH (a:AssertionResult {result_id:'ar_smoothed_01'}), (q:QualityAssertion {assertion_id:'a_smoothed_freshness'})
  CREATE (a)-[:evaluates]->(q);
MATCH (a:AssertionResult {result_id:'ar_amount_usd_01'}), (q:QualityAssertion {assertion_id:'a_amount_usd_notnull'})
  CREATE (a)-[:evaluates]->(q);

// ------------------------------------------- consumers, owners, SLA, incident
CREATE (:Consumer {name:'pricing_service',   criticality:1});
CREATE (:Consumer {name:'finance_dashboard', criticality:3});
MATCH (c:Consumer {name:'pricing_service'}), (d:Dataset {name:'daily_revenue'})
  CREATE (c)-[:consumes]->(d);
MATCH (c:Consumer {name:'finance_dashboard'}), (d:Dataset {name:'daily_revenue'})
  CREATE (c)-[:consumes]->(d);

CREATE (:Principal {name:'data_platform_team', kind:'TEAM'});
CREATE (:Principal {name:'analytics_team',     kind:'TEAM'});
MATCH (p:Principal {name:'data_platform_team'}), (d:Dataset)
  WHERE d.name IN ['orders_raw','fx_rates','fx_rates_smoothed','orders_clean']
  CREATE (p)-[:owns]->(d);
MATCH (p:Principal {name:'analytics_team'}), (d:Dataset {name:'daily_revenue'})
  CREATE (p)-[:owns]->(d);
MATCH (p:Principal {name:'data_platform_team'}), (pl:Pipeline)
  WHERE pl.name IN ['ingest_orders','ingest_fx','smooth_fx','clean_orders']
  CREATE (p)-[:owns]->(pl);
MATCH (p:Principal {name:'analytics_team'}), (pl:Pipeline {name:'agg_revenue'})
  CREATE (p)-[:owns]->(pl);

CREATE (:SLA {sla_id:'sla_daily_revenue', max_staleness_minutes:30});
MATCH (d:Dataset {name:'daily_revenue'}), (s:SLA {sla_id:'sla_daily_revenue'})
  CREATE (d)-[:governed_by]->(s);

CREATE (:Incident {incident_id:'inc_0214', detected_at:timestamp('2026-09-21 02:14:00')});
MATCH (i:Incident {incident_id:'inc_0214'}), (d:Dataset {name:'orders_clean'})
  CREATE (i)-[:affects]->(d);
