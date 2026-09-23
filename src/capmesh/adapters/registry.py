from __future__ import annotations

from capmesh.adapters.base import BindingAdapter
from capmesh.models.manifest import Manifest
from capmesh.models.resolution import Binding


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: list[BindingAdapter] = []

    def register(self, adapter: BindingAdapter) -> None:
        self._adapters.append(adapter)

    def get_adapter(self, manifest: Manifest) -> BindingAdapter:
        for adapter in self._adapters:
            if adapter.supports(manifest):
                return adapter
        raise ValueError(f"No adapter found for protocol '{manifest.interface.protocol}'")

    def bind(self, manifest: Manifest, trace_id: str) -> Binding:
        adapter = self.get_adapter(manifest)
        return adapter.bind(manifest, trace_id)
