# Incident Triage Skill

## Purpose
Rapidly diagnose production incidents, create tracking tickets,
and notify on-call responders.

## Procedure

### Step 1 — Gather Metrics
Use `metrics.query/v1` to pull the last 30 minutes of:
- Latency percentiles (p50, p95, p99)
- Error rate and 5xx counts
- Throughput (requests/sec)
- Infrastructure metrics (CPU, memory, disk I/O)
- Downstream service health

### Step 2 — Correlate and Hypothesize
Compare current metrics against baseline (same time last week).
Identify the most likely root cause from:
- Traffic spike
- Memory leak / GC pressure
- Database slow queries
- Downstream dependency failure
- Deployment regression

### Step 3 — Create Incident Ticket
Use `issue.create/v1` to open a P1/P2 ticket with:
- Incident timeline
- Hypothesis and supporting data
- Affected services and customers
- Assigned on-call engineer

### Step 4 — Notify
Use `notification.send/v1` to alert:
- On-call Slack channel with incident summary
- Management escalation if P1
- Status page update if customer-facing

### Step 5 — Produce Triage Report
Output an IncidentTriageReport with severity, hypotheses ranked
by confidence, and recommended next actions.
