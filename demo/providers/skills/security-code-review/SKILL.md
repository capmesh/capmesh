# Security Code Review

## Procedure
1. Use repository.search to find security-sensitive files
   (auth modules, config files, API endpoints, secrets)
2. Use repository.read to examine each file
3. Check for OWASP Top 10 vulnerabilities
4. Rate each finding: CRITICAL / HIGH / MEDIUM / LOW
5. Generate a structured findings report

## What to look for
- Hardcoded secrets and API keys
- SQL injection (string concatenation in queries)
- XSS (unescaped user input in templates)
- Insecure authentication patterns
- Debug mode in production configs
- Missing input validation
- Insecure deserialization
