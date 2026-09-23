from __future__ import annotations

from typing import Protocol

from capmesh.models.enums import Status, Visibility
from capmesh.models.manifest import Manifest
from capmesh.models.resolution import CallerContext, PolicyDecision


class PolicyRule(Protocol):
    def evaluate(self, caller: CallerContext, provider: Manifest, capability: str) -> PolicyDecision: ...


class VisibilityRule:
    def evaluate(self, caller: CallerContext, provider: Manifest, capability: str) -> PolicyDecision:
        vis = provider.governance.visibility
        owner = provider.metadata.owner

        if vis == Visibility.PUBLIC:
            return PolicyDecision(allowed=True, reason="public visibility")

        if vis == Visibility.ORGANIZATION:
            if caller.organization == owner:
                return PolicyDecision(allowed=True, reason="same organization")
            return PolicyDecision(
                allowed=False,
                reason=f"Visibility: organization-only, caller org '{caller.organization}' != owner '{owner}'",
            )

        if vis == Visibility.PRIVATE:
            if caller.identity == owner:
                return PolicyDecision(allowed=True, reason="owner access")
            return PolicyDecision(
                allowed=False,
                reason=f"Visibility: private, caller '{caller.identity}' is not owner '{owner}'",
            )

        return PolicyDecision(allowed=True, reason="unknown visibility, allowing")


class EnvironmentRule:
    def evaluate(self, caller: CallerContext, provider: Manifest, capability: str) -> PolicyDecision:
        provider_envs = provider.governance.environment

        if not provider_envs:
            return PolicyDecision(allowed=True, reason="provider has no environment restrictions")

        if caller.environment is None:
            return PolicyDecision(allowed=True, reason="caller has no environment context")

        if caller.environment in provider_envs:
            return PolicyDecision(allowed=True, reason=f"environment '{caller.environment}' matches")

        return PolicyDecision(
            allowed=False,
            reason=f"Environment: caller '{caller.environment}' not in provider environments {provider_envs}",
        )


class StatusRule:
    def evaluate(self, caller: CallerContext, provider: Manifest, capability: str) -> PolicyDecision:
        if provider.governance.status == Status.REVOKED:
            return PolicyDecision(allowed=False, reason="provider is revoked")
        return PolicyDecision(allowed=True, reason=f"status is {provider.governance.status.value}")
