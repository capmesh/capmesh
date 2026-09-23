# Pull Request Review Skill

## Purpose
End-to-end pull request review combining code quality and security
analysis, producing a single actionable PR report.

## Procedure

### Step 1 — Load PR Metadata
Use `repository.read/v1` to load:
- PR title, description, linked issues
- Diff summary (files changed, lines added/removed)
- Reviewer assignments and prior comments

### Step 2 — Code Quality Review
Invoke `code.review/v1` on the PR diff to obtain quality findings.

### Step 3 — Security Review
Invoke `security.code.review/v1` on the PR diff to obtain security
findings.

### Step 4 — Consolidate
Merge findings, deduplicate overlapping issues, and rank by
severity and impact.

### Step 5 — Author Summary
Produce a PRReviewReport with:
- LGTM / Changes Requested verdict
- Inline comment suggestions for each finding
- Summary paragraph for reviewers
- Checklist: tests added, docs updated, breaking changes flagged
