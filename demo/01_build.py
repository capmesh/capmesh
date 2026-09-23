#!/usr/bin/env python3
"""
Step 1: Build all providers — validate manifests and compute digests.

Like 'docker build' — this checks your YAML is valid, computes a
sha256 digest, and confirms the provider is ready to register.

Nothing is stored yet. This is a pre-flight check.
"""
from pathlib import Path

from capmesh.models.serialization import manifest_from_yaml, compute_digest

providers_dir = Path(__file__).parent / "providers"

print("=" * 70)
print("  CAPMESH DEMO - Step 1: Build (validate + digest)")
print("=" * 70)
print()

built = []
errors = []

for manifest_path in sorted(providers_dir.rglob("manifest.yaml")):
    rel_path = manifest_path.relative_to(providers_dir)
    folder = str(rel_path.parent)

    try:
        # Read YAML
        yaml_str = manifest_path.read_text(encoding="utf-8")

        # Validate — this will fail if the manifest is malformed
        manifest = manifest_from_yaml(yaml_str)

        # Compute digest
        digest = compute_digest(manifest)

        m = manifest.metadata
        caps = ", ".join(c.capability for c in manifest.provides)
        reqs = ", ".join(c.capability for c in manifest.requires) or "none"
        labels = manifest.governance.labels
        framework = labels.get("framework", "")

        print(f"  BUILD {folder}")
        print(f"    Kind:      {m.kind.value}")
        print(f"    Name:      {m.namespace}/{m.name}:{m.version}")
        print(f"    Protocol:  {manifest.interface.protocol}")
        print(f"    Provides:  {caps}")
        print(f"    Requires:  {reqs}")
        if framework:
            print(f"    Framework: {framework}")
        print(f"    Digest:    sha256:{digest}")
        print(f"    Status:    VALID")
        print()

        built.append((manifest, digest, folder))

    except Exception as e:
        print(f"  BUILD {folder}")
        print(f"    Status:    FAILED - {e}")
        print()
        errors.append((folder, str(e)))

# Summary
print("-" * 70)
if errors:
    print(f"  {len(built)} built, {len(errors)} FAILED")
    for folder, err in errors:
        print(f"    FAIL: {folder} - {err}")
else:
    print(f"  {len(built)} providers built successfully. All manifests valid.")
    print()
    print("  Digests are deterministic — same content always produces the same hash.")
    print("  Once registered, the same name+version can never be overwritten")
    print("  with different content (immutability).")

print()
print("  CLI equivalent for each provider:")
print("  $ capmesh tool build --directory demo/providers/tools/github-reader/")
print("  $ capmesh agent build --directory demo/providers/agents/langgraph-security-reviewer/")
print("  $ capmesh skill build --directory demo/providers/skills/security-code-review/")
print()
print("  Next: Run 02_register.py to store them in the registry.")
print()
