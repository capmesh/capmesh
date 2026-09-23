from __future__ import annotations

from capmesh.models.manifest import Manifest
from capmesh.models.resolution import Binding


class A2ABindingAdapter:
    def supports(self, manifest: Manifest) -> bool:
        return manifest.interface.protocol == "a2a"

    def bind(self, manifest: Manifest, trace_id: str) -> Binding:
        meta = manifest.metadata
        iface = manifest.interface
        return Binding(
            provider=f"{meta.namespace}/{meta.name}:{meta.version}",
            protocol="a2a",
            connection={"endpoint": iface.endpoint},
            trace_id=trace_id,
        )
