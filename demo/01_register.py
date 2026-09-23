#!/usr/bin/env python3
"""
Step 1: Register all providers from YAML manifests and build the registry.

This script walks the providers/ directory, loads every manifest.yaml,
registers it in a fresh CapMesh registry, and shows what's available.
"""
import os
import sys
import tempfile
from pathlib import Path

from capmesh.models.serialization import manifest_from_yaml
from capmesh.registry import Registry

# Use a shared temp dir so Step 2 can read the same registry
DEMO_ROOT = Path(tempfile.gettempdir()) / "capmesh-demo-registry"
DEMO_ROOT.mkdir(parents=True, exist_ok=True)
os.environ["CAPMESH_DEMO_ROOT"] = str(DEMO_ROOT)

# Write the root path so step 2 can find it
(Path(__file__).parent / ".demo_root").write_text(str(DEMO_ROOT))

registry = Registry(root=DEMO_ROOT)
providers_dir = Path(__file__).parent / "providers"

print("=" * 70)
print("  CAPMESH DEMO — Step 1: Register Providers")
print("=" * 70)
print(f"  Registry: {DEMO_ROOT}")
print()

# Walk all manifest.yaml files
registered = []
for manifest_path in sorted(providers_dir.rglob("manifest.yaml")):
    yaml_str = manifest_path.read_text(encoding="utf-8")
    manifest = manifest_from_yaml(yaml_str)
    digest = registry.register(manifest)

    m = manifest.metadata
    caps = ", ".join(c.capability for c in manifest.provides)
    reqs = ", ".join(c.capability for c in manifest.requires) or "none"
    labels = manifest.governance.labels
    framework = labels.get("framework", "-")

    registered.append(manifest)

    print(f"  [{m.kind.value.upper():5s}] {m.namespace}/{m.name}:{m.version}")
    print(f"         Protocol:  {manifest.interface.protocol}")
    print(f"         Provides:  {caps}")
    print(f"         Requires:  {reqs}")
    if framework != "-":
        print(f"         Framework: {framework}")
    print(f"         Digest:    sha256:{digest[:20]}...")
    print()

# Summary
print("-" * 70)
print(f"  Registered {len(registered)} providers:")
tools = [m for m in registered if m.metadata.kind.value == "tool"]
agents = [m for m in registered if m.metadata.kind.value == "agent"]
skills = [m for m in registered if m.metadata.kind.value == "skill"]
print(f"    Tools:  {len(tools)}  ({', '.join(m.metadata.name for m in tools)})")
print(f"    Agents: {len(agents)}  ({', '.join(m.metadata.name for m in agents)})")
print(f"    Skills: {len(skills)}  ({', '.join(m.metadata.name for m in skills)})")
print()

# Show what capabilities are available
print("  Available capabilities:")
seen = set()
for m in registered:
    for cap in m.provides:
        key = f"{cap.capability}/{cap.contract}"
        if key not in seen:
            providers = registry.providers_for(cap.capability, cap.contract)
            names = [f"{p.name}:{p.version}" for p in providers]
            print(f"    {cap.capability}/{cap.contract}")
            for name in names:
                print(f"      -> {name}")
            seen.add(key)
print()
print("  Registry built. Run 02_resolve.py to see it in action.")
print()
