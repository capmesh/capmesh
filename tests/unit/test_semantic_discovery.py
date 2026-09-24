import pytest
import tempfile
from pathlib import Path

from capmesh.models import (
    A2AInterface, MCPInterface, CapabilityRef, Governance, Kind,
    Manifest, Metadata, Status, Visibility,
)
from capmesh.registry import Registry
from capmesh.resolver.discovery import CapabilityDiscovery


def _register_providers(registry):
    providers = [
        ("repository.read", "Read files and code from a git repository", "mcp"),
        ("security.code.review", "Review code for security vulnerabilities and OWASP issues", "a2a"),
        ("security.scan", "Scan for CVEs and dependency vulnerabilities", "a2a"),
        ("notification.send", "Send notifications and alerts to Slack or Teams", "rest"),
        ("performance.analyze", "Analyze application performance and latency", "a2a"),
        ("deploy.execute", "Deploy applications to staging or production", "a2a"),
        ("data.query", "Query databases and run SQL", "mcp"),
        ("test.generate", "Generate unit tests for code", "a2a"),
        ("documentation.generate", "Generate docs and READMEs from code", "a2a"),
        ("issue.create", "Create bug tickets in project tracker", "rest"),
    ]
    for cap, desc, proto in providers:
        ns = cap.split(".")[0]
        name = cap.replace(".", "-")
        if proto == "mcp":
            iface = MCPInterface(protocol="mcp", server=f"{name}-mcp")
        else:
            iface = A2AInterface(protocol="a2a", endpoint=f"https://{name}.example.com")
        registry.register(Manifest(
            metadata=Metadata(kind=Kind.TOOL if proto == "mcp" else Kind.AGENT,
                              namespace=ns, name=name, version="1.0.0", owner="team"),
            provides=[CapabilityRef(capability=cap, contract="v1", description=desc)],
            requires=[],
            interface=iface,
            governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        ))


@pytest.fixture
def discovery_with_embeddings(tmp_path):
    from capmesh.resolver.embeddings import EmbeddingEngine
    engine = EmbeddingEngine()
    if not engine.available:
        pytest.skip("sentence-transformers not installed")
    registry = Registry(root=tmp_path)
    _register_providers(registry)
    return CapabilityDiscovery(registry, embedding_engine=engine)


def test_semantic_finds_related(discovery_with_embeddings):
    """Semantic search should find related capabilities even with different words."""
    results = discovery_with_embeddings.discover("check code for bugs")
    caps = [r.capability for r in results]
    assert "security.code.review" in caps or "security.scan" in caps


def test_semantic_ranks_better_than_keyword(discovery_with_embeddings):
    """'make sure our APIs are fast' should find performance.analyze."""
    results = discovery_with_embeddings.discover("make sure our APIs are fast")
    caps = [r.capability for r in results]
    assert "performance.analyze" in caps


def test_semantic_finds_with_synonyms(discovery_with_embeddings):
    """'alert the team about an incident' should find notification.send."""
    results = discovery_with_embeddings.discover("alert the team about an incident")
    caps = [r.capability for r in results]
    assert "notification.send" in caps


def test_semantic_scores_are_reasonable(discovery_with_embeddings):
    results = discovery_with_embeddings.discover("security vulnerability scan")
    assert len(results) > 0
    assert results[0].score > 0.3
    assert results[0].score <= 1.0


def test_fallback_to_keyword_without_embeddings(tmp_path):
    """Without embedding engine, should fall back to keyword matching."""
    registry = Registry(root=tmp_path)
    _register_providers(registry)
    discovery = CapabilityDiscovery(registry, embedding_engine=None)
    results = discovery.discover("security")
    assert len(results) > 0  # keyword matching still works
