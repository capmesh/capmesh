from __future__ import annotations

from pathlib import Path

from capmesh.models.enums import Kind
from capmesh.models.manifest import Manifest
from capmesh.registry.storage import ArtifactRecord, Storage


class Registry:
    def __init__(self, root: Path | None = None) -> None:
        if root is None:
            root = Path.home() / ".capmesh"
        self._storage = Storage(root)
        self._storage.init()

    def register(self, manifest: Manifest) -> str:
        return self._storage.save_manifest(manifest)

    def get(self, namespace: str, name: str, version: str) -> Manifest | None:
        return self._storage.load_manifest(namespace, name, version)

    def providers_for(self, capability: str, contract: str) -> list[ArtifactRecord]:
        return self._storage.find_providers(capability, contract)

    def search(self, query: str) -> list[ArtifactRecord]:
        return self._storage.search(query)

    def list(
        self, namespace: str | None = None, kind: Kind | None = None
    ) -> list[ArtifactRecord]:
        return self._storage.list_artifacts(namespace=namespace, kind=kind)

    def tag(self, namespace: str, name: str, version: str, tag: str) -> None:
        self._storage.add_tag(namespace, name, version, tag)

    def delete(self, namespace: str, name: str, version: str) -> None:
        self._storage.delete_artifact(namespace, name, version)

    def rebuild_index(self) -> int:
        return self._storage.rebuild_index()
