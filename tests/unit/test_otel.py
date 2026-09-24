import pytest


def test_otel_instrumentor_exists():
    from capmesh.telemetry.otel import OtelInstrumentor
    assert OtelInstrumentor is not None


def test_otel_instrumentor_wraps_resolve(tmp_path):
    from capmesh.telemetry.otel import OtelInstrumentor
    from capmesh.registry import Registry
    from capmesh.resolver import Resolver
    from capmesh.policy import default_policy_engine
    from capmesh.models import (
        A2AInterface, CapabilityRef, Governance, Kind,
        Manifest, Metadata, Status, Visibility,
    )
    from capmesh.models.resolution import CallerContext, ResolveRequest

    registry = Registry(root=tmp_path)
    resolver = Resolver(registry=registry, policy_engine=default_policy_engine())

    # Instrument
    instrumentor = OtelInstrumentor()
    instrumentor.instrument(resolver)

    # Register a provider
    registry.register(Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="ns", name="test",
                          version="1.0.0", owner="o"),
        provides=[CapabilityRef(capability="test.cap", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://test.example"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))

    # Resolve — should not error even with OTEL instrumented
    result = resolver.resolve(ResolveRequest(
        capability="test.cap", contract="v1",
        caller=CallerContext(identity="test"),
    ))
    assert result.provider_name == "test"


def test_otel_noop_when_not_installed(tmp_path, monkeypatch):
    """If opentelemetry is not available, instrumentor should be a no-op."""
    from capmesh.telemetry.otel import OtelInstrumentor

    instrumentor = OtelInstrumentor()
    # Should not raise even if tracing backend is not configured
    from capmesh.registry import Registry
    from capmesh.resolver import Resolver
    from capmesh.policy import default_policy_engine

    registry = Registry(root=tmp_path)
    resolver = Resolver(registry=registry, policy_engine=default_policy_engine())
    instrumentor.instrument(resolver)


def test_otel_span_attributes(tmp_path):
    """Verify span attributes are set correctly."""
    from capmesh.telemetry.otel import OtelInstrumentor
    from capmesh.registry import Registry
    from capmesh.resolver import Resolver
    from capmesh.policy import default_policy_engine
    from capmesh.models import (
        A2AInterface, CapabilityRef, Governance, Kind,
        Manifest, Metadata, Status, Visibility,
    )
    from capmesh.models.resolution import CallerContext, ResolveRequest
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    # Setup in-memory exporter to capture spans
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    registry = Registry(root=tmp_path)
    resolver = Resolver(registry=registry, policy_engine=default_policy_engine())

    instrumentor = OtelInstrumentor(tracer_provider=provider)
    instrumentor.instrument(resolver)

    registry.register(Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="sec", name="reviewer",
                          version="2.0.0", owner="team"),
        provides=[CapabilityRef(capability="security.scan", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://scan.example"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    ))

    resolver.resolve(ResolveRequest(
        capability="security.scan", contract="v1",
        caller=CallerContext(identity="ci-pipeline", environment="production"),
    ))

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "capmesh.resolve"
    attrs = dict(span.attributes)
    assert attrs["capmesh.capability"] == "security.scan"
    assert attrs["capmesh.contract"] == "v1"
    assert attrs["capmesh.provider"] == "sec/reviewer:2.0.0"
    assert attrs["capmesh.protocol"] == "a2a"
    assert attrs["capmesh.outcome"] == "success"
    assert attrs["capmesh.caller"] == "ci-pipeline"
    assert attrs["capmesh.environment"] == "production"
    assert attrs["capmesh.candidates"] == 1
    assert "capmesh.resolution_ms" in attrs


def test_connect_telemetry_param(tmp_path):
    """connect(telemetry=True) should work without errors."""
    import capmesh
    mesh = capmesh.connect(root=str(tmp_path), telemetry=True)
    assert mesh is not None
