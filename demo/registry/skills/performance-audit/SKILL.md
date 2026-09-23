# Performance Audit Skill

## Purpose
Conduct a full-stack performance audit, identify bottlenecks,
and alert stakeholders.

## Procedure

### Step 1 — Collect Metrics
Use `metrics.query/v1` to gather 7-day trend data:
- API latency by endpoint (p50, p95, p99)
- Database query times
- Cache hit/miss ratios
- External dependency call times

### Step 2 — Deep Analysis
Use `performance.analyze/v1` on the codebase and runtime profiles:
- N+1 query detection
- Missing indexes
- Synchronous I/O in hot paths
- Memory allocation hot spots
- Thread pool / event loop blocking

### Step 3 — Benchmark Comparison
Compare against SLO targets and industry benchmarks.
Flag any metric exceeding threshold by >20%.

### Step 4 — Notify
Use `notification.send/v1` to send audit summary to:
- Engineering lead
- SRE on-call channel

### Step 5 — Report
Produce a PerformanceAuditReport with:
- Executive summary
- Top 5 bottlenecks with estimated impact
- Optimisation recommendations ranked by effort vs. gain
