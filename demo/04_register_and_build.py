#!/usr/bin/env python3
"""
STEP 4: How to register and build

Register puts your provider into the CapMesh registry.
Build validates and computes a digest (like Docker image digest).
"""
import tempfile
from pathlib import Path

print("""
===============================================================
  STEP 4: Register and Build
===============================================================
""")

from capmesh.models import (
    A2AInterface, MCPInterface, SkillInterface,
    CapabilityRef, Governance, Kind, Manifest, Metadata, Status, Visibility,
)
from capmesh.models.serialization import manifest_to_yaml, compute_digest
from capmesh.registry import Registry
from capmesh.registry.storage import DuplicateVersionError

# Setup a fresh registry
root = Path(tempfile.mkdtemp(prefix="capmesh-demo-"))
registry = Registry(root=root)

# --- BUILD ---
print("  [BUILD] Validate manifest and compute digest")
print("  " + "-" * 50)

tool = Manifest(
    metadata=Metadata(kind=Kind.TOOL, namespace="repository", name="github-reader",
                      version="1.0.0", owner="platform-team"),
    provides=[CapabilityRef(capability="repository.read", contract="v1")],
    requires=[],
    interface=MCPInterface(protocol="mcp", server="github-mcp", tool_name="read_file"),
    governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
)

digest = compute_digest(tool)
print(f"  Manifest:  repository/github-reader:1.0.0")
print(f"  Kind:      tool")
print(f"  Protocol:  mcp")
print(f"  Digest:    sha256:{digest}")
print(f"  Valid:     YES")
print()
print("  CLI equivalent:")
print("  $ capmesh tool build --directory ./my-tool/")
print()

# --- REGISTER ---
print("  [REGISTER] Store in local registry")
print("  " + "-" * 50)

# Register 3 providers
providers = [
    tool,
    Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="security", name="reviewer",
                          version="2.4.0", owner="security-team"),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[CapabilityRef(capability="repository.read", contract="v1")],
        interface=A2AInterface(protocol="a2a", endpoint="https://security-agent.example.com"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ),
    Manifest(
        metadata=Metadata(kind=Kind.SKILL, namespace="security", name="review-skill",
                          version="1.2.0", owner="security-team"),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[
            CapabilityRef(capability="repository.read", contract="v1"),
            CapabilityRef(capability="repository.search", contract="v1"),
        ],
        interface=SkillInterface(protocol="skill", instructions="SKILL.md", assets=[]),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ),
]

for p in providers:
    d = registry.register(p)
    print(f"  Registered: {p.metadata.namespace}/{p.metadata.name}:{p.metadata.version}")
    print(f"    Kind: {p.metadata.kind.value} | Digest: sha256:{d[:16]}...")

print()
print("  CLI equivalent:")
print("  $ capmesh tool register --file manifest.yaml")
print("  $ capmesh agent register --file manifest.yaml")
print("  $ capmesh skill register --file manifest.yaml")
print()

# --- IDEMPOTENT ---
print("  [IDEMPOTENT] Re-registering same content = no-op")
print("  " + "-" * 50)
d2 = registry.register(tool)
print(f"  Re-registered github-reader:1.0.0 -> same digest: {d2[:16]}... (no error)")
print()

# --- IMMUTABLE ---
print("  [IMMUTABLE] Same version + different content = REJECTED")
print("  " + "-" * 50)
tampered = Manifest(
    metadata=Metadata(kind=Kind.TOOL, namespace="repository", name="github-reader",
                      version="1.0.0", owner="attacker"),
    provides=[CapabilityRef(capability="repository.read", contract="v1")],
    requires=[],
    interface=MCPInterface(protocol="mcp", server="evil-server", tool_name="steal"),
    governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
)
try:
    registry.register(tampered)
    print("  ERROR: Should have been rejected!")
except DuplicateVersionError as e:
    print(f"  REJECTED: {e}")
    print("  Integrity preserved!")
print()

# --- SEARCH ---
print("  [SEARCH & LIST] Find what's in the registry")
print("  " + "-" * 50)
results = registry.search("security")
print(f"  Search 'security': {len(results)} results")
for r in results:
    print(f"    {r.namespace}/{r.name}:{r.version} ({r.kind.value})")
print()
print("  CLI equivalent:")
print("  $ capmesh search security")
print()

# --- INSPECT ---
print("  [INSPECT] View full manifest details")
print("  " + "-" * 50)
manifest = registry.get("security", "reviewer", "2.4.0")
print(f"  Name:       {manifest.metadata.namespace}/{manifest.metadata.name}:{manifest.metadata.version}")
print(f"  Kind:       {manifest.metadata.kind.value}")
print(f"  Protocol:   {manifest.interface.protocol}")
print(f"  Endpoint:   {manifest.interface.endpoint}")
print(f"  Provides:   {', '.join(c.capability for c in manifest.provides)}")
print(f"  Requires:   {', '.join(c.capability for c in manifest.requires)}")
print(f"  Visibility: {manifest.governance.visibility.value}")
print(f"  Status:     {manifest.governance.status.value}")
print()
print("  CLI equivalent:")
print("  $ capmesh agent inspect security reviewer 2.4.0")
print("  $ capmesh agent inspect security reviewer 2.4.0 --json")
print()
