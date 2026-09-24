from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from packaging.version import InvalidVersion, Version

from capmesh.models.manifest import Manifest
from capmesh.models.resolution import (
    Binding,
    CallerContext,
    CandidateRecord,
    Resolution,
    ResolutionTrace,
    ResolveRequest,
)
from capmesh.adapters.registry import AdapterRegistry
from capmesh.policy.engine import PolicyEngine
from capmesh.registry.registry import Registry
from capmesh.resolver.discovery import CapabilityDiscovery
from capmesh.telemetry.traces import TraceStore


class ResolutionError(Exception):
    """Raised when no provider can be resolved."""


class Resolver:
    def __init__(
        self,
        registry: Registry,
        policy_engine: PolicyEngine,
        trace_store: TraceStore | None = None,
        adapter_registry: AdapterRegistry | None = None,
    ) -> None:
        self._registry = registry
        self._policy = policy_engine
        self._trace_store = trace_store
        self._adapter_registry = adapter_registry
        self._discovery = CapabilityDiscovery(registry)

    def need(self, query: str, caller: CallerContext | None = None,
             contract: str = "v1", version_constraint: str | None = None) -> Resolution:
        """Resolve a capability using natural language.

        Examples:
            resolver.need("read code from a repo")
            resolver.need("scan for security issues")
            resolver.need("notify the team on slack")
        """
        if caller is None:
            caller = CallerContext(identity="anonymous")

        # Try exact match first
        providers = self._registry.providers_for(query, contract)
        if providers:
            return self.resolve(ResolveRequest(
                capability=query, contract=contract,
                caller=caller, version_constraint=version_constraint,
            ))

        # Natural language discovery
        result = self._discovery.discover_one(query, contract)
        if result is None:
            raise ResolutionError(
                f"no_match: could not find a capability matching '{query}'"
            )

        return self.resolve(ResolveRequest(
            capability=result.capability, contract=contract,
            caller=caller, version_constraint=version_constraint,
        ))

    def discover(self, query: str, contract: str = "v1", limit: int = 5):
        """Search for capabilities matching a natural language query.
        Returns a list of DiscoveryResult objects."""
        return self._discovery.discover(query, contract, limit)

    def resolve(self, request: ResolveRequest) -> Resolution:
        start = time.monotonic()
        trace_id = f"res_{uuid.uuid4().hex[:12]}"
        candidates: list[CandidateRecord] = []

        # Step 1: Find candidates via registry.providers_for()
        provider_records = self._registry.providers_for(request.capability, request.contract)

        if not provider_records:
            trace = self._build_trace(
                trace_id, request, candidates, None, None,
                time.monotonic() - start, "no_candidates",
            )
            self._save_trace(trace)
            raise ResolutionError(
                f"no_candidates: no providers for {request.capability}/{request.contract}"
            )

        # Steps 2-6: Load full manifests, apply policy and version constraints
        # (Steps 2 & 4 — deprecated/revoked and contract — already handled by registry)
        approved: list[tuple[Manifest, str]] = []  # (manifest, protocol)

        for rec in provider_records:
            # Load full manifest for policy evaluation (registry only returns ArtifactRecords)
            manifest = self._registry.get(rec.namespace, rec.name, rec.version)
            if manifest is None:
                continue

            provider_key = f"{rec.namespace}/{rec.name}"

            # Step 3: Health checks (stub in V1 — all healthy)

            # Step 5: Apply policy via policy_engine.evaluate()
            decision = self._policy.evaluate(request.caller, manifest, request.capability)
            if not decision.allowed:
                candidates.append(CandidateRecord(
                    provider=provider_key,
                    version=rec.version,
                    passed=False,
                    rejection_reason=f"policy: {decision.reason}",
                ))
                continue

            # Step 6: Version constraints via packaging.version.Version
            if request.version_constraint:
                if not self._matches_constraint(rec.version, request.version_constraint):
                    candidates.append(CandidateRecord(
                        provider=provider_key,
                        version=rec.version,
                        passed=False,
                        rejection_reason=(
                            f"version_constraint: {rec.version} does not match "
                            f"{request.version_constraint}"
                        ),
                    ))
                    continue

            candidates.append(CandidateRecord(
                provider=provider_key,
                version=rec.version,
                passed=True,
            ))
            approved.append((manifest, manifest.interface.protocol))

        if not approved:
            trace = self._build_trace(
                trace_id, request, candidates, None, None,
                time.monotonic() - start, "all_filtered",
            )
            self._save_trace(trace)
            raise ResolutionError(
                f"all_filtered: all providers for {request.capability}/{request.contract} "
                "were filtered out"
            )

        # Step 7: Select highest semver
        approved.sort(
            key=lambda item: self._parse_version(item[0].metadata.version),
            reverse=True,
        )
        selected_manifest, selected_protocol = approved[0]
        meta = selected_manifest.metadata

        # Step 8: Build binding via adapter registry (or fallback for backward compat)
        if self._adapter_registry:
            binding = self._adapter_registry.bind(selected_manifest, trace_id)
        else:
            binding = Binding(
                provider=f"{meta.namespace}/{meta.name}:{meta.version}",
                protocol=selected_protocol,
                connection=self._extract_connection(selected_manifest),
                trace_id=trace_id,
            )

        elapsed = time.monotonic() - start

        # Step 9: Record trace
        trace = self._build_trace(
            trace_id, request, candidates,
            f"{meta.namespace}/{meta.name}:{meta.version}",
            selected_protocol, elapsed, "success",
        )
        self._save_trace(trace)

        return Resolution(
            provider_name=meta.name,
            provider_version=meta.version,
            provider_namespace=meta.namespace,
            binding=binding,
            trace=trace,
        )

    # --- helpers ---

    def _matches_constraint(self, version_str: str, constraint: str) -> bool:
        """Return True if version_str satisfies the comma-separated version constraint."""
        try:
            ver = Version(version_str)
        except InvalidVersion:
            return False

        for part in constraint.split(","):
            part = part.strip()
            if not part:
                continue
            if part.startswith(">="):
                if not (ver >= Version(part[2:])):
                    return False
            elif part.startswith(">"):
                if not (ver > Version(part[1:])):
                    return False
            elif part.startswith("<="):
                if not (ver <= Version(part[2:])):
                    return False
            elif part.startswith("<"):
                if not (ver < Version(part[1:])):
                    return False
            elif part.startswith("=="):
                if not (ver == Version(part[2:])):
                    return False
            elif part.startswith("!="):
                if not (ver != Version(part[2:])):
                    return False

        return True

    def _parse_version(self, version_str: str) -> Version:
        try:
            return Version(version_str)
        except InvalidVersion:
            return Version("0.0.0")

    def _extract_connection(self, manifest: Manifest) -> dict:
        iface = manifest.interface
        data: dict = {}
        if hasattr(iface, "endpoint"):
            data["endpoint"] = iface.endpoint
        if hasattr(iface, "server"):
            data["server"] = iface.server
        if hasattr(iface, "tool_name") and iface.tool_name is not None:
            data["tool_name"] = iface.tool_name
        if hasattr(iface, "instructions"):
            data["instructions"] = iface.instructions
        if hasattr(iface, "auth_type"):
            data["auth_type"] = iface.auth_type
        return data

    def _build_trace(
        self,
        trace_id: str,
        request: ResolveRequest,
        candidates: list[CandidateRecord],
        selected_provider: str | None,
        selected_protocol: str | None,
        elapsed: float,
        outcome: str,
    ) -> ResolutionTrace:
        return ResolutionTrace(
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc),
            requested_capability=request.capability,
            requested_contract=request.contract,
            caller=request.caller,
            candidates=candidates,
            selected_provider=selected_provider,
            selected_protocol=selected_protocol,
            resolution_ms=round(elapsed * 1000, 2),
            outcome=outcome,
        )

    def _save_trace(self, trace: ResolutionTrace) -> None:
        if self._trace_store is not None:
            self._trace_store.save_trace(trace)
