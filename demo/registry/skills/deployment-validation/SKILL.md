# Deployment Validation Skill

## Purpose
Validate a deployment is healthy after rollout: check metrics,
run smoke tests, and notify stakeholders.

## Procedure

### Step 1 — Trigger Canary
Use `deploy.execute/v1` to deploy to 5% of traffic (canary).
Wait 5 minutes.

### Step 2 — Monitor Canary
Use `metrics.query/v1` to compare canary vs. baseline:
- Error rate delta (alert if >0.1% increase)
- Latency p99 delta (alert if >50ms increase)
- Business metrics (conversions, API calls) for regressions

### Step 3 — Decide
If canary is healthy: promote to 100% traffic.
If canary is degraded: automatic rollback via `deploy.execute/v1`.

### Step 4 — Post-Deploy Validation
Use `metrics.query/v1` at 15 min and 60 min post-deploy to
confirm stability.

### Step 5 — Notify
Use `notification.send/v1` to send deployment status to:
- Engineering Slack channel
- Deployment tracking ticket (if linked)

### Step 6 — Report
Produce a DeploymentValidationReport with:
- Canary verdict: HEALTHY / DEGRADED
- Full deploy status: SUCCESS / ROLLED_BACK
- Metric delta table
- Timeline of events
