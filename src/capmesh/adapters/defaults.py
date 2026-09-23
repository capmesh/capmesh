from __future__ import annotations

from typing import TYPE_CHECKING

from capmesh.adapters.a2a import A2ABindingAdapter
from capmesh.adapters.mcp import MCPBindingAdapter
from capmesh.adapters.registry import AdapterRegistry
from capmesh.adapters.rest import RESTBindingAdapter
from capmesh.adapters.skills import SkillBindingAdapter

if TYPE_CHECKING:
    from capmesh.resolver.resolver import Resolver


def default_adapter_registry(resolver: Resolver | None = None) -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(A2ABindingAdapter())
    registry.register(MCPBindingAdapter())
    registry.register(SkillBindingAdapter(resolver=resolver))
    registry.register(RESTBindingAdapter())
    return registry
