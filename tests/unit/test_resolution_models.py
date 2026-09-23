from datetime import datetime, timezone

from capmesh.models.resolution import (
    Binding,
    CallerContext,
    CandidateRecord,
    PolicyDecision,
    Resolution,
    ResolutionTrace,
    ResolveRequest,
)
from capmesh.registry.storage import ArtifactRecord
from capmesh.models.enums import Kind


def test_caller_context():
    ctx = CallerContext(identity="orchestrator-1", environment="production")
    assert ctx.identity == "orchestrator-1"
    assert ctx.organization is None
    assert ctx.roles == []


def test_caller_context_full():
    ctx = CallerContext(
        identity="orchestrator-1",
        organization="security-team",
        environment="production",
        roles=["admin"],
    )
    assert ctx.organization == "security-team"
    assert ctx.roles == ["admin"]


def test_resolve_request():
    req = ResolveRequest(
        capability="security.code.review",
        contract="v1",
        caller=CallerContext(identity="test"),
    )
    assert req.capability == "security.code.review"
    assert req.version_constraint is None


def test_resolve_request_with_constraint():
    req = ResolveRequest(
        capability="security.code.review",
        contract="v1",
        caller=CallerContext(identity="test"),
        version_constraint=">=2.0",
    )
    assert req.version_constraint == ">=2.0"


def test_candidate_record():
    c = CandidateRecord(provider="security/reviewer", version="2.4.0", passed=True)
    assert c.passed is True
    assert c.rejection_reason is None


def test_candidate_record_rejected():
    c = CandidateRecord(
        provider="security/reviewer",
        version="3.0.0",
        passed=False,
        rejection_reason="contract_mismatch",
    )
    assert c.passed is False
    assert c.rejection_reason == "contract_mismatch"


def test_resolution_trace():
    trace = ResolutionTrace(
        trace_id="res_abc123def456",
        timestamp=datetime.now(timezone.utc),
        requested_capability="security.code.review",
        requested_contract="v1",
        caller=CallerContext(identity="test"),
        candidates=[
            CandidateRecord(provider="security/reviewer", version="2.4.0", passed=True),
        ],
        selected_provider="security/reviewer:2.4.0",
        selected_protocol="a2a",
        resolution_ms=34.0,
        outcome="success",
    )
    assert trace.trace_id.startswith("res_")
    assert trace.outcome == "success"


def test_resolution_trace_no_candidates():
    trace = ResolutionTrace(
        trace_id="res_abc123def456",
        timestamp=datetime.now(timezone.utc),
        requested_capability="nonexistent",
        requested_contract="v1",
        caller=CallerContext(identity="test"),
        candidates=[],
        selected_provider=None,
        selected_protocol=None,
        resolution_ms=1.0,
        outcome="no_candidates",
    )
    assert trace.outcome == "no_candidates"
    assert trace.selected_provider is None


def test_binding():
    b = Binding(
        provider="security/reviewer:2.4.0",
        protocol="a2a",
        connection={"endpoint": "https://agent.example"},
        trace_id="res_abc123def456",
    )
    assert b.protocol == "a2a"
    assert b.connection["endpoint"] == "https://agent.example"


def test_policy_decision_allowed():
    d = PolicyDecision(allowed=True, reason="all rules passed")
    assert d.allowed is True


def test_policy_decision_denied():
    d = PolicyDecision(allowed=False, reason="visibility: private")
    assert d.allowed is False
