from __future__ import annotations

from capmesh.models.manifest import Manifest
from capmesh.models.resolution import Binding


class MCPBindingAdapter:
    def supports(self, manifest: Manifest) -> bool:
        return manifest.interface.protocol == "mcp"

    def bind(self, manifest: Manifest, trace_id: str) -> Binding:
        meta = manifest.metadata
        iface = manifest.interface
        connection: dict = {"server": iface.server}
        if iface.tool_name:
            connection["tool_name"] = iface.tool_name
        return Binding(
            provider=f"{meta.namespace}/{meta.name}:{meta.version}",
            protocol="mcp",
            connection=connection,
            trace_id=trace_id,
        )
