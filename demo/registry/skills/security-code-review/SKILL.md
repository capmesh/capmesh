# Security Code Review Skill

## Purpose
Perform a thorough security review of a code repository, identifying
vulnerabilities, misconfigurations, and compliance issues.

## Procedure

### Step 1 — Fetch Repository Context
Use `repository.read/v1` to fetch the target branch at HEAD.
Retrieve: all source files, dependency manifests (package.json,
requirements.txt, go.mod, pom.xml), CI/CD configuration files,
and infrastructure-as-code templates.

### Step 2 — Search for Known Patterns
Use `repository.search/v1` to scan for:
- Hardcoded secrets (API keys, tokens, passwords)
- Insecure function calls (eval, exec, shell injection sinks)
- Deprecated cryptographic primitives (MD5, SHA1, DES)
- SQL injection patterns (string-concatenated queries)
- SSRF-prone URL construction patterns

### Step 3 — Run Automated Scan
Use `security.scan/v1` to run the full dependency and SAST scan.
Collect:
- CVE list with severity (critical/high/medium/low)
- License compliance report
- OWASP Top 10 checklist results

### Step 4 — Triage and Score
Classify each finding by:
- Severity: Critical / High / Medium / Low / Informational
- Exploitability: Direct / Indirect / Theoretical
- Fix effort: Trivial / Moderate / Complex

### Step 5 — Produce Report
Output a structured SecurityReviewReport containing:
- Executive summary (1 paragraph)
- Critical findings table (finding, location, CWE, recommendation)
- CVE table (package, version, CVE-ID, severity, fix version)
- Overall risk score (0-100)
- Sign-off decision: APPROVED / CONDITIONAL / BLOCKED
