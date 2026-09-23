import pytest

from capmesh.models import (
    A2AInterface,
    CapabilityRef,
    Governance,
    Kind,
    Manifest,
    Metadata,
    Status,
    Visibility,
)
from capmesh.models.resolution import CallerContext, PolicyDecision
from capmesh.policy.engine import PolicyEngine, default_policy_engine
from capmesh.policy.rules import EnvironmentRule, StatusRule, VisibilityRule


def _manifest(
    visibility: Visibility = Visibility.PUBLIC,
    status: Status = Status.APPROVED,
    owner: str = "security-team",
    environment: list[str] | None = None,
) -> Manifest:
    return Manifest(
        metadata=Metadata(
            kind=Kind.AGENT,
            namespace="security",
            name="reviewer",
            version="1.0.0",
            owner=owner,
        ),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://agent.example"),
        governance=Governance(
            visibility=visibility,
            status=status,
            environment=environment or [],
        ),
    )


def _caller(
    identity: str = "user-1",
    organization: str | None = None,
    environment: str | None = None,
) -> CallerContext:
    return CallerContext(identity=identity, organization=organization, environment=environment)


# --- VisibilityRule ---


def test_visibility_public_allows_anyone():
    rule = VisibilityRule()
    decision = rule.evaluate(_caller(), _manifest(visibility=Visibility.PUBLIC), "test")
    assert decision.allowed is True


def test_visibility_org_allows_same_org():
    rule = VisibilityRule()
    decision = rule.evaluate(
        _caller(organization="security-team"),
        _manifest(visibility=Visibility.ORGANIZATION, owner="security-team"),
        "test",
    )
    assert decision.allowed is True


def test_visibility_org_denies_different_org():
    rule = VisibilityRule()
    decision = rule.evaluate(
        _caller(organization="other-team"),
        _manifest(visibility=Visibility.ORGANIZATION, owner="security-team"),
        "test",
    )
    assert decision.allowed is False
    assert "visibility" in decision.reason.lower()


def test_visibility_private_allows_owner():
    rule = VisibilityRule()
    decision = rule.evaluate(
        _caller(identity="security-team"),
        _manifest(visibility=Visibility.PRIVATE, owner="security-team"),
        "test",
    )
    assert decision.allowed is True


def test_visibility_private_denies_non_owner():
    rule = VisibilityRule()
    decision = rule.evaluate(
        _caller(identity="other-user"),
        _manifest(visibility=Visibility.PRIVATE, owner="security-team"),
        "test",
    )
    assert decision.allowed is False


# --- EnvironmentRule ---


def test_environment_allows_matching():
    rule = EnvironmentRule()
    decision = rule.evaluate(
        _caller(environment="production"),
        _manifest(environment=["production"]),
        "test",
    )
    assert decision.allowed is True


def test_environment_denies_mismatch():
    rule = EnvironmentRule()
    decision = rule.evaluate(
        _caller(environment="staging"),
        _manifest(environment=["production"]),
        "test",
    )
    assert decision.allowed is False
    assert "environment" in decision.reason.lower()


def test_environment_allows_when_provider_has_no_env():
    rule = EnvironmentRule()
    decision = rule.evaluate(
        _caller(environment="staging"),
        _manifest(environment=[]),
        "test",
    )
    assert decision.allowed is True


def test_environment_allows_when_caller_has_no_env():
    rule = EnvironmentRule()
    decision = rule.evaluate(
        _caller(environment=None),
        _manifest(environment=["production"]),
        "test",
    )
    assert decision.allowed is True


# --- StatusRule ---


def test_status_allows_approved():
    rule = StatusRule()
    decision = rule.evaluate(_caller(), _manifest(status=Status.APPROVED), "test")
    assert decision.allowed is True


def test_status_denies_revoked():
    rule = StatusRule()
    decision = rule.evaluate(_caller(), _manifest(status=Status.REVOKED), "test")
    assert decision.allowed is False
    assert "revoked" in decision.reason.lower()


def test_status_allows_deprecated():
    rule = StatusRule()
    decision = rule.evaluate(_caller(), _manifest(status=Status.DEPRECATED), "test")
    assert decision.allowed is True


# --- PolicyEngine ---


def test_engine_all_rules_pass():
    engine = default_policy_engine()
    decision = engine.evaluate(
        _caller(identity="user"),
        _manifest(visibility=Visibility.PUBLIC, status=Status.APPROVED),
        "test",
    )
    assert decision.allowed is True


def test_engine_first_deny_wins():
    engine = default_policy_engine()
    decision = engine.evaluate(
        _caller(identity="other"),
        _manifest(visibility=Visibility.PRIVATE, owner="owner"),
        "test",
    )
    assert decision.allowed is False
    assert "visibility" in decision.reason.lower()


def test_engine_empty_rules_allows():
    engine = PolicyEngine(rules=[])
    decision = engine.evaluate(_caller(), _manifest(), "test")
    assert decision.allowed is True
