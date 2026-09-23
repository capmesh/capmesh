import pytest
from capmesh.models import (
    A2AInterface, MCPInterface, SkillInterface, RESTInterface,
    CapabilityRef, Governance, Kind, Manifest, Metadata, Status, Visibility,
)
from capmesh.adapters.registry import AdapterRegistry
from capmesh.adapters.base import BindingAdapter
from capmesh.models.resolution import Binding


def _agent_manifest() -> Manifest:
    return Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="sec", name="rev", version="1.0.0", owner="o"),
        provides=[CapabilityRef(capability="test", contract="v1")],
        requires=[], interface=A2AInterface(protocol="a2a", endpoint="https://a.example"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )


def _tool_manifest() -> Manifest:
    return Manifest(
        metadata=Metadata(kind=Kind.TOOL, namespace="repo", name="gh", version="1.0.0", owner="o"),
        provides=[CapabilityRef(capability="test", contract="v1")],
        requires=[], interface=MCPInterface(protocol="mcp", server="gh-mcp"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )


class StubAdapter:
    def __init__(self, protocol: str):
        self._protocol = protocol

    def supports(self, manifest: Manifest) -> bool:
        return manifest.interface.protocol == self._protocol

    def bind(self, manifest: Manifest, trace_id: str) -> Binding:
        return Binding(provider="test", protocol=self._protocol, connection={}, trace_id=trace_id)


def test_register_and_get_adapter():
    reg = AdapterRegistry()
    adapter = StubAdapter("a2a")
    reg.register(adapter)
    found = reg.get_adapter(_agent_manifest())
    assert found is adapter


def test_get_adapter_returns_correct_one():
    reg = AdapterRegistry()
    a2a = StubAdapter("a2a")
    mcp = StubAdapter("mcp")
    reg.register(a2a)
    reg.register(mcp)
    assert reg.get_adapter(_agent_manifest()) is a2a
    assert reg.get_adapter(_tool_manifest()) is mcp


def test_get_adapter_raises_for_unknown():
    reg = AdapterRegistry()
    with pytest.raises(ValueError, match="No adapter"):
        reg.get_adapter(_agent_manifest())


def test_bind_delegates_to_adapter():
    reg = AdapterRegistry()
    reg.register(StubAdapter("a2a"))
    binding = reg.bind(_agent_manifest(), "res_test123")
    assert binding.protocol == "a2a"
    assert binding.trace_id == "res_test123"
