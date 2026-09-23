# Release Checklist Skill

## Purpose
Execute a full pre-release checklist: generate missing tests,
security sign-off, and gate-controlled deployment.

## Procedure

### Step 1 — Test Coverage Gate
Use `test.generate/v1` to identify untested code paths and
generate unit/integration tests. Require minimum 80% coverage
before proceeding.

### Step 2 — Security Clearance
Use `security.code.review/v1` on the release branch.
Block release if any Critical/High findings remain unresolved.

### Step 3 — Deployment Gate
Use `deploy.execute/v1` to deploy to staging with:
- Blue/green switch
- Smoke test suite run
- Rollback plan verified

### Step 4 — Sign-Off Report
Produce a ReleaseChecklistReport with:
- Test gate: PASSED/FAILED (coverage %)
- Security gate: CLEARED/BLOCKED (finding count by severity)
- Staging deploy: SUCCESS/FAILED
- Overall: GO / NO-GO
