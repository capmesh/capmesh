from __future__ import annotations

from capmesh.models.manifest import Manifest
from capmesh.models.resolution import CallerContext, PolicyDecision
from capmesh.policy.rules import EnvironmentRule, PolicyRule, StatusRule, VisibilityRule


class PolicyEngine:
    def __init__(self, rules: list[PolicyRule] | None = None) -> None:
        self._rules: list[PolicyRule] = rules if rules is not None else []

    def evaluate(self, caller: CallerContext, provider: Manifest, capability: str) -> PolicyDecision:
        for rule in self._rules:
            decision = rule.evaluate(caller, provider, capability)
            if not decision.allowed:
                return decision
        return PolicyDecision(allowed=True, reason="all rules passed")


def default_policy_engine() -> PolicyEngine:
    return PolicyEngine(rules=[StatusRule(), VisibilityRule(), EnvironmentRule()])
