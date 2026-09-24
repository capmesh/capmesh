"""OpenTelemetry instrumentation for CapMesh resolution."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from capmesh.resolver.resolver import Resolver


class OtelInstrumentor:
    """Wraps Resolver.resolve() to emit OTEL spans.

    Usage:
        from capmesh.telemetry.otel import OtelInstrumentor
        instrumentor = OtelInstrumentor()
        instrumentor.instrument(resolver)
    """

    def __init__(self, tracer_provider=None) -> None:
        self._tracer = None
        try:
            from opentelemetry import trace
            if tracer_provider:
                self._tracer = tracer_provider.get_tracer("capmesh", "0.1.0")
            else:
                self._tracer = trace.get_tracer("capmesh", "0.1.0")
        except ImportError:
            pass  # opentelemetry not installed — no-op

    def instrument(self, resolver: "Resolver") -> None:
        if self._tracer is None:
            return  # no-op

        original_resolve = resolver.resolve
        tracer = self._tracer

        def instrumented_resolve(request):
            with tracer.start_as_current_span("capmesh.resolve") as span:
                span.set_attribute("capmesh.capability", request.capability)
                span.set_attribute("capmesh.contract", request.contract)
                span.set_attribute("capmesh.caller", request.caller.identity)
                span.set_attribute("capmesh.environment", request.caller.environment or "")

                if request.version_constraint:
                    span.set_attribute("capmesh.version_constraint", request.version_constraint)

                # Check if this will be a cache hit
                cached = resolver._cache.get(
                    request.capability, request.contract,
                    request.caller.identity, request.caller.environment,
                    request.version_constraint,
                )
                span.set_attribute("capmesh.cache_hit", cached is not None)

                try:
                    result = original_resolve(request)
                    span.set_attribute(
                        "capmesh.provider",
                        f"{result.provider_namespace}/{result.provider_name}:{result.provider_version}",
                    )
                    span.set_attribute("capmesh.protocol", result.binding.protocol)
                    span.set_attribute("capmesh.outcome", result.trace.outcome)
                    span.set_attribute("capmesh.candidates", len(result.trace.candidates))
                    span.set_attribute("capmesh.resolution_ms", result.trace.resolution_ms)
                    span.set_attribute("capmesh.trace_id", result.trace.trace_id)
                    return result
                except Exception as e:
                    span.set_attribute("capmesh.outcome", "error")
                    span.set_attribute("capmesh.error", str(e))
                    span.record_exception(e)
                    raise

        resolver.resolve = instrumented_resolve
