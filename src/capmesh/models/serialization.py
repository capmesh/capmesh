from __future__ import annotations

import hashlib

import yaml

from capmesh.models.manifest import Manifest


class _CanonicalDumper(yaml.Dumper):
    """YAML dumper that indents list items (never uses indentless blocks)."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        return super().increase_indent(flow, False)


def manifest_to_yaml(manifest: Manifest) -> str:
    """Serialize a Manifest to canonical YAML (sorted keys, digest excluded)."""
    data = manifest.model_dump(mode="json")
    # Exclude digest from canonical form — it's computed from the content
    data.get("metadata", {}).pop("digest", None)
    return yaml.dump(data, Dumper=_CanonicalDumper, sort_keys=True, default_flow_style=False)


def manifest_from_yaml(yaml_str: str) -> Manifest:
    """Deserialize YAML string to a Manifest."""
    data = yaml.safe_load(yaml_str)
    return Manifest.model_validate(data)


def compute_digest(manifest: Manifest) -> str:
    """Compute sha256 hex digest of the canonical YAML representation."""
    canonical = manifest_to_yaml(manifest)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
