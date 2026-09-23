#!/usr/bin/env python3
"""
STEP 3: How to write a Skill

A Skill describes HOW work should be performed — procedural instructions
that an agent follows. It declares what capabilities it needs, but does
NOT hardcode which tools or agents provide them.

This is CapMesh's key insight: Skills are portable across tool vendors.
"""

print("""
===============================================================
  STEP 3: Writing a Skill Manifest + Instructions
===============================================================

A Skill has two parts:
  1. manifest.yaml — declares capabilities provided and required
  2. SKILL.md — procedural instructions for the agent
""")

from capmesh.models import (
    SkillInterface, CapabilityRef, Governance, Kind,
    Manifest, Metadata, Status, Visibility,
)
from capmesh.models.serialization import manifest_to_yaml

skill = Manifest(
    metadata=Metadata(
        kind=Kind.SKILL,
        namespace="security",
        name="security-code-review",
        version="1.2.0",
        owner="security-engineering",
    ),
    provides=[
        CapabilityRef(capability="security.code.review", contract="v1"),
    ],
    requires=[
        CapabilityRef(capability="repository.read", contract="v1"),
        CapabilityRef(capability="repository.search", contract="v1"),
    ],
    interface=SkillInterface(
        protocol="skill",
        instructions="SKILL.md",
        assets=[],
    ),
    governance=Governance(
        visibility=Visibility.PUBLIC,
        status=Status.APPROVED,
    ),
)

yaml_output = manifest_to_yaml(skill)

print("  manifest.yaml:")
print("  " + "-" * 50)
for line in yaml_output.strip().split("\n"):
    print(f"  {line}")

skill_md = """# Security Code Review

## Procedure
1. Use repository.search to find security-sensitive files
   (auth modules, config files, API endpoints)
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
"""

print()
print("  SKILL.md:")
print("  " + "-" * 50)
for line in skill_md.strip().split("\n"):
    print(f"  {line}")

print("""
  Key points:
  - 'requires' lists capabilities, NOT specific tools
  - The skill says "use repository.search" — not "use GitHub" or "use GitLab"
  - When CapMesh binds this skill, it SEPARATELY resolves each required
    capability to a real tool (dual binding)
  - Same skill works with GitHub, GitLab, Bitbucket — no changes needed
""")

print("  CLI equivalent:")
print("  $ capmesh skill init --namespace security --name security-code-review --version 1.2.0 --owner security-engineering")
print()
