from __future__ import annotations

from pydantic import BaseModel, Field

from capmesh.models.enums import Kind, Visibility, Status
from capmesh.models.interfaces import Interface


class CapabilityRef(BaseModel):
    capability: str
    contract: str
    description: str = ""


class Governance(BaseModel):
    visibility: Visibility
    status: Status
    environment: list[str] = Field(default_factory=list)
    labels: dict[str, str] = Field(default_factory=dict)


class HealthCheck(BaseModel):
    enabled: bool
    endpoint: str | None = None
    interval_seconds: int = 60


class Metadata(BaseModel):
    api_version: str = "capmesh.io/v1alpha1"
    kind: Kind
    namespace: str
    name: str
    version: str
    owner: str
    digest: str | None = None


class Manifest(BaseModel):
    metadata: Metadata
    provides: list[CapabilityRef] = Field(default_factory=list)
    requires: list[CapabilityRef] = Field(default_factory=list)
    interface: Interface
    governance: Governance
