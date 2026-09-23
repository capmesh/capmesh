# Onboarding Guide Skill

## Purpose
Generate a personalized onboarding guide for new engineers joining
a team, based on actual repository structure and existing docs.

## Procedure

### Step 1 — Repository Survey
Use `repository.read/v1` to inventory:
- README files at every level
- Architecture decision records (ADR)
- CI/CD pipeline configurations
- Service dependency graph (from docker-compose, k8s manifests)
- Key entry points (main files, CLI commands)

### Step 2 — Gap Analysis
Identify missing or outdated documentation sections.
Flag services with no runbook.

### Step 3 — Generate Guide
Use `documentation.generate/v1` to produce:
- "Getting Started in 30 Minutes" step-by-step guide
- Local development environment setup
- Architecture overview with service map
- Common workflows (deploy, rollback, add a feature)
- Glossary of team-specific terms

### Step 4 — Output
Produce an OnboardingGuide document with structured sections,
estimated reading time, and links to authoritative sources.
