# CapMesh Phase 5: Proof-of-Value Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create example manifests, a demo script, and an end-to-end test that demonstrates CapMesh's core value: dynamic capability discovery, resolution, provider substitution, and auditable traces — all without changing/restarting the consumer.

**Architecture:** Example manifests in `examples/` directory, a runnable demo script, and an e2e test that exercises the full flow programmatically. Updates README with usage examples.

**Tech Stack:** Python 3.10+, pytest, existing capmesh package

**Spec:** `docs/superpowers/specs/2026-09-23-capmesh-v1-design.md` (Section 20)

## Global Constraints

- Examples must be self-contained YAML manifests
- Demo must work with just `pip install capmesh` — no external services
- E2E test proves: register → resolve → bind → swap provider → re-resolve → trace

---

### Task 1: Example Manifests

**Files:**
- Create: `examples/security-agent/manifest.yaml`
- Create: `examples/github-tool/manifest.yaml`
- Create: `examples/security-review-skill/manifest.yaml`
- Create: `examples/security-review-skill/SKILL.md`
- Create: `examples/performance-agent/manifest.yaml`
- Create: `examples/rest-analyzer/manifest.yaml`

**Interfaces:**
- Consumes: Manifest schema from Phase 1
- Produces: 5 example manifests covering all 4 protocols

- [ ] **Step 1: Create LangGraph security agent (A2A)**

`examples/security-agent/manifest.yaml`:
```yaml
apiVersion: capmesh.io/v1alpha1
kind: agent
metadata:
  namespace: security
  name: security-reviewer
  version: "2.4.0"
  owner: security-engineering
provides:
  - capability: security.code.review
    contract: v1
requires:
  - capability: repository.read
    contract: v1
interface:
  protocol: a2a
  endpoint: https://security-agent.example.com
governance:
  visibility: public
  status: approved
  environment:
    - production
    - staging
```

- [ ] **Step 2: Create GitHub MCP tool**

`examples/github-tool/manifest.yaml`:
```yaml
apiVersion: capmesh.io/v1alpha1
kind: tool
metadata:
  namespace: repository
  name: github-reader
  version: "1.0.0"
  owner: platform-team
provides:
  - capability: repository.read
    contract: v1
  - capability: repository.search
    contract: v1
requires: []
interface:
  protocol: mcp
  server: github-mcp
  tool_name: read_file
governance:
  visibility: public
  status: approved
```

- [ ] **Step 3: Create security review skill**

`examples/security-review-skill/manifest.yaml`:
```yaml
apiVersion: capmesh.io/v1alpha1
kind: skill
metadata:
  namespace: security
  name: security-code-review
  version: "1.2.0"
  owner: security-engineering
provides:
  - capability: security.code.review
    contract: v1
requires:
  - capability: repository.read
    contract: v1
  - capability: repository.search
    contract: v1
interface:
  protocol: skill
  instructions: SKILL.md
  assets: []
governance:
  visibility: public
  status: approved
```

`examples/security-review-skill/SKILL.md`:
```markdown
# Security Code Review Skill

## Procedure
1. Use repository search to find security-sensitive files
2. Use repository read to examine each file
3. Check for common vulnerabilities (OWASP Top 10)
4. Generate a findings report with severity ratings

## Notes
This skill requires repository.read and repository.search capabilities.
The specific tool providers are resolved at bind time by CapMesh.
```

- [ ] **Step 4: Create performance agent (A2A)**

`examples/performance-agent/manifest.yaml`:
```yaml
apiVersion: capmesh.io/v1alpha1
kind: agent
metadata:
  namespace: performance
  name: performance-analyzer
  version: "1.0.0"
  owner: platform-team
provides:
  - capability: performance.analyze
    contract: v1
requires:
  - capability: repository.read
    contract: v1
interface:
  protocol: a2a
  endpoint: https://perf-agent.example.com
governance:
  visibility: public
  status: approved
```

- [ ] **Step 5: Create REST analyzer**

`examples/rest-analyzer/manifest.yaml`:
```yaml
apiVersion: capmesh.io/v1alpha1
kind: tool
metadata:
  namespace: analysis
  name: code-analyzer
  version: "1.8.0"
  owner: platform-team
provides:
  - capability: code.analyze
    contract: v1
requires: []
interface:
  protocol: rest
  endpoint: https://analyzer.example.com/api/v1/analyze
  auth_type: bearer
  request_mapping:
    input: "$.body"
  response_mapping:
    output: "$.result"
governance:
  visibility: public
  status: approved
```

- [ ] **Step 6: Commit**

```bash
git add examples/
git commit -m "feat: add example manifests for all four protocols"
```

---

### Task 2: Demo Script

**Files:**
- Create: `examples/demo.py`

**Interfaces:**
- Consumes: `Registry`, `Resolver`, `PolicyEngine`, `TraceStore`, `AdapterRegistry`, `Manifest`, `manifest_from_yaml`
- Produces: Runnable demo script that demonstrates the full CapMesh flow

- [ ] **Step 1: Write demo script**

`examples/demo.py`:
```python
#!/usr/bin/env python3
"""CapMesh Proof-of-Value Demo

Demonstrates:
1. Register providers from example manifests
2. Resolve capabilities to providers
3. Show resolution traces
4. Dynamically add a new provider without restart
5. Swap a compatible provider
"""
import sqlite3
import sys
from pathlib import Path

from capmesh.adapters.defaults import default_adapter_registry
from capmesh.models.resolution import CallerContext, ResolveRequest
from capmesh.models.serialization import manifest_from_yaml
from capmesh.policy import default_policy_engine
from capmesh.registry import Registry
from capmesh.resolver import Resolver, ResolutionError
from capmesh.telemetry import TraceStore


def main():
    # Setup: temp registry
    import tempfile
    root = Path(tempfile.mkdtemp(prefix="capmesh-demo-"))
    print(f"Registry root: {root}\n")

    registry = Registry(root=root)
    policy = default_policy_engine()
    db = sqlite3.connect(str(root / "traces.db"))
    db.row_factory = sqlite3.Row
    trace_store = TraceStore(db)
    trace_store.init_schema()

    resolver = Resolver(registry=registry, policy_engine=policy, trace_store=trace_store)
    adapter_reg = default_adapter_registry(resolver=resolver)
    resolver._adapter_registry = adapter_reg

    examples_dir = Path(__file__).parent

    # Step 1: Register providers
    print("=" * 60)
    print("STEP 1: Register providers")
    print("=" * 60)

    manifests_to_register = [
        "security-agent/manifest.yaml",
        "github-tool/manifest.yaml",
        "security-review-skill/manifest.yaml",
    ]

    for manifest_path in manifests_to_register:
        full_path = examples_dir / manifest_path
        yaml_str = full_path.read_text()
        manifest = manifest_from_yaml(yaml_str)
        digest = registry.register(manifest)
        print(f"  Registered: {manifest.metadata.namespace}/{manifest.metadata.name}:{manifest.metadata.version}")
        print(f"    Digest: sha256:{digest[:16]}...")
        print(f"    Provides: {', '.join(c.capability for c in manifest.provides)}")

    # Step 2: Resolve security.code.review
    print(f"\n{'=' * 60}")
    print("STEP 2: Resolve security.code.review/v1")
    print("=" * 60)

    request = ResolveRequest(
        capability="security.code.review",
        contract="v1",
        caller=CallerContext(identity="demo-orchestrator", environment="production"),
    )
    resolution = resolver.resolve(request)
    print(f"  Provider:  {resolution.provider_namespace}/{resolution.provider_name}:{resolution.provider_version}")
    print(f"  Protocol:  {resolution.binding.protocol}")
    print(f"  Trace ID:  {resolution.trace.trace_id}")
    print(f"  Resolution: {resolution.trace.resolution_ms:.1f} ms")

    # Step 3: Show trace
    print(f"\n{'=' * 60}")
    print("STEP 3: Resolution Trace")
    print("=" * 60)

    trace = trace_store.get_trace(resolution.trace.trace_id)
    print(f"  Requested: {trace.requested_capability}/{trace.requested_contract}")
    print(f"  Candidates: {len(trace.candidates)}")
    for c in trace.candidates:
        status = "PASS" if c.passed else f"FAIL ({c.rejection_reason})"
        print(f"    {c.provider}:{c.version} -> {status}")
    print(f"  Selected: {trace.selected_provider}")
    print(f"  Outcome: {trace.outcome}")

    # Step 4: Dynamic discovery — add performance agent WITHOUT restart
    print(f"\n{'=' * 60}")
    print("STEP 4: Dynamic Discovery — add new provider at runtime")
    print("=" * 60)

    perf_yaml = (examples_dir / "performance-agent/manifest.yaml").read_text()
    perf_manifest = manifest_from_yaml(perf_yaml)
    registry.register(perf_manifest)
    print(f"  Registered: {perf_manifest.metadata.namespace}/{perf_manifest.metadata.name}:{perf_manifest.metadata.version}")

    # Resolve performance.analyze — works immediately
    perf_request = ResolveRequest(
        capability="performance.analyze",
        contract="v1",
        caller=CallerContext(identity="demo-orchestrator"),
    )
    perf_resolution = resolver.resolve(perf_request)
    print(f"  Resolved:  {perf_resolution.provider_namespace}/{perf_resolution.provider_name}:{perf_resolution.provider_version}")
    print(f"  Protocol:  {perf_resolution.binding.protocol}")
    print("  No restart needed!")

    # Step 5: Provider swap — register a higher-version security reviewer
    print(f"\n{'=' * 60}")
    print("STEP 5: Provider Swap — higher version replaces selection")
    print("=" * 60)

    from capmesh.models import (
        A2AInterface, CapabilityRef, Governance, Kind, Manifest, Metadata,
        Status, Visibility,
    )
    new_reviewer = Manifest(
        metadata=Metadata(
            kind=Kind.AGENT, namespace="security", name="security-reviewer-v3",
            version="3.0.0", owner="security-engineering",
        ),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[],
        interface=A2AInterface(protocol="a2a", endpoint="https://security-v3.example.com"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED, environment=["production", "staging"]),
    )
    registry.register(new_reviewer)
    print(f"  Registered: security/security-reviewer-v3:3.0.0")

    resolution2 = resolver.resolve(request)
    print(f"  Re-resolved: {resolution2.provider_namespace}/{resolution2.provider_name}:{resolution2.provider_version}")
    print(f"  Previous:    {resolution.provider_namespace}/{resolution.provider_name}:{resolution.provider_version}")
    print(f"  No consumer code changes needed!")

    # Step 6: Resolve repository.read (MCP tool)
    print(f"\n{'=' * 60}")
    print("STEP 6: Resolve repository.read/v1 (MCP tool)")
    print("=" * 60)

    repo_request = ResolveRequest(
        capability="repository.read",
        contract="v1",
        caller=CallerContext(identity="demo-orchestrator"),
    )
    repo_resolution = resolver.resolve(repo_request)
    print(f"  Provider:  {repo_resolution.provider_namespace}/{repo_resolution.provider_name}:{repo_resolution.provider_version}")
    print(f"  Protocol:  {repo_resolution.binding.protocol}")
    print(f"  Server:    {repo_resolution.binding.connection.get('server', 'N/A')}")

    print(f"\n{'=' * 60}")
    print("DEMO COMPLETE")
    print("=" * 60)
    print(f"\nAll resolutions auditable. {len(trace_store.list_traces())} traces stored.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify demo runs**

```bash
python examples/demo.py
```

Expected: full demo output showing all 6 steps

- [ ] **Step 3: Commit**

```bash
git add examples/demo.py
git commit -m "feat: add proof-of-value demo script"
```

---

### Task 3: E2E Test + README Update

**Files:**
- Create: `tests/e2e/__init__.py`
- Create: `tests/e2e/test_demo.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: all CapMesh modules
- Produces: E2E test proving the full workflow; updated README with usage examples

- [ ] **Step 1: Write E2E test**

`tests/e2e/__init__.py`:
```python
```

`tests/e2e/test_demo.py`:
```python
import sqlite3
from pathlib import Path

import pytest

from capmesh.adapters.defaults import default_adapter_registry
from capmesh.models import (
    A2AInterface, CapabilityRef, Governance, Kind, MCPInterface,
    Manifest, Metadata, SkillInterface, Status, Visibility,
)
from capmesh.models.resolution import CallerContext, ResolveRequest
from capmesh.policy import default_policy_engine
from capmesh.registry import Registry
from capmesh.resolver import Resolver, ResolutionError
from capmesh.telemetry import TraceStore


@pytest.fixture
def system(tmp_path: Path):
    registry = Registry(root=tmp_path)
    policy = default_policy_engine()
    db = sqlite3.connect(str(tmp_path / "traces.db"))
    db.row_factory = sqlite3.Row
    trace_store = TraceStore(db)
    trace_store.init_schema()
    resolver = Resolver(registry=registry, policy_engine=policy, trace_store=trace_store)
    adapter_reg = default_adapter_registry(resolver=resolver)
    resolver._adapter_registry = adapter_reg
    return registry, resolver, trace_store


def _agent(namespace, name, version, capability, contract="v1", endpoint="https://a.example"):
    return Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace=namespace, name=name, version=version, owner="team"),
        provides=[CapabilityRef(capability=capability, contract=contract)],
        requires=[], interface=A2AInterface(protocol="a2a", endpoint=endpoint),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )


def _tool(namespace, name, version, capability, server="mcp-server", tool_name="tool"):
    return Manifest(
        metadata=Metadata(kind=Kind.TOOL, namespace=namespace, name=name, version=version, owner="team"),
        provides=[CapabilityRef(capability=capability, contract="v1")],
        requires=[], interface=MCPInterface(protocol="mcp", server=server, tool_name=tool_name),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )


def _skill(namespace, name, version, capability, requires_caps):
    return Manifest(
        metadata=Metadata(kind=Kind.SKILL, namespace=namespace, name=name, version=version, owner="team"),
        provides=[CapabilityRef(capability=capability, contract="v1")],
        requires=[CapabilityRef(capability=c, contract="v1") for c in requires_caps],
        interface=SkillInterface(protocol="skill", instructions="SKILL.md", assets=[]),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )


def test_full_lifecycle(system):
    """V1 acceptance test: register, resolve, swap, trace."""
    registry, resolver, trace_store = system

    # 1. Register providers
    registry.register(_agent("security", "reviewer", "2.4.0", "security.code.review"))
    registry.register(_tool("repository", "github-reader", "1.0.0", "repository.read", "gh-mcp", "read_file"))

    # 2. Resolve security.code.review
    req = ResolveRequest(
        capability="security.code.review", contract="v1",
        caller=CallerContext(identity="orchestrator"),
    )
    res = resolver.resolve(req)
    assert res.provider_name == "reviewer"
    assert res.provider_version == "2.4.0"
    assert res.binding.protocol == "a2a"
    assert res.trace.outcome == "success"

    # 3. Verify trace is auditable
    trace = trace_store.get_trace(res.trace.trace_id)
    assert trace is not None
    assert trace.selected_provider == "security/reviewer:2.4.0"

    # 4. Add new provider dynamically (no restart)
    registry.register(_agent("performance", "perf-analyzer", "1.0.0", "performance.analyze"))
    perf_res = resolver.resolve(ResolveRequest(
        capability="performance.analyze", contract="v1",
        caller=CallerContext(identity="orchestrator"),
    ))
    assert perf_res.provider_name == "perf-analyzer"

    # 5. Swap provider — register higher version
    registry.register(_agent("security", "reviewer-v3", "3.0.0", "security.code.review"))
    res2 = resolver.resolve(req)
    assert res2.provider_version == "3.0.0"  # Highest semver wins
    assert res2.provider_name == "reviewer-v3"

    # 6. Verify trace count
    traces = trace_store.list_traces(limit=100)
    assert len(traces) >= 3


def test_skill_dual_binding(system):
    """Skill declares capabilities, resolver binds tools independently."""
    registry, resolver, _ = system

    # Register the tool that satisfies the skill's requirement
    registry.register(_tool("repository", "gh-reader", "1.0.0", "repository.read", "gh-mcp", "read"))

    # Register the skill
    registry.register(_skill("security", "review-skill", "1.0.0", "security.code.review", ["repository.read"]))

    # Resolve the skill
    res = resolver.resolve(ResolveRequest(
        capability="security.code.review", contract="v1",
        caller=CallerContext(identity="orchestrator"),
    ))
    assert res.binding.protocol == "skill"
    assert res.binding.connection["instructions"] == "SKILL.md"
    # Skill adapter should have resolved the required capability
    assert len(res.binding.connection["tool_bindings"]) == 1
    assert res.binding.connection["tool_bindings"][0]["protocol"] == "mcp"


def test_provider_swap_without_consumer_changes(system):
    """Replace a compatible provider without consumer code changes."""
    registry, resolver, _ = system

    # Register v1
    registry.register(_tool("repository", "github-reader", "1.0.0", "repository.read", "gh-mcp", "read"))

    # Resolve
    req = ResolveRequest(
        capability="repository.read", contract="v1",
        caller=CallerContext(identity="consumer"),
    )
    res1 = resolver.resolve(req)
    assert res1.provider_name == "github-reader"

    # Register a compatible replacement (higher version)
    registry.register(_tool("repository", "gitlab-reader", "2.0.0", "repository.read", "gl-mcp", "read"))

    # Same request, different provider — no consumer code changes
    res2 = resolver.resolve(req)
    assert res2.provider_version == "2.0.0"
    assert res2.provider_name == "gitlab-reader"


def test_cross_framework_discovery(system):
    """Discover providers from different agent frameworks."""
    registry, resolver, _ = system

    # LangGraph agent
    registry.register(_agent("security", "langgraph-reviewer", "1.0.0", "security.code.review"))
    # "Strands" agent (different framework, same capability)
    registry.register(_agent("security", "strands-reviewer", "2.0.0", "security.code.review"))

    # Both are discoverable
    providers = registry.providers_for("security.code.review", "v1")
    assert len(providers) == 2

    # Resolver picks highest version
    res = resolver.resolve(ResolveRequest(
        capability="security.code.review", contract="v1",
        caller=CallerContext(identity="orchestrator"),
    ))
    assert res.provider_version == "2.0.0"


def test_immutable_version_rejects_different_digest(system):
    """Same name+version with different digest is rejected."""
    registry, _, _ = system

    registry.register(_agent("security", "reviewer", "1.0.0", "security.code.review"))

    with pytest.raises(Exception):  # DuplicateVersionError
        registry.register(_agent("security", "reviewer", "1.0.0", "security.code.review",
                                 endpoint="https://different.example"))
```

- [ ] **Step 2: Run E2E tests**

```bash
pytest tests/e2e/ -v
```

Expected: all PASS

- [ ] **Step 3: Update README**

`README.md`:
```markdown
# CapMesh

Service discovery for the agentic world: dynamically discover and bind Agents, Skills and Tools by capability.

## Installation

```bash
pip install capmesh
```

For the registry server:
```bash
pip install "capmesh[server]"
```

## Quick Start

### Register a provider

```bash
# Scaffold a new agent manifest
capmesh agent init --namespace security --name reviewer --version 1.0.0 --owner my-team

# Register it
capmesh agent register --file manifest.yaml
```

### Search and resolve

```bash
# Search for providers
capmesh search "security"

# Resolve a capability to a provider
capmesh resolve security.code.review

# Show full resolution trace
capmesh resolve security.code.review --trace

# List all providers for a capability
capmesh providers security.code.review
```

### Run the registry server

```bash
capmesh server start --port 8080
```

Or with Docker:
```bash
docker run -p 8080:8080 -v capmesh-data:/data capmesh-server
```

### API

```bash
# Register a provider
curl -X POST http://localhost:8080/v1/providers/register \
  -H "Content-Type: application/json" \
  -d @manifest.json

# Resolve a capability
curl -X POST http://localhost:8080/v1/resolve \
  -H "Content-Type: application/json" \
  -d '{"capability": "security.code.review", "contract": "v1", "caller": {"identity": "my-app"}}'
```

## Demo

Run the proof-of-value demo:
```bash
python examples/demo.py
```

## Key Concepts

- **Capability**: What a consumer needs (e.g., `security.code.review`)
- **Provider**: An Agent, Skill, or Tool that provides a capability
- **Resolution**: Finding and selecting the best provider for a capability
- **Binding**: Protocol-specific connection info to use the provider
- **Trace**: Auditable record of every resolution decision

## License

Apache 2.0
```

- [ ] **Step 4: Run full test suite**

```bash
pytest tests/ -v --cov=capmesh --cov-report=term-missing
```

Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/ README.md
git commit -m "feat: add e2e tests proving V1 acceptance criteria and update README"
```

---

## Phase 5 Completion Checklist (V1 Acceptance Criteria)

- [ ] Register an existing A2A agent without modifying it
- [ ] Register/introspect an MCP server and map a tool to a capability
- [ ] Register a Skill package
- [ ] Support one REST/custom adapter
- [ ] Resolve exact capability IDs deterministically
- [ ] Discover providers implemented in at least two different agent frameworks
- [ ] Add a new remote provider without changing/redeploying the orchestrator
- [ ] Replace a compatible provider without consumer code changes
- [ ] Persist an auditable resolution trace
- [ ] Reject duplicate immutable version pushes with different digests
- [ ] A Skill can declare required capabilities without naming a concrete Tool provider
- [ ] The Resolver can bind a Skill's required capability to a compatible Tool/MCP provider
