# Full Code Review Skill

## Purpose
Deliver a comprehensive code review combining quality metrics,
architecture assessment, and security scanning.

## Procedure

### Step 1 — Fetch Code
Use `repository.read/v1` to retrieve all modified files in the
target diff or branch.

### Step 2 — Static Analysis
Use `code.quality/v1` to obtain:
- Code coverage percentage
- Cyclomatic complexity per module
- Technical debt estimate (hours)
- Duplication ratio
- Maintainability index

### Step 3 — Security Pass
Use `security.scan/v1` for a lightweight security pass:
- Dependency vulnerabilities
- Obvious injection sinks

### Step 4 — Architecture Review
Assess:
- Layer boundary violations
- Circular dependency detection
- API contract consistency

### Step 5 — Report
Produce a CodeReviewReport with:
- Per-file quality scores
- Actionable improvement list (ranked by impact)
- Security finding summary
- Overall recommendation: APPROVE / REQUEST_CHANGES / REJECT
