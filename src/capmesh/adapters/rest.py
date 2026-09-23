from __future__ import annotations

from capmesh.models.manifest import Manifest
from capmesh.models.resolution import Binding


class RESTBindingAdapter:
    def supports(self, manifest: Manifest) -> bool:
        return manifest.interface.protocol == "rest"

    def bind(self, manifest: Manifest, trace_id: str) -> Binding:
        meta = manifest.metadata
        iface = manifest.interface
        return Binding(
            provider=f"{meta.namespace}/{meta.name}:{meta.version}",
            protocol="rest",
            connection={
                "endpoint": iface.endpoint,
                "auth_type": iface.auth_type,
                "request_mapping": iface.request_mapping,
                "response_mapping": iface.response_mapping,
            },
            trace_id=trace_id,
        )
