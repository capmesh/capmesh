# CapMesh V1 Design Specification

> Dynamic capability discovery, resolution and binding for Agents, Skills and Tools.
> "Service discovery for the agentic world."

**Date:** 2026-09-23
**Version:** v0.1
**License:** Apache 2.0

---

## 1. Architecture Overview

CapMesh is a single Python package (`capmesh`) implementing a framework-agnostic capability control plane for heterogeneous agentic systems. A consumer expresses WHAT it needs as a capability; CapMesh discovers providers, applies compatibility and policy, selects an approved provider, and returns the binding needed to use it.

CapMesh composes A2A, MCP/API and Agent Skills rather than replacing them. It does not provide the agent reasoning runtime in V1.

### Two-Plane Architecture

- **Artifact Plane (Docker-inspired):** BUILD/REGISTER providers, PUSH to registry with version/tag/digest/owner. Supports new packaged artifacts and existing remote agents/MCP servers/Skills.
- **Capability Plane (CapMesh differentiator):** Consumer expresses a need as a capability. Resolver discovers candidates, applies compatibility/policy/health/version filters, and returns a selected provider with binding instructions.

### Internal Structure

```
src/capmesh/
├── models/          # Pydantic models for manifests, capabilities, artifacts
├── registry/        # SQLite + YAML file storage, CRUD operations
├── resolver/        # Deterministic capability resolution
├── policy/          # Pluggable policy engine (API key auth, allow/deny rules)
├── adapters/        # A2A, MCP, Skill, REST binding adapters
│   ├── a2a.py
│   ├── mcp.py
│   ├── skills.py
│   └── rest.py
├── cli/             # Typer CLI
├── server/          # FastAPI registry API
└── telemetry/       # Resolution trace logging
```

### Local Storage Layout

```
~/.capmesh/
├── config.yaml          # CLI config, auth tokens
├── registry.db          # SQLite index
└── artifacts/
    └── {namespace}/{name}/{version}/
        └── manifest.yaml
```

### Technology Choices

- **Language:** Python 3.10+
- **Models:** Pydantic v2
- **CLI:** Typer
- **Server:** FastAPI + Uvicorn
- **Storage:** YAML files (source of truth) + SQLite (query index)
- **HTTP client:** httpx
- **Distribution:** PyPI package + Docker image for registry server

---

## 2. Data Models

All models use Pydantic v2 for validation and serialization.

### Core Manifest Model

Shared across Agent, Skill, and Tool kinds:

```python
class Metadata:
    api_version: str          # "capmesh.io/v1alpha1"
    kind: Kind                # Agent | Skill | Tool
    namespace: str            # e.g. "security"
    name: str                 # e.g. "security-reviewer"
    version: str              # semver, e.g. "2.4.0"
    owner: str                # e.g. "security-engineering"
    digest: str | None        # sha256 of manifest content

class CapabilityRef:
    capability: str           # e.g. "security.code.review"
    contract: str             # e.g. "v1"

class Manifest:
    metadata: Metadata
    provides: list[CapabilityRef]
    requires: list[CapabilityRef]
    interface: Interface      # kind-specific
    governance: Governance
```

### Kind-Specific Interfaces

```python
class A2AInterface:           # Agent
    protocol: "a2a"
    endpoint: str

class MCPInterface:           # Tool
    protocol: "mcp"
    server: str
    tool_name: str | None

class SkillInterface:         # Skill
    protocol: "skill"
    instructions: str         # path to SKILL.md
    assets: list[str]

class RESTInterface:          # Adapter
    protocol: "rest"
    endpoint: str
    auth_type: str            # "bearer", "api_key", "none"
    request_mapping: dict
    response_mapping: dict
```

### Governance and Health

```python
class Governance:
    visibility: Visibility    # public | organization | private
    status: Status            # approved | deprecated | revoked
    environment: list[str]    # e.g. ["production", "staging"]
    labels: dict[str, str]

class HealthCheck:
    enabled: bool
    endpoint: str | None
    interval_seconds: int
```

### Resolution Trace

```python
class ResolutionTrace:
    trace_id: str
    requested_capability: str
    requested_contract: str
    candidates: list[CandidateRecord]
    filters_applied: list[FilterRecord]
    selected: str | None
    protocol: str
    resolution_ms: float
    timestamp: datetime
```

### Capability IDs

Dotted hierarchy: `<domain>.<subdomain>.<action>`

- `security.code.review`
- `repository.read`
- `repository.pull-request.create`
- `presentation.create`
- `document.pdf.create`
- `data.query`

Capability contract versions are independent from provider artifact versions.

### Versioning and Immutability

- Same `name+version+digest` = idempotent (no-op)
- Same `name+version` with different `digest` = rejected with error

---

## 3. Registry Layer

Dual storage: YAML files as source of truth, SQLite as query index.

### YAML File Storage

```
~/.capmesh/artifacts/
└── security/security-reviewer/2.4.0/
    └── manifest.yaml
```

### SQLite Index

```sql
artifacts(namespace, name, kind, version, digest, manifest_path, created_at)
capabilities(artifact_id, capability, contract, direction)  -- provides | requires
tags(artifact_id, tag)
governance(artifact_id, visibility, status, owner, environment)
```

### Registry Operations

```python
class Registry:
    def register(manifest: Manifest) -> Artifact
        # 1. Validate manifest
        # 2. Compute digest (sha256 of canonical YAML)
        # 3. Reject if same name+version exists with different digest
        # 4. Write YAML to artifacts dir
        # 5. Index in SQLite

    def get(namespace, name, version) -> Artifact

    def providers_for(capability, contract) -> list[Artifact]

    def search(query: str) -> list[Artifact]
        # Keyword match on name, namespace, capability IDs

    def tag(namespace, name, version, tag) -> None

    def delete(namespace, name, version) -> None
        # Soft delete (mark revoked), keep artifact for audit

    def rebuild_index() -> None
        # Scan YAML files, rebuild SQLite from scratch
```

---

## 4. Resolver

Deterministic resolution pipeline. No ML, no ranking in V1.

### Request and Response

```python
class ResolveRequest:
    capability: str
    contract: str
    caller: CallerContext
    version_constraint: str | None

class Resolution:
    provider: Artifact
    binding: Binding
    trace: ResolutionTrace
```

### Resolution Steps

```python
class Resolver:
    def resolve(request: ResolveRequest) -> Resolution:
        # Step 1: Find candidates — registry.providers_for(capability, contract)
        # Step 2: Filter disabled/deprecated/revoked
        # Step 3: Filter unhealthy (cached health status)
        # Step 4: Contract compatibility — exact match, no cross-version fallback
        # Step 5: Apply policy — policy_engine.evaluate() for each candidate
        # Step 6: Apply version constraints — semver filtering
        # Step 7: Select — highest semver among remaining candidates
        # Step 8: Build binding — adapter_registry.get_adapter(selected).bind()
        # Step 9: Record trace — store in SQLite
```

### Design Decisions

- **Exact contract match** — `v1` never silently matches `v2`
- **Highest semver wins** — simple, predictable tie-breaking
- **Every resolution produces a trace** — stored in SQLite
- **Health checks are non-blocking** — cached status, async refresh

---

## 5. Policy Engine

Pluggable, rule-based. First deny wins.

```python
class PolicyEngine:
    def evaluate(caller, provider, capability, context) -> PolicyDecision
        # Run rules in order, first deny wins
```

### V1 Built-in Rules

1. **Visibility** — public (anyone), organization (same org), private (owner only)
2. **Environment** — provider labeled "production" can't be resolved from "staging" caller
3. **Namespace** — only namespace owners can push/modify artifacts
4. **Status** — revoked providers are never resolvable

### Authentication (V1)

API key auth with pluggable `AuthProvider` interface:

```python
class AuthProvider(Protocol):
    def authenticate(credentials: str) -> CallerContext | None

class APIKeyAuth(AuthProvider):
    # Hashed API keys stored in SQLite
    # CallerContext: identity, org, roles, environment

# Future: OIDCAuth implements same interface
```

### Policy Configuration

```yaml
# ~/.capmesh/policy.yaml
rules:
  - kind: visibility
    enabled: true
  - kind: environment
    enabled: true
  - kind: namespace
    enabled: true
```

---

## 6. Binding Adapters

Each adapter translates a resolved provider into a protocol-specific binding.

```python
class Binding:
    provider: str             # "security/security-reviewer:2.4.0"
    protocol: str             # "a2a", "mcp", "skill", "rest"
    connection: dict          # protocol-specific details
    trace_id: str

class BindingAdapter(Protocol):
    def supports(self, provider: Artifact) -> bool
    def bind(self, provider: Artifact) -> Binding
```

### Four Adapters

1. **A2A Adapter** — returns endpoint URL + agent card metadata
2. **MCP Adapter** — returns MCP server URI + tool name
3. **Skill Adapter** — dual binding: loads skill instructions/assets AND independently resolves the skill's required capabilities into tool bindings
4. **REST Adapter** — returns URL + request/response mapping + auth type

### Skill Dual Binding (Section 14A)

The Skill adapter performs two bindings:
1. Load/activate the resolved Skill instructions and assets
2. Independently resolve and expose the Tool providers required by the Skill's capability requirements

A SKILL.md mentioning a tool does not grant it. The same Skill artifact remains portable across frameworks.

---

## 7. CLI Design

Typer with subcommand groups.

```
capmesh
├── skill     init | build | push | pull | inspect | register
├── tool      init | build | push | pull | inspect | register
├── agent     init | build | push | pull | inspect | register
├── search    <query>                    # keyword search
├── resolve   <capability>               # resolve capability to provider
├── providers <capability>               # list providers for capability
├── graph     <capability>               # show dependency graph
├── tag       <ref> <tag>                # tag a version
├── login                                # authenticate + store API key
└── server    start                      # run FastAPI registry server
```

### Output Style

Docker-inspired table format by default:

```
$ capmesh providers security.code.review
NAMESPACE   NAME                VERSION   STATUS     PROTOCOL
security    security-reviewer   2.4.0     approved   a2a
security    external-reviewer   1.8.0     approved   rest

$ capmesh resolve security.code.review
 Resolved security.code.review/v1
  Provider:  security/security-reviewer:2.4.0
  Protocol:  a2a
  Endpoint:  https://security-agent.example
  Trace:     res_7f3a2b1c
```

### Flags

- `--json` on all commands for machine-readable output
- `--trace` on `resolve` to show full resolution trace

---

## 8. Server API

FastAPI, thin layer over the core library.

### Endpoints

```
POST   /v1/providers/register
GET    /v1/providers/{namespace}/{name}
GET    /v1/capabilities/{id}/providers
POST   /v1/search
POST   /v1/resolve
GET    /v1/resolutions/{trace_id}
POST   /v1/artifacts/publish
GET    /v1/artifacts/{namespace}/{name}/{version}
GET    /healthz
```

### Example

```json
// POST /v1/resolve
// Request:
{
    "capability": "security.code.review",
    "contract": "v1",
    "caller": {"identity": "orchestrator-1", "environment": "production"},
    "version_constraint": ">=2.0"
}

// Response:
{
    "provider": "security/security-reviewer:2.4.0",
    "protocol": "a2a",
    "binding": {"endpoint": "https://security-agent.example"},
    "trace_id": "res_7f3a2b1c"
}
```

### Auth

API key via `Authorization: Bearer <key>` header.

---

## 9. Telemetry and Resolution Traces

Every resolution is auditable. Stored in SQLite, queryable via CLI and API.

### Trace Structure

```python
class ResolutionTrace:
    trace_id: str                    # "res_7f3a2b1c"
    timestamp: datetime
    requested_capability: str
    requested_contract: str
    caller: CallerContext
    candidates: list[CandidateRecord]
    # Each candidate: provider name+version, passed/rejected, rejection reason
    selected_provider: str | None
    selected_protocol: str | None
    resolution_ms: float
    outcome: "success" | "no_candidates" | "all_filtered"
```

### CLI Trace Output

```
$ capmesh resolve security.code.review --trace

Requested: security.code.review/v1
Candidates: 3
   security/reviewer:2.4.0       compatible, approved, healthy
   security/reviewer:3.0.0       contract v2 -> rejected (contract_mismatch)
   external/reviewer:1.8.0       policy denied (environment)
Selected: security/reviewer:2.4.0
Protocol: a2a
Resolution: 34 ms
Trace ID: res_7f3a2b1c
```

### Retention

SQLite table, no auto-cleanup in V1. No external telemetry export in V1 (no OpenTelemetry). Trace structure is OTEL-friendly for future export.

---

## 10. Testing Strategy

Three layers:

```
tests/
├── unit/              # Fast, no I/O
│   ├── test_models.py
│   ├── test_registry.py
│   ├── test_resolver.py
│   └── test_policy.py
├── integration/       # Real storage, real CLI
│   ├── test_cli.py
│   ├── test_server.py
│   └── test_adapters.py
└── e2e/               # Proof-of-value scenario
    └── test_demo.py
```

**Tools:** pytest, pytest-cov, httpx (async test client).

**Per-phase testing:**
- Phase 1: models validate correctly, registry stores/retrieves/rejects duplicates, CLI commands work
- Phase 2: resolver selects correctly, policy denies correctly, traces are recorded
- Phase 3: each adapter produces correct bindings
- Phase 4: API endpoints return correct responses, auth works
- Phase 5: full demo scenario passes end-to-end

---

## 11. Phased Build Order

Vertical slices. Each phase is testable before moving on.

### Phase 1 — Foundation (Models + Registry + CLI skeleton)

- Pydantic models for manifests, capabilities, governance
- Registry: YAML storage + SQLite index + CRUD
- CLI: skill/tool/agent init, build, push, pull, inspect, register
- CLI: search, tag, login (config storage)
- Tests: unit + CLI integration

### Phase 2 — Resolution (Resolver + Policy)

- Resolver: 9-step pipeline
- Policy engine: visibility, environment, namespace, status rules
- Auth: API key authentication
- Resolution traces: storage + query
- CLI: resolve, providers (with --trace, --json)
- Tests: unit + integration

### Phase 3 — Binding (Adapters)

- A2A adapter
- MCP adapter
- Skill adapter (dual binding)
- REST adapter
- Tests: adapter unit + integration

### Phase 4 — Server (FastAPI API)

- All REST endpoints
- Auth middleware
- Dockerfile for registry server
- Tests: API integration

### Phase 5 — Proof-of-Value Demo

- Example: Strands orchestrator with CapMesh
- Example: LangGraph security agent (A2A)
- Example: MCP repository tool
- Example: Company presentation skill
- Demo script: dynamic discovery + provider swap
- Tests: e2e scenario

**Rule:** Do not speculatively build later phases before previous phases are tested.

---

## 12. V1 Acceptance Criteria

From the design document:

- Register an existing A2A agent without modifying it
- Register/introspect an MCP server and map a tool to a capability
- Register a Skill package
- Support one REST/custom adapter
- Resolve exact capability IDs deterministically
- Discover providers implemented in at least two different agent frameworks
- Add a new remote provider without changing/redeploying the orchestrator
- Replace a compatible provider without consumer code changes
- Persist an auditable resolution trace
- Reject duplicate immutable version pushes with different digests
- A Skill can declare required capabilities without naming a concrete Tool provider
- The Resolver can bind a Skill's required capability to a compatible Tool/MCP provider
- Claude adapter loads Skill content and Tool bindings separately

---

## 13. Non-Goals for V1

- No new agent framework
- No agent runtime
- No new A2A protocol
- No replacement for MCP or Agent Skills
- No Kubernetes-like scheduler
- No marketplace/payment system
- No semantic-only authorization/provider selection
