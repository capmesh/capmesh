"""CapMesh — service discovery for the agentic world."""

__version__ = "0.1.0"

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from capmesh.resolver.resolver import Resolver


class CapMesh:
    """Simple interface to CapMesh. One import, one connect, done.

    Usage:
        import capmesh

        mesh = capmesh.connect()

        # Natural language
        result = mesh.need("scan for security issues")
        print(result.binding.connection)

        # Exact capability
        result = mesh.resolve("security.code.review")

        # Explore what's available
        results = mesh.discover("security")

        # With caller context
        result = mesh.need("read a repo", identity="my-agent", environment="production")
    """

    def __init__(self, resolver: "Resolver", registry) -> None:
        self._resolver = resolver
        self._registry = registry

    def need(self, query: str, protocol: str | None = None,
             identity: str = "default", environment: str | None = None,
             version: str | None = None):
        """Find a capability using natural language.

        Args:
            query: What you need, in plain English ("read a repo", "scan for security issues")
            protocol: Filter by protocol — "mcp", "a2a", "rest", "skill", or None for any
            identity: Who's asking (for policy enforcement)
            environment: Where you're running ("production", "staging")
            version: Version constraint (">=2.0", ">=1.0,<3.0")

        Returns:
            Resolution with .binding.protocol, .binding.connection, .provider_name, etc.

        Examples:
            mesh.need("security scan")                           # any protocol
            mesh.need("security scan", protocol="a2a")           # only A2A agents
            mesh.need("read a repo", protocol="mcp")             # only MCP tools
            mesh.need("analyze code", protocol="rest")           # only REST APIs
            mesh.need("review code", protocol="skill")           # only Skills
        """
        from capmesh.models.resolution import CallerContext
        caller = CallerContext(identity=identity, environment=environment)
        result = self._resolver.need(query, caller=caller, version_constraint=version)

        if protocol and result.binding.protocol != protocol:
            # First match wasn't the right protocol — search through all providers
            return self._resolve_with_protocol(
                result.trace.requested_capability, "v1", protocol, caller, version
            )

        return result

    def resolve(self, capability: str, contract: str = "v1",
                protocol: str | None = None,
                identity: str = "default", environment: str | None = None,
                version: str | None = None):
        """Resolve an exact capability ID.

        Args:
            capability: Capability ID ("security.code.review", "repository.read")
            contract: Contract version (default "v1")
            protocol: Filter by protocol — "mcp", "a2a", "rest", "skill", or None for any
            identity: Who's asking
            environment: Where you're running
            version: Version constraint

        Returns:
            Resolution with .binding.protocol, .binding.connection, .provider_name, etc.

        Examples:
            mesh.resolve("security.code.review")                          # any protocol
            mesh.resolve("security.code.review", protocol="a2a")          # only A2A agents
            mesh.resolve("security.code.review", protocol="skill")        # only Skills
            mesh.resolve("repository.read", protocol="mcp")               # only MCP tools
        """
        from capmesh.models.resolution import CallerContext, ResolveRequest
        caller = CallerContext(identity=identity, environment=environment)

        if protocol is None:
            return self._resolver.resolve(ResolveRequest(
                capability=capability, contract=contract,
                caller=caller, version_constraint=version,
            ))

        return self._resolve_with_protocol(capability, contract, protocol, caller, version)

    def _resolve_with_protocol(self, capability, contract, protocol, caller, version):
        """Resolve filtering by protocol. Iterates providers to find matching protocol."""
        from capmesh.resolver import ResolutionError

        providers = self._registry.providers_for(capability, contract)
        for p in providers:
            manifest = self._registry.get(p.namespace, p.name, p.version)
            if manifest and manifest.interface.protocol == protocol:
                from capmesh.models.resolution import ResolveRequest
                return self._resolver.resolve(ResolveRequest(
                    capability=capability, contract=contract,
                    caller=caller,
                    version_constraint=f"=={p.version}",
                ))
        raise ResolutionError(
            f"no_match: no {protocol} provider for {capability}/{contract}"
        )

    def discover(self, query: str, limit: int = 5):
        """Explore what capabilities are available.

        Args:
            query: Search term ("security", "deploy", "notify")
            limit: Max results

        Returns:
            List of matches with .capability, .score, .reason
        """
        return self._resolver.discover(query, limit=limit)

    def register(self, manifest_path: str):
        """Register a provider from a YAML manifest file.

        Args:
            manifest_path: Path to manifest.yaml
        """
        from capmesh.models.serialization import manifest_from_yaml
        yaml_str = Path(manifest_path).read_text(encoding="utf-8")
        manifest = manifest_from_yaml(yaml_str)
        return self._registry.register(manifest)

    def search(self, query: str):
        """Search the registry by keyword."""
        return self._registry.search(query)

    def providers(self, capability: str, contract: str = "v1"):
        """List all providers for a capability."""
        return self._registry.providers_for(capability, contract)

    @property
    def cache_stats(self) -> dict:
        """Resolution cache stats: hits, misses, size."""
        return self._resolver.cache_stats

    def __repr__(self) -> str:
        count = len(self._registry.list())
        return f"<CapMesh: {count} providers registered>"


def connect(root: str | None = None, server: str | None = None) -> CapMesh:
    """Connect to CapMesh. One line to get started.

    Args:
        root: Local registry path (default: ~/.capmesh/)
        server: Remote server URL (future: connects to CapMesh server)

    Returns:
        CapMesh instance ready to use

    Usage:
        import capmesh
        mesh = capmesh.connect()
        result = mesh.need("scan for security issues")
    """
    import sqlite3
    from capmesh.adapters.defaults import default_adapter_registry
    from capmesh.policy import default_policy_engine
    from capmesh.registry import Registry
    from capmesh.resolver import Resolver
    from capmesh.telemetry import TraceStore

    registry_root = Path(root) if root else None
    registry = Registry(root=registry_root)

    policy = default_policy_engine()

    storage_root = registry_root or Path.home() / ".capmesh"
    db = sqlite3.connect(str(storage_root / "traces.db"))
    db.row_factory = sqlite3.Row
    trace_store = TraceStore(db)
    trace_store.init_schema()

    resolver = Resolver(
        registry=registry,
        policy_engine=policy,
        trace_store=trace_store,
    )
    adapter_reg = default_adapter_registry(resolver=resolver)
    resolver._adapter_registry = adapter_reg

    return CapMesh(resolver=resolver, registry=registry)
