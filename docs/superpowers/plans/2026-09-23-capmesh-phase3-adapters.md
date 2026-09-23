# CapMesh Phase 3: Binding Adapters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the four binding adapters (A2A, MCP, Skill, REST) and an AdapterRegistry that the Resolver uses in Step 8 to produce protocol-specific bindings.

**Architecture:** Each adapter implements a `BindingAdapter` protocol with `supports()` and `bind()` methods. The Skill adapter performs dual binding — loads skill content and independently resolves the skill's required capabilities. The AdapterRegistry maps protocol names to adapters. The Resolver's `_extract_connection` is replaced by proper adapter dispatch.

**Tech Stack:** Python 3.10+, Pydantic v2

**Spec:** `docs/superpowers/specs/2026-09-23-capmesh-v1-design.md` (Section 6)

## Global Constraints

- Python >= 3.10, Pydantic >= 2.0
- Skills declare capability requirements, not concrete tool implementations
- A SKILL.md reference to a tool does not grant it
- Adapters return Binding objects with protocol-specific connection dicts
- Skill adapter dual binding: (1) load instructions/assets (2) resolve required capabilities

---

### Task 1: BindingAdapter Protocol and AdapterRegistry

**Files:**
- Create: `src/capmesh/adapters/__init__.py`
- Create: `src/capmesh/adapters/base.py`
- Create: `src/capmesh/adapters/registry.py`
- Create: `tests/unit/test_adapter_registry.py`

**Interfaces:**
- Consumes: `Binding` from Phase 2; `Manifest` from Phase 1
- Produces:
  - `BindingAdapter(Protocol)` with `supports(manifest: Manifest) -> bool` and `bind(manifest: Manifest, trace_id: str) -> Binding`
  - `AdapterRegistry()` with `register(adapter: BindingAdapter)`, `get_adapter(manifest: Manifest) -> BindingAdapter`, `bind(manifest: Manifest, trace_id: str) -> Binding`

- [ ] **Step 1: Write failing tests**

`tests/unit/test_adapter_registry.py`:
```python
import pytest
from capmesh.models import (
    A2AInterface, MCPInterface, SkillInterface, RESTInterface,
    CapabilityRef, Governance, Kind, Manifest, Metadata, Status, Visibility,
)
from capmesh.adapters.registry import AdapterRegistry
from capmesh.adapters.base import BindingAdapter
from capmesh.models.resolution import Binding


def _agent_manifest() -> Manifest:
    return Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="sec", name="rev", version="1.0.0", owner="o"),
        provides=[CapabilityRef(capability="test", contract="v1")],
        requires=[], interface=A2AInterface(protocol="a2a", endpoint="https://a.example"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )


def _tool_manifest() -> Manifest:
    return Manifest(
        metadata=Metadata(kind=Kind.TOOL, namespace="repo", name="gh", version="1.0.0", owner="o"),
        provides=[CapabilityRef(capability="test", contract="v1")],
        requires=[], interface=MCPInterface(protocol="mcp", server="gh-mcp"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )


class StubAdapter:
    def __init__(self, protocol: str):
        self._protocol = protocol

    def supports(self, manifest: Manifest) -> bool:
        return manifest.interface.protocol == self._protocol

    def bind(self, manifest: Manifest, trace_id: str) -> Binding:
        return Binding(provider="test", protocol=self._protocol, connection={}, trace_id=trace_id)


def test_register_and_get_adapter():
    reg = AdapterRegistry()
    adapter = StubAdapter("a2a")
    reg.register(adapter)
    found = reg.get_adapter(_agent_manifest())
    assert found is adapter


def test_get_adapter_returns_correct_one():
    reg = AdapterRegistry()
    a2a = StubAdapter("a2a")
    mcp = StubAdapter("mcp")
    reg.register(a2a)
    reg.register(mcp)
    assert reg.get_adapter(_agent_manifest()) is a2a
    assert reg.get_adapter(_tool_manifest()) is mcp


def test_get_adapter_raises_for_unknown():
    reg = AdapterRegistry()
    with pytest.raises(ValueError, match="No adapter"):
        reg.get_adapter(_agent_manifest())


def test_bind_delegates_to_adapter():
    reg = AdapterRegistry()
    reg.register(StubAdapter("a2a"))
    binding = reg.bind(_agent_manifest(), "res_test123")
    assert binding.protocol == "a2a"
    assert binding.trace_id == "res_test123"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_adapter_registry.py -v
```

- [ ] **Step 3: Implement base and registry**

`src/capmesh/adapters/__init__.py`:
```python
from capmesh.adapters.registry import AdapterRegistry

__all__ = ["AdapterRegistry"]
```

`src/capmesh/adapters/base.py`:
```python
from __future__ import annotations

from typing import Protocol

from capmesh.models.manifest import Manifest
from capmesh.models.resolution import Binding


class BindingAdapter(Protocol):
    def supports(self, manifest: Manifest) -> bool: ...
    def bind(self, manifest: Manifest, trace_id: str) -> Binding: ...
```

`src/capmesh/adapters/registry.py`:
```python
from __future__ import annotations

from capmesh.adapters.base import BindingAdapter
from capmesh.models.manifest import Manifest
from capmesh.models.resolution import Binding


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: list[BindingAdapter] = []

    def register(self, adapter: BindingAdapter) -> None:
        self._adapters.append(adapter)

    def get_adapter(self, manifest: Manifest) -> BindingAdapter:
        for adapter in self._adapters:
            if adapter.supports(manifest):
                return adapter
        raise ValueError(f"No adapter found for protocol '{manifest.interface.protocol}'")

    def bind(self, manifest: Manifest, trace_id: str) -> Binding:
        adapter = self.get_adapter(manifest)
        return adapter.bind(manifest, trace_id)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/unit/test_adapter_registry.py -v
```

Expected: all PASSED

- [ ] **Step 5: Commit**

```bash
git add src/capmesh/adapters/ tests/unit/test_adapter_registry.py
git commit -m "feat: add BindingAdapter protocol and AdapterRegistry"
```

---

### Task 2: A2A, MCP, and REST Adapters

**Files:**
- Create: `src/capmesh/adapters/a2a.py`
- Create: `src/capmesh/adapters/mcp.py`
- Create: `src/capmesh/adapters/rest.py`
- Create: `tests/unit/test_adapters.py`

**Interfaces:**
- Consumes: `BindingAdapter` from Task 1; `Binding` from Phase 2; `A2AInterface`, `MCPInterface`, `RESTInterface` from Phase 1
- Produces:
  - `A2ABindingAdapter` — supports "a2a" protocol, returns endpoint in connection
  - `MCPBindingAdapter` — supports "mcp" protocol, returns server + tool_name
  - `RESTBindingAdapter` — supports "rest" protocol, returns endpoint + auth_type + mappings

- [ ] **Step 1: Write failing tests**

`tests/unit/test_adapters.py`:
```python
from capmesh.models import (
    A2AInterface, MCPInterface, RESTInterface, SkillInterface,
    CapabilityRef, Governance, Kind, Manifest, Metadata, Status, Visibility,
)
from capmesh.adapters.a2a import A2ABindingAdapter
from capmesh.adapters.mcp import MCPBindingAdapter
from capmesh.adapters.rest import RESTBindingAdapter


def _manifest(interface) -> Manifest:
    return Manifest(
        metadata=Metadata(kind=Kind.AGENT, namespace="ns", name="test", version="1.0.0", owner="o"),
        provides=[CapabilityRef(capability="test", contract="v1")],
        requires=[], interface=interface,
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )


# --- A2A ---

def test_a2a_supports():
    adapter = A2ABindingAdapter()
    assert adapter.supports(_manifest(A2AInterface(protocol="a2a", endpoint="https://a.example")))
    assert not adapter.supports(_manifest(MCPInterface(protocol="mcp", server="s")))


def test_a2a_bind():
    adapter = A2ABindingAdapter()
    m = _manifest(A2AInterface(protocol="a2a", endpoint="https://agent.example"))
    binding = adapter.bind(m, "res_test")
    assert binding.protocol == "a2a"
    assert binding.connection["endpoint"] == "https://agent.example"
    assert binding.provider == "ns/test:1.0.0"
    assert binding.trace_id == "res_test"


# --- MCP ---

def test_mcp_supports():
    adapter = MCPBindingAdapter()
    assert adapter.supports(_manifest(MCPInterface(protocol="mcp", server="gh")))
    assert not adapter.supports(_manifest(A2AInterface(protocol="a2a", endpoint="x")))


def test_mcp_bind():
    adapter = MCPBindingAdapter()
    m = _manifest(MCPInterface(protocol="mcp", server="github-mcp", tool_name="search"))
    binding = adapter.bind(m, "res_test")
    assert binding.protocol == "mcp"
    assert binding.connection["server"] == "github-mcp"
    assert binding.connection["tool_name"] == "search"


def test_mcp_bind_no_tool_name():
    adapter = MCPBindingAdapter()
    m = _manifest(MCPInterface(protocol="mcp", server="github-mcp"))
    binding = adapter.bind(m, "res_test")
    assert "tool_name" not in binding.connection


# --- REST ---

def test_rest_supports():
    adapter = RESTBindingAdapter()
    iface = RESTInterface(protocol="rest", endpoint="https://api.example", auth_type="bearer", request_mapping={}, response_mapping={})
    assert adapter.supports(_manifest(iface))
    assert not adapter.supports(_manifest(A2AInterface(protocol="a2a", endpoint="x")))


def test_rest_bind():
    adapter = RESTBindingAdapter()
    iface = RESTInterface(
        protocol="rest", endpoint="https://api.example/v1",
        auth_type="bearer",
        request_mapping={"input": "$.body"},
        response_mapping={"output": "$.result"},
    )
    binding = adapter.bind(_manifest(iface), "res_test")
    assert binding.protocol == "rest"
    assert binding.connection["endpoint"] == "https://api.example/v1"
    assert binding.connection["auth_type"] == "bearer"
    assert binding.connection["request_mapping"] == {"input": "$.body"}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_adapters.py -v
```

- [ ] **Step 3: Implement adapters**

`src/capmesh/adapters/a2a.py`:
```python
from __future__ import annotations

from capmesh.models.manifest import Manifest
from capmesh.models.resolution import Binding


class A2ABindingAdapter:
    def supports(self, manifest: Manifest) -> bool:
        return manifest.interface.protocol == "a2a"

    def bind(self, manifest: Manifest, trace_id: str) -> Binding:
        meta = manifest.metadata
        iface = manifest.interface
        return Binding(
            provider=f"{meta.namespace}/{meta.name}:{meta.version}",
            protocol="a2a",
            connection={"endpoint": iface.endpoint},
            trace_id=trace_id,
        )
```

`src/capmesh/adapters/mcp.py`:
```python
from __future__ import annotations

from capmesh.models.manifest import Manifest
from capmesh.models.resolution import Binding


class MCPBindingAdapter:
    def supports(self, manifest: Manifest) -> bool:
        return manifest.interface.protocol == "mcp"

    def bind(self, manifest: Manifest, trace_id: str) -> Binding:
        meta = manifest.metadata
        iface = manifest.interface
        connection: dict = {"server": iface.server}
        if iface.tool_name:
            connection["tool_name"] = iface.tool_name
        return Binding(
            provider=f"{meta.namespace}/{meta.name}:{meta.version}",
            protocol="mcp",
            connection=connection,
            trace_id=trace_id,
        )
```

`src/capmesh/adapters/rest.py`:
```python
from __future__ import annotations

from capmesh.models.manifest import Manifest
from capmesh.models.resolution import Binding


class RESTBindingAdapter:
    def supports(self, manifest: Manifest) -> bool:
        return manifest.interface.protocol == "rest"

    def bind(self, manifest: Manifest, trace_id: str) -> Binding:
        meta = manifest.metadata
        iface = manifest.interface
        return Binding(
            provider=f"{meta.namespace}/{meta.name}:{meta.version}",
            protocol="rest",
            connection={
                "endpoint": iface.endpoint,
                "auth_type": iface.auth_type,
                "request_mapping": iface.request_mapping,
                "response_mapping": iface.response_mapping,
            },
            trace_id=trace_id,
        )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/unit/test_adapters.py -v
```

Expected: all PASSED

- [ ] **Step 5: Commit**

```bash
git add src/capmesh/adapters/ tests/unit/test_adapters.py
git commit -m "feat: add A2A, MCP, and REST binding adapters"
```

---

### Task 3: Skill Adapter with Dual Binding

**Files:**
- Create: `src/capmesh/adapters/skills.py`
- Modify: `tests/unit/test_adapters.py` (append skill adapter tests)

**Interfaces:**
- Consumes: `BindingAdapter` from Task 1; `Resolver` from Phase 2; `SkillInterface` from Phase 1
- Produces:
  - `SkillBindingAdapter(resolver: Resolver | None)` — supports "skill" protocol
  - `bind()` returns Binding with `instructions`, `assets`, and `tool_bindings` (resolved from skill's requires)

- [ ] **Step 1: Write failing tests**

Append to `tests/unit/test_adapters.py`:
```python
from capmesh.adapters.skills import SkillBindingAdapter


def test_skill_supports():
    adapter = SkillBindingAdapter()
    iface = SkillInterface(protocol="skill", instructions="SKILL.md", assets=["templates/"])
    assert adapter.supports(_manifest(iface))
    assert not adapter.supports(_manifest(A2AInterface(protocol="a2a", endpoint="x")))


def test_skill_bind_without_resolver():
    adapter = SkillBindingAdapter()
    iface = SkillInterface(protocol="skill", instructions="SKILL.md", assets=["templates/"])
    m = _manifest(iface)
    binding = adapter.bind(m, "res_test")
    assert binding.protocol == "skill"
    assert binding.connection["instructions"] == "SKILL.md"
    assert binding.connection["assets"] == ["templates/"]
    assert binding.connection["tool_bindings"] == []


def test_skill_bind_with_requires(tmp_path):
    from pathlib import Path
    from capmesh.registry import Registry
    from capmesh.policy import default_policy_engine
    from capmesh.resolver import Resolver

    registry = Registry(root=tmp_path)
    # Register a tool that provides repository.read
    tool = Manifest(
        metadata=Metadata(kind=Kind.TOOL, namespace="repo", name="gh-reader", version="1.0.0", owner="o"),
        provides=[CapabilityRef(capability="repository.read", contract="v1")],
        requires=[], interface=MCPInterface(protocol="mcp", server="gh-mcp", tool_name="read"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )
    registry.register(tool)

    resolver = Resolver(registry=registry, policy_engine=default_policy_engine())
    adapter = SkillBindingAdapter(resolver=resolver)

    skill = Manifest(
        metadata=Metadata(kind=Kind.SKILL, namespace="sec", name="review-skill", version="1.0.0", owner="o"),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[CapabilityRef(capability="repository.read", contract="v1")],
        interface=SkillInterface(protocol="skill", instructions="SKILL.md", assets=[]),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )

    binding = adapter.bind(skill, "res_test")
    assert binding.protocol == "skill"
    assert len(binding.connection["tool_bindings"]) == 1
    assert binding.connection["tool_bindings"][0]["protocol"] == "mcp"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_adapters.py -v
```

- [ ] **Step 3: Implement skill adapter**

`src/capmesh/adapters/skills.py`:
```python
from __future__ import annotations

from typing import TYPE_CHECKING

from capmesh.models.manifest import Manifest
from capmesh.models.resolution import Binding, CallerContext, ResolveRequest

if TYPE_CHECKING:
    from capmesh.resolver.resolver import Resolver


class SkillBindingAdapter:
    def __init__(self, resolver: Resolver | None = None) -> None:
        self._resolver = resolver

    def supports(self, manifest: Manifest) -> bool:
        return manifest.interface.protocol == "skill"

    def bind(self, manifest: Manifest, trace_id: str) -> Binding:
        meta = manifest.metadata
        iface = manifest.interface

        # Step 1: Load skill instructions and assets
        connection: dict = {
            "instructions": iface.instructions,
            "assets": list(iface.assets),
            "tool_bindings": [],
        }

        # Step 2: Resolve required capabilities into tool bindings
        if self._resolver and manifest.requires:
            tool_bindings = []
            for req in manifest.requires:
                try:
                    resolution = self._resolver.resolve(
                        ResolveRequest(
                            capability=req.capability,
                            contract=req.contract,
                            caller=CallerContext(identity=f"skill:{meta.name}"),
                        )
                    )
                    tool_bindings.append({
                        "capability": req.capability,
                        "contract": req.contract,
                        "provider": resolution.binding.provider,
                        "protocol": resolution.binding.protocol,
                        "connection": resolution.binding.connection,
                    })
                except Exception:
                    # If a required capability can't be resolved, skip it
                    tool_bindings.append({
                        "capability": req.capability,
                        "contract": req.contract,
                        "error": "unresolvable",
                    })
            connection["tool_bindings"] = tool_bindings

        return Binding(
            provider=f"{meta.namespace}/{meta.name}:{meta.version}",
            protocol="skill",
            connection=connection,
            trace_id=trace_id,
        )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/unit/test_adapters.py -v
```

Expected: all PASSED

- [ ] **Step 5: Commit**

```bash
git add src/capmesh/adapters/skills.py tests/unit/test_adapters.py
git commit -m "feat: add Skill adapter with dual binding (instructions + resolved capabilities)"
```

---

### Task 4: Integrate Adapters into Resolver + Default Adapter Registry

**Files:**
- Modify: `src/capmesh/resolver/resolver.py` (use AdapterRegistry instead of _extract_connection)
- Create: `src/capmesh/adapters/defaults.py`
- Modify: `src/capmesh/adapters/__init__.py`
- Modify: `src/capmesh/cli/resolve_commands.py` (wire up adapters)

**Interfaces:**
- Consumes: `AdapterRegistry` from Task 1; all adapters from Tasks 2-3; `Resolver` from Phase 2
- Produces:
  - `default_adapter_registry(resolver: Resolver | None) -> AdapterRegistry` — returns registry with all 4 adapters
  - Updated `Resolver.__init__` accepts optional `adapter_registry: AdapterRegistry`

- [ ] **Step 1: Create default adapter registry**

`src/capmesh/adapters/defaults.py`:
```python
from __future__ import annotations

from typing import TYPE_CHECKING

from capmesh.adapters.a2a import A2ABindingAdapter
from capmesh.adapters.mcp import MCPBindingAdapter
from capmesh.adapters.registry import AdapterRegistry
from capmesh.adapters.rest import RESTBindingAdapter
from capmesh.adapters.skills import SkillBindingAdapter

if TYPE_CHECKING:
    from capmesh.resolver.resolver import Resolver


def default_adapter_registry(resolver: Resolver | None = None) -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(A2ABindingAdapter())
    registry.register(MCPBindingAdapter())
    registry.register(SkillBindingAdapter(resolver=resolver))
    registry.register(RESTBindingAdapter())
    return registry
```

- [ ] **Step 2: Update Resolver to use AdapterRegistry**

In `src/capmesh/resolver/resolver.py`, modify `__init__` to accept `adapter_registry` and use it in resolve:

Replace the `_extract_connection` call in the resolve method with:
```python
# Step 8: Build binding via adapter
if self._adapter_registry:
    binding = self._adapter_registry.bind(selected_manifest, trace_id)
else:
    binding = Binding(
        provider=f"{meta.namespace}/{meta.name}:{meta.version}",
        protocol=selected_protocol,
        connection=self._extract_connection(selected_manifest),
        trace_id=trace_id,
    )
```

Add `adapter_registry` parameter to `__init__`:
```python
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
```

- [ ] **Step 3: Update CLI to wire adapters**

In `src/capmesh/cli/resolve_commands.py`, update `_get_resolver()` to create and pass adapter registry:
```python
from capmesh.adapters.defaults import default_adapter_registry

# After creating resolver:
adapter_reg = default_adapter_registry(resolver=resolver)
resolver._adapter_registry = adapter_reg
```

- [ ] **Step 4: Update adapters __init__.py**

```python
from capmesh.adapters.defaults import default_adapter_registry
from capmesh.adapters.registry import AdapterRegistry

__all__ = ["AdapterRegistry", "default_adapter_registry"]
```

- [ ] **Step 5: Run all tests**

```bash
pytest tests/ -v
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/capmesh/adapters/ src/capmesh/resolver/ src/capmesh/cli/resolve_commands.py
git commit -m "feat: integrate binding adapters into resolver pipeline"
```

---

### Task 5: Full Phase 3 Test Verification

**Files:**
- No new files

- [ ] **Step 1: Run full test suite with coverage**

```bash
pytest tests/ -v --cov=capmesh --cov-report=term-missing
```

Expected: all pass, coverage >= 80%

- [ ] **Step 2: Commit if any fixes needed**

```bash
git add -A
git commit -m "chore: verify Phase 3 test suite"
```
