from capmesh.models import (
    A2AInterface, MCPInterface, RESTInterface, SkillInterface,
    CapabilityRef, Governance, Kind, Manifest, Metadata, Status, Visibility,
)
from capmesh.adapters.a2a import A2ABindingAdapter
from capmesh.adapters.mcp import MCPBindingAdapter
from capmesh.adapters.rest import RESTBindingAdapter


def _manifest(interface) -> Manifest:
    return Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="ns", name="test", version="1.0.0", owner="o"),
        provides=[CapabilityRef(capability="test", contract="v1")],
        requires=[], interface=interface,
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )


# --- A2A ---

def test_a2a_supports():
    adapter = A2ABindingAdapter()
    assert adapter.supports(_manifest(A2AInterface(protocol="a2a", endpoint="https://a.example")))
    assert not adapter.supports(_manifest(MCPInterface(protocol="mcp", server="s")))


def test_a2a_bind():
    adapter = A2ABindingAdapter()
    m = _manifest(A2AInterface(protocol="a2a", endpoint="https://agent.example"))
    binding = adapter.bind(m, "res_test")
    assert binding.protocol == "a2a"
    assert binding.connection["endpoint"] == "https://agent.example"
    assert binding.provider == "ns/test:1.0.0"
    assert binding.trace_id == "res_test"


# --- MCP ---

def test_mcp_supports():
    adapter = MCPBindingAdapter()
    assert adapter.supports(_manifest(MCPInterface(protocol="mcp", server="gh")))
    assert not adapter.supports(_manifest(A2AInterface(protocol="a2a", endpoint="x")))


def test_mcp_bind():
    adapter = MCPBindingAdapter()
    m = _manifest(MCPInterface(protocol="mcp", server="github-mcp", tool_name="search"))
    binding = adapter.bind(m, "res_test")
    assert binding.protocol == "mcp"
    assert binding.connection["server"] == "github-mcp"
    assert binding.connection["tool_name"] == "search"


def test_mcp_bind_no_tool_name():
    adapter = MCPBindingAdapter()
    m = _manifest(MCPInterface(protocol="mcp", server="github-mcp"))
    binding = adapter.bind(m, "res_test")
    assert "tool_name" not in binding.connection


# --- REST ---

def test_rest_supports():
    adapter = RESTBindingAdapter()
    iface = RESTInterface(protocol="rest", endpoint="https://api.example", auth_type="bearer", request_mapping={}, response_mapping={})
    assert adapter.supports(_manifest(iface))
    assert not adapter.supports(_manifest(A2AInterface(protocol="a2a", endpoint="x")))


def test_rest_bind():
    adapter = RESTBindingAdapter()
    iface = RESTInterface(
        protocol="rest", endpoint="https://api.example/v1",
        auth_type="bearer",
        request_mapping={"input": "$.body"},
        response_mapping={"output": "$.result"},
    )
    binding = adapter.bind(_manifest(iface), "res_test")
    assert binding.protocol == "rest"
    assert binding.connection["endpoint"] == "https://api.example/v1"
    assert binding.connection["auth_type"] == "bearer"
    assert binding.connection["request_mapping"] == {"input": "$.body"}
