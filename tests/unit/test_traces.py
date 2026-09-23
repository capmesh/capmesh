import sqlite3
from datetime import datetime, timezone

import pytest

from capmesh.models.resolution import CallerContext, CandidateRecord, ResolutionTrace
from capmesh.telemetry.traces import TraceStore


@pytest.fixture
def trace_store(tmp_path) -> TraceStore:
    db = sqlite3.connect(str(tmp_path / "test.db"))
    db.row_factory = sqlite3.Row
    store = TraceStore(db)
    store.init_schema()
    return store


def _sample_trace(trace_id: str = "res_abc123def456") -> ResolutionTrace:
    return ResolutionTrace(
        trace_id=trace_id,
        timestamp=datetime.now(timezone.utc),
        requested_capability="security.code.review",
        requested_contract="v1",
        caller=CallerContext(identity="orchestrator-1", environment="production"),
        candidates=[
            CandidateRecord(provider="security/reviewer", version="2.4.0", passed=True),
            CandidateRecord(
                provider="security/reviewer",
                version="3.0.0",
                passed=False,
                rejection_reason="contract_mismatch",
            ),
        ],
        selected_provider="security/reviewer:2.4.0",
        selected_protocol="a2a",
        resolution_ms=34.0,
        outcome="success",
    )


def test_save_and_get_trace(trace_store: TraceStore):
    trace = _sample_trace()
    trace_store.save_trace(trace)

    loaded = trace_store.get_trace("res_abc123def456")
    assert loaded is not None
    assert loaded.trace_id == "res_abc123def456"
    assert loaded.requested_capability == "security.code.review"
    assert loaded.outcome == "success"
    assert loaded.selected_provider == "security/reviewer:2.4.0"
    assert len(loaded.candidates) == 2


def test_get_nonexistent_trace(trace_store: TraceStore):
    assert trace_store.get_trace("res_nonexistent") is None


def test_list_traces(trace_store: TraceStore):
    trace_store.save_trace(_sample_trace("res_aaa"))
    trace_store.save_trace(_sample_trace("res_bbb"))
    trace_store.save_trace(_sample_trace("res_ccc"))

    traces = trace_store.list_traces(limit=2)
    assert len(traces) == 2


def test_list_traces_returns_newest_first(trace_store: TraceStore):
    trace_store.save_trace(_sample_trace("res_first"))
    trace_store.save_trace(_sample_trace("res_second"))

    traces = trace_store.list_traces(limit=10)
    assert traces[0].trace_id == "res_second"
