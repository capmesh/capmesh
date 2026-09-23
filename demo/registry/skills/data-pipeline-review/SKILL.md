# Data Pipeline Review Skill

## Purpose
Review data pipeline health, data quality, and transformation
logic correctness.

## Procedure

### Step 1 — Sample Data
Use `data.query/v1` to sample recent pipeline output:
- Last 10,000 rows from each output table
- Row counts at each pipeline stage
- Null/empty value ratios per column
- Distribution of key categorical fields

### Step 2 — Quality Analysis
Use `data.analyze/v1` to check:
- Schema drift (unexpected column additions/removals)
- Data type consistency
- Referential integrity violations
- Duplicate key detection
- Outlier detection in numeric fields

### Step 3 — Lineage Audit
Trace data from source to final sink.
Verify transformation logic matches documented business rules.

### Step 4 — Report
Produce a DataPipelineReport with:
- Data quality score (0-100) per table
- Anomaly list with row-level examples
- Schema change log
- Recommended fixes with effort estimate
