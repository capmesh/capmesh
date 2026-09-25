"""Test CapMesh MCP server tools."""
import json
import tempfile
from pathlib import Path

import pytest

from capmesh.models import (
    A2AInterface, MCPInterface, CapabilityRef, Governance, Kind,
    Manifest, Metadata, Status, Visibility,
)
from capmesh.models.serialization import manifest_to_yaml


@pytest.fixture
def mcp_server(tmp_path):
    """Create a CapMesh MCP server with test providers."""
    from capmesh.mcp.server import create_mcp_server
    import capmesh

    # Register some providers first
    mesh = capmesh.connect(root=str(tmp_path))
    providers = [
        Manifest(
            metadata=Metadata(kind=Kind.TOOL, namespace="repo", name="github-reader",
                              version="1.0.0", owner="platform"),
            provides=[CapabilityRef(capability="repository.read", contract="v1",
                                    description="Read files from a repository")],
            requires=[],
            interface=MCPInterface(protocol="mcp", server="github-mcp", tool_name="read_file"),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ),
        Manifest(
            metadata=Metadata(kind=Kind.AGENT, namespace="security", name="reviewer",
                              version="3.1.0", owner="security-team"),
            provides=[CapabilityRef(capability="security.code.review", contract="v1",
                                    description="Review code for security vulnerabilities")],
            requires=[CapabilityRef(capability="repository.read", contract="v1")],
            interface=A2AInterface(protocol="a2a", endpoint="https://reviewer.example.com"),
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ),
    ]
    tmp_manifests = Path(tempfile.mkdtemp())
    for p in providers:
        path = tmp_manifests / f"{p.metadata.name}.yaml"
        path.write_text(manifest_to_yaml(p))
        mesh.register(str(path))

    # Create MCP server pointing at same registry
    server = create_mcp_server(root=str(tmp_path))
    return server


def test_mcp_server_creates(mcp_server):
    assert mcp_server is not None


def test_resolve_tool(mcp_server):
    # Access the tool function directly
    tools = mcp_server._tool_manager._tools
    assert "resolve" in tools

    # Call it
    resolve_fn = tools["resolve"].fn
    result_str = resolve_fn(query="repository.read", kind="", protocol="", version="")
    result = json.loads(result_str)
    assert "provider" in result
    assert "github-reader" in result["provider"]
    assert result["protocol"] == "mcp"
    assert result["connection"]["server"] == "github-mcp"


def test_resolve_with_kind_filter(mcp_server):
    tools = mcp_server._tool_manager._tools
    resolve_fn = tools["resolve"].fn

    result = json.loads(resolve_fn(query="security code review", kind="agent", protocol="", version=""))
    assert "reviewer" in result["provider"]
    assert result["protocol"] == "a2a"


def test_discover_tool(mcp_server):
    tools = mcp_server._tool_manager._tools
    discover_fn = tools["discover"].fn

    result = json.loads(discover_fn(query="security", limit=5))
    assert len(result) > 0
    assert any(r["capability"] == "security.code.review" for r in result)


def test_search_tool(mcp_server):
    tools = mcp_server._tool_manager._tools
    search_fn = tools["search"].fn

    result = json.loads(search_fn(query="github"))
    assert len(result) > 0
    assert result[0]["name"] == "github-reader"


def test_providers_tool(mcp_server):
    tools = mcp_server._tool_manager._tools
    providers_fn = tools["providers"].fn

    result = json.loads(providers_fn(capability="security.code.review", contract="v1"))
    assert len(result) == 1
    assert result[0]["name"] == "reviewer"


def test_inspect_tool(mcp_server):
    tools = mcp_server._tool_manager._tools
    inspect_fn = tools["inspect"].fn

    result = json.loads(inspect_fn(namespace="repo", name="github-reader", version="1.0.0"))
    assert result["metadata"]["name"] == "github-reader"
    assert result["interface"]["protocol"] == "mcp"


def test_inspect_not_found(mcp_server):
    tools = mcp_server._tool_manager._tools
    inspect_fn = tools["inspect"].fn

    result = json.loads(inspect_fn(namespace="nope", name="nope", version="1.0.0"))
    assert "error" in result


def test_register_tool(mcp_server):
    tools = mcp_server._tool_manager._tools
    register_fn = tools["register_provider"].fn

    manifest_yaml = manifest_to_yaml(Manifest(
        metadata=Metadata(kind=Kind.TOOL, namespace="new", name="new-tool",
                          version="1.0.0", owner="test"),
        provides=[CapabilityRef(capability="new.capability", contract="v1")],
        requires=[],
        interface=MCPInterface(protocol="mcp", server="new-mcp"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))

    result = json.loads(register_fn(manifest_yaml=manifest_yaml))
    assert "registered" in result
    assert result["registered"] == "new/new-tool:1.0.0"
    assert "digest" in result
