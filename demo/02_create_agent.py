#!/usr/bin/env python3
"""
STEP 2: How to write an Agent

An Agent is an autonomous service that provides a capability via A2A protocol.
It could be built with LangGraph, CrewAI, Strands, or any framework.
CapMesh doesn't care about the framework — only the capability.
"""

print("""
===============================================================
  STEP 2: Writing an Agent Manifest
===============================================================

An Agent manifest describes:
  - What capability this agent provides
  - Its A2A endpoint
  - What capabilities it requires from others
""")

from capmesh.models import (
    A2AInterface, CapabilityRef, Governance, Kind,
    Manifest, Metadata, Status, Visibility,
)
from capmesh.models.serialization import manifest_to_yaml

agent = Manifest(
    metadata=Metadata(
        kind=Kind.AGENT,
        namespace="security",
        name="security-reviewer",
        version="2.4.0",
        owner="security-engineering",
    ),
    provides=[
        CapabilityRef(capability="security.code.review", contract="v1"),
    ],
    requires=[
        CapabilityRef(capability="repository.read", contract="v1"),
    ],
    interface=A2AInterface(
        protocol="a2a",
        endpoint="https://security-agent.example.com",
    ),
    governance=Governance(
        visibility=Visibility.PUBLIC,
        status=Status.APPROVED,
        environment=["production", "staging"],
    ),
)

yaml_output = manifest_to_yaml(agent)

print("  manifest.yaml:")
print("  " + "-" * 50)
for line in yaml_output.strip().split("\n"):
    print(f"  {line}")

print("""
  Key points:
  - 'provides' says this agent can do security.code.review
  - 'requires' says it NEEDS repository.read (but doesn't say WHO provides it)
  - 'interface.protocol: a2a' means it speaks the A2A protocol
  - 'governance.environment' limits it to production and staging
  - Framework (LangGraph, CrewAI, etc.) is NOT in the manifest — it's irrelevant
""")

print("  CLI equivalent:")
print("  $ capmesh agent init --namespace security --name security-reviewer --version 2.4.0 --owner security-engineering")
print()
