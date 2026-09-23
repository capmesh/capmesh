from __future__ import annotations

from typing import TYPE_CHECKING

from capmesh.models.manifest import Manifest
from capmesh.models.resolution import Binding, CallerContext, ResolveRequest

if TYPE_CHECKING:
    from capmesh.resolver.resolver import Resolver


class SkillBindingAdapter:
    def __init__(self, resolver: Resolver | None = None) -> None:
        self._resolver = resolver

    def supports(self, manifest: Manifest) -> bool:
        return manifest.interface.protocol == "skill"

    def bind(self, manifest: Manifest, trace_id: str) -> Binding:
        meta = manifest.metadata
        iface = manifest.interface

        # Step 1: Load skill instructions and assets
        connection: dict = {
            "instructions": iface.instructions,
            "assets": list(iface.assets),
            "tool_bindings": [],
        }

        # Step 2: Resolve required capabilities into tool bindings
        if self._resolver and manifest.requires:
            tool_bindings = []
            for req in manifest.requires:
                try:
                    resolution = self._resolver.resolve(
                        ResolveRequest(
                            capability=req.capability,
                            contract=req.contract,
                            caller=CallerContext(identity=f"skill:{meta.name}"),
                        )
                    )
                    tool_bindings.append({
                        "capability": req.capability,
                        "contract": req.contract,
                        "provider": resolution.binding.provider,
                        "protocol": resolution.binding.protocol,
                        "connection": resolution.binding.connection,
                    })
                except Exception:
                    # If a required capability can't be resolved, record as unresolvable
                    tool_bindings.append({
                        "capability": req.capability,
                        "contract": req.contract,
                        "error": "unresolvable",
                    })
            connection["tool_bindings"] = tool_bindings

        return Binding(
            provider=f"{meta.namespace}/{meta.name}:{meta.version}",
            protocol="skill",
            connection=connection,
            trace_id=trace_id,
        )
