"""
CapMesh MCP Server — expose capability discovery as MCP tools.

Any agent that speaks MCP can discover capabilities natively.
Add this ONE MCP server and get access to the entire capability catalog.

Usage:
    # Standalone
    python -m capmesh.mcp.server

    # Or in code
    from capmesh.mcp import create_mcp_server
    mcp = create_mcp_server()
    mcp.run(transport="stdio")
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

import capmesh as cm


def create_mcp_server(root: str | None = None) -> FastMCP:
    """Create a CapMesh MCP server with discovery tools."""

    mcp = FastMCP(
        "CapMesh",
        instructions=(
            "CapMesh is a capability discovery service. Use these tools to find "
            "and resolve Agents, Skills, and MCP Tools by describing what you need. "
            "You can search with natural language, filter by kind (agent/tool/skill) "
            "and protocol (mcp/a2a/rest), and get connection bindings to call providers directly."
        ),
    )

    # Use env var or parameter for registry root
    _root = root or os.environ.get("CAPMESH_ROOT")
    mesh = cm.connect(root=_root)

    @mcp.tool()
    def resolve(
        query: str,
        kind: str = "",
        protocol: str = "",
        version: str = "",
    ) -> str:
        """Resolve a capability — find the best provider for what you need.

        Args:
            query: What you need, in natural language or exact capability ID.
                   Examples: "read a repository", "security scan", "security.code.review"
            kind: Filter by provider type — "agent", "tool", "skill", or empty for any.
            protocol: Filter by protocol — "mcp", "a2a", "rest", "skill", or empty for any.
            version: Version constraint — e.g. ">=2.0", ">=1.0,<3.0", or empty for latest.

        Returns:
            JSON with provider name, protocol, connection binding, and trace ID.
        """
        kwargs = {}
        if kind:
            kwargs["kind"] = kind
        if protocol:
            kwargs["protocol"] = protocol
        if version:
            kwargs["version"] = version

        try:
            result = mesh.need(query, **kwargs)
            return json.dumps({
                "provider": f"{result.provider_namespace}/{result.provider_name}:{result.provider_version}",
                "protocol": result.binding.protocol,
                "connection": result.binding.connection,
                "trace_id": result.trace.trace_id,
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def discover(query: str, limit: int = 5) -> str:
        """Explore what capabilities are available — ranked by relevance.

        Args:
            query: Search term — "security", "deploy", "notify", "database", etc.
            limit: Maximum results to return (default 5).

        Returns:
            JSON list of matching capabilities with scores and reasons.
        """
        results = mesh.discover(query, limit=limit)
        return json.dumps([
            {
                "capability": r.capability,
                "contract": r.contract,
                "score": r.score,
                "reason": r.reason,
            }
            for r in results
        ], indent=2)

    @mcp.tool()
    def search(query: str) -> str:
        """Search the registry by keyword — find providers by name, namespace, or capability.

        Args:
            query: Keyword to search for — "security", "github", "notification", etc.

        Returns:
            JSON list of matching providers with kind and protocol.
        """
        results = mesh.search(query)
        data = []
        for r in results:
            manifest = mesh._registry.get(r.namespace, r.name, r.version)
            protocol = manifest.interface.protocol if manifest else "?"
            data.append({
                "namespace": r.namespace,
                "name": r.name,
                "version": r.version,
                "kind": r.kind.value,
                "protocol": protocol,
            })
        return json.dumps(data, indent=2)

    @mcp.tool()
    def providers(capability: str, contract: str = "v1") -> str:
        """List all providers for a specific capability.

        Args:
            capability: Capability ID — e.g. "security.code.review", "repository.read"
            contract: Contract version (default "v1").

        Returns:
            JSON list of providers with kind, version, and protocol.
        """
        results = mesh.providers(capability, contract)
        data = []
        for r in results:
            manifest = mesh._registry.get(r.namespace, r.name, r.version)
            protocol = manifest.interface.protocol if manifest else "?"
            data.append({
                "namespace": r.namespace,
                "name": r.name,
                "version": r.version,
                "kind": r.kind.value,
                "protocol": protocol,
            })
        return json.dumps(data, indent=2)

    @mcp.tool()
    def register_provider(manifest_yaml: str) -> str:
        """Register a new provider from a YAML manifest.

        Args:
            manifest_yaml: The full YAML content of a CapMesh manifest.

        Returns:
            JSON with the digest of the registered provider.
        """
        from capmesh.models.serialization import manifest_from_yaml
        import tempfile

        try:
            # Validate by parsing
            manifest = manifest_from_yaml(manifest_yaml)

            # Write to temp file and register
            tmp = Path(tempfile.mkdtemp()) / "manifest.yaml"
            tmp.write_text(manifest_yaml, encoding="utf-8")
            digest = mesh.register(str(tmp))

            m = manifest.metadata
            return json.dumps({
                "registered": f"{m.namespace}/{m.name}:{m.version}",
                "kind": m.kind.value,
                "digest": digest,
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    def inspect(namespace: str, name: str, version: str) -> str:
        """Inspect a provider — get full manifest details.

        Args:
            namespace: Provider namespace — e.g. "security", "repository"
            name: Provider name — e.g. "crewai-reviewer", "github-reader"
            version: Provider version — e.g. "3.1.0", "1.0.0"

        Returns:
            JSON with full manifest details including capabilities, interface, and governance.
        """
        manifest = mesh._registry.get(namespace, name, version)
        if manifest is None:
            return json.dumps({"error": f"{namespace}/{name}:{version} not found"})
        return json.dumps(manifest.model_dump(mode="json"), indent=2, default=str)

    return mcp


# Allow running directly: python -m capmesh.mcp.server
if __name__ == "__main__":
    server = create_mcp_server()
    server.run(transport="stdio")
