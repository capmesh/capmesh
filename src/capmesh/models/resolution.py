from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CallerContext(BaseModel):
    identity: str
    organization: str | None = None
    environment: str | None = None
    roles: list[str] = Field(default_factory=list)


class ResolveRequest(BaseModel):
    capability: str
    contract: str
    caller: CallerContext
    version_constraint: str | None = None


class CandidateRecord(BaseModel):
    provider: str
    version: str
    passed: bool
    rejection_reason: str | None = None


class ResolutionTrace(BaseModel):
    trace_id: str
    timestamp: datetime
    requested_capability: str
    requested_contract: str
    caller: CallerContext
    candidates: list[CandidateRecord] = Field(default_factory=list)
    selected_provider: str | None = None
    selected_protocol: str | None = None
    resolution_ms: float = 0.0
    outcome: str = "success"


class Binding(BaseModel):
    provider: str
    protocol: str
    connection: dict = Field(default_factory=dict)
    trace_id: str


class PolicyDecision(BaseModel):
    allowed: bool
    reason: str


class Resolution(BaseModel):
    provider_name: str
    provider_version: str
    provider_namespace: str
    binding: Binding
    trace: ResolutionTrace
