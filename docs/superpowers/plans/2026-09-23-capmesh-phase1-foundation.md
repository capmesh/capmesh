# CapMesh Phase 1: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the foundation layer — Pydantic models, dual-storage registry (YAML + SQLite), and Typer CLI skeleton with local artifact commands (init, build, inspect, register, search, tag).

**Note:** `push` and `pull` commands require a remote registry server and are deferred to Phase 4. `login` requires auth (Phase 2).

**Architecture:** Single Python package `capmesh` with models, registry, and CLI modules. Registry stores manifests as YAML files (source of truth) and indexes them in SQLite for queries. CLI uses Typer with subcommand groups mirroring Docker's UX.

**Tech Stack:** Python 3.10+, Pydantic v2, Typer, PyYAML, SQLite3 (stdlib), pytest, pytest-cov

**Spec:** `docs/superpowers/specs/2026-09-23-capmesh-v1-design.md`

## Global Constraints

- Python >= 3.10
- Pydantic >= 2.0
- Typer >= 0.9
- PyYAML >= 6.0
- All models use Pydantic v2 `BaseModel` (not dataclasses)
- `api_version` is always `"capmesh.io/v1alpha1"`
- Manifest digests use sha256 of canonical YAML (sorted keys, no comments)
- Same `name+version+digest` = idempotent; same `name+version` + different `digest` = rejected
- Default storage root: `~/.capmesh/`
- CLI output: Docker-style tables by default, `--json` flag for machine-readable output

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/capmesh/__init__.py`
- Create: `src/capmesh/models/__init__.py`
- Create: `src/capmesh/registry/__init__.py`
- Create: `src/capmesh/cli/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/integration/__init__.py`
- Create: `README.md`
- Create: `LICENSE`

**Interfaces:**
- Consumes: nothing (first task)
- Produces: installable package `capmesh` with empty modules, `pytest` runnable

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "capmesh"
version = "0.1.0"
description = "Service discovery for the agentic world: dynamically discover and bind Agents, Skills and Tools by capability."
readme = "README.md"
license = "Apache-2.0"
requires-python = ">=3.10"
dependencies = [
    "pydantic>=2.0",
    "typer>=0.9",
    "pyyaml>=6.0",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
]

[project.scripts]
capmesh = "capmesh.cli:app"

[tool.hatch.build.targets.wheel]
packages = ["src/capmesh"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create package structure**

Create these files with minimal content:

`src/capmesh/__init__.py`:
```python
"""CapMesh — service discovery for the agentic world."""

__version__ = "0.1.0"
```

`src/capmesh/models/__init__.py`:
```python
```

`src/capmesh/registry/__init__.py`:
```python
```

`src/capmesh/cli/__init__.py`:
```python
import typer

app = typer.Typer(
    name="capmesh",
    help="Service discovery for the agentic world.",
    no_args_is_help=True,
)
```

`tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`:
```python
```

- [ ] **Step 3: Create README.md**

```markdown
# CapMesh

Service discovery for the agentic world: dynamically discover and bind Agents, Skills and Tools by capability.

## Installation

```bash
pip install capmesh
```

## License

Apache 2.0
```

- [ ] **Step 4: Create LICENSE**

Apache 2.0 license text with `Copyright 2026 CapMesh Contributors`.

- [ ] **Step 5: Install package in dev mode and verify**

```bash
pip install -e ".[dev]"
python -c "import capmesh; print(capmesh.__version__)"
capmesh --help
pytest --co
```

Expected: version prints `0.1.0`, CLI shows help text, pytest collects 0 tests.

- [ ] **Step 6: Initialize git and commit**

```bash
git init
```

Create `.gitignore`:
```
__pycache__/
*.pyc
*.egg-info/
dist/
build/
.eggs/
*.db
.venv/
```

```bash
git add .
git commit -m "chore: scaffold capmesh package with pyproject.toml and empty modules"
```

---

### Task 2: Core Pydantic Models

**Files:**
- Create: `src/capmesh/models/enums.py`
- Create: `src/capmesh/models/interfaces.py`
- Create: `src/capmesh/models/manifest.py`
- Modify: `src/capmesh/models/__init__.py`
- Create: `tests/unit/test_models.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `Kind` enum: `AGENT`, `SKILL`, `TOOL`
  - `Visibility` enum: `PUBLIC`, `ORGANIZATION`, `PRIVATE`
  - `Status` enum: `APPROVED`, `DEPRECATED`, `REVOKED`
  - `CapabilityRef(capability: str, contract: str)`
  - `Governance(visibility: Visibility, status: Status, environment: list[str], labels: dict[str, str])`
  - `HealthCheck(enabled: bool, endpoint: str | None, interval_seconds: int)`
  - `A2AInterface(protocol: Literal["a2a"], endpoint: str)`
  - `MCPInterface(protocol: Literal["mcp"], server: str, tool_name: str | None)`
  - `SkillInterface(protocol: Literal["skill"], instructions: str, assets: list[str])`
  - `RESTInterface(protocol: Literal["rest"], endpoint: str, auth_type: str, request_mapping: dict, response_mapping: dict)`
  - `Interface` = union of the four interface types (discriminated on `protocol`)
  - `Metadata(api_version: str, kind: Kind, namespace: str, name: str, version: str, owner: str, digest: str | None)`
  - `Manifest(metadata: Metadata, provides: list[CapabilityRef], requires: list[CapabilityRef], interface: Interface, governance: Governance)`

- [ ] **Step 1: Write failing tests for enums**

`tests/unit/test_models.py`:
```python
from capmesh.models.enums import Kind, Visibility, Status


def test_kind_enum_has_three_values():
    assert set(Kind) == {Kind.AGENT, Kind.SKILL, Kind.TOOL}


def test_visibility_enum_has_three_values():
    assert set(Visibility) == {Visibility.PUBLIC, Visibility.ORGANIZATION, Visibility.PRIVATE}


def test_status_enum_has_three_values():
    assert set(Status) == {Status.APPROVED, Status.DEPRECATED, Status.REVOKED}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'capmesh.models.enums'`

- [ ] **Step 3: Implement enums**

`src/capmesh/models/enums.py`:
```python
from enum import Enum


class Kind(str, Enum):
    AGENT = "agent"
    SKILL = "skill"
    TOOL = "tool"


class Visibility(str, Enum):
    PUBLIC = "public"
    ORGANIZATION = "organization"
    PRIVATE = "private"


class Status(str, Enum):
    APPROVED = "approved"
    DEPRECATED = "deprecated"
    REVOKED = "revoked"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_models.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Write failing tests for interface models**

Append to `tests/unit/test_models.py`:
```python
import pytest
from pydantic import ValidationError
from capmesh.models.interfaces import (
    A2AInterface,
    MCPInterface,
    SkillInterface,
    RESTInterface,
)


def test_a2a_interface():
    iface = A2AInterface(protocol="a2a", endpoint="https://agent.example")
    assert iface.protocol == "a2a"
    assert iface.endpoint == "https://agent.example"


def test_a2a_interface_rejects_wrong_protocol():
    with pytest.raises(ValidationError):
        A2AInterface(protocol="mcp", endpoint="https://agent.example")


def test_mcp_interface():
    iface = MCPInterface(protocol="mcp", server="github-mcp", tool_name="search")
    assert iface.protocol == "mcp"
    assert iface.server == "github-mcp"
    assert iface.tool_name == "search"


def test_mcp_interface_optional_tool_name():
    iface = MCPInterface(protocol="mcp", server="github-mcp")
    assert iface.tool_name is None


def test_skill_interface():
    iface = SkillInterface(
        protocol="skill", instructions="SKILL.md", assets=["templates/"]
    )
    assert iface.protocol == "skill"
    assert iface.instructions == "SKILL.md"
    assert iface.assets == ["templates/"]


def test_skill_interface_empty_assets():
    iface = SkillInterface(protocol="skill", instructions="SKILL.md", assets=[])
    assert iface.assets == []


def test_rest_interface():
    iface = RESTInterface(
        protocol="rest",
        endpoint="https://api.example/v1",
        auth_type="bearer",
        request_mapping={"input": "$.body"},
        response_mapping={"output": "$.result"},
    )
    assert iface.protocol == "rest"
    assert iface.auth_type == "bearer"
```

- [ ] **Step 6: Run tests to verify they fail**

```bash
pytest tests/unit/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'capmesh.models.interfaces'`

- [ ] **Step 7: Implement interface models**

`src/capmesh/models/interfaces.py`:
```python
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class A2AInterface(BaseModel):
    protocol: Literal["a2a"]
    endpoint: str


class MCPInterface(BaseModel):
    protocol: Literal["mcp"]
    server: str
    tool_name: str | None = None


class SkillInterface(BaseModel):
    protocol: Literal["skill"]
    instructions: str
    assets: list[str] = Field(default_factory=list)


class RESTInterface(BaseModel):
    protocol: Literal["rest"]
    endpoint: str
    auth_type: str
    request_mapping: dict = Field(default_factory=dict)
    response_mapping: dict = Field(default_factory=dict)


Interface = Annotated[
    Union[A2AInterface, MCPInterface, SkillInterface, RESTInterface],
    Field(discriminator="protocol"),
]
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
pytest tests/unit/test_models.py -v
```

Expected: 10 PASSED

- [ ] **Step 9: Write failing tests for manifest model**

Append to `tests/unit/test_models.py`:
```python
from capmesh.models.manifest import (
    CapabilityRef,
    Governance,
    HealthCheck,
    Metadata,
    Manifest,
)
from capmesh.models.enums import Kind, Visibility, Status


def test_capability_ref():
    ref = CapabilityRef(capability="security.code.review", contract="v1")
    assert ref.capability == "security.code.review"
    assert ref.contract == "v1"


def test_governance_defaults():
    gov = Governance(
        visibility=Visibility.PUBLIC,
        status=Status.APPROVED,
    )
    assert gov.environment == []
    assert gov.labels == {}


def test_health_check():
    hc = HealthCheck(enabled=True, endpoint="https://agent.example/health", interval_seconds=30)
    assert hc.enabled is True
    assert hc.interval_seconds == 30


def test_health_check_disabled():
    hc = HealthCheck(enabled=False)
    assert hc.endpoint is None
    assert hc.interval_seconds == 60


def test_metadata():
    meta = Metadata(
        api_version="capmesh.io/v1alpha1",
        kind=Kind.AGENT,
        namespace="security",
        name="security-reviewer",
        version="2.4.0",
        owner="security-engineering",
    )
    assert meta.digest is None
    assert meta.kind == Kind.AGENT


def test_manifest_agent():
    manifest = Manifest(
        metadata=Metadata(
            api_version="capmesh.io/v1alpha1",
            kind=Kind.AGENT,
            namespace="security",
            name="security-reviewer",
            version="2.4.0",
            owner="security-engineering",
        ),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[CapabilityRef(capability="repository.read", contract="v1")],
        interface=A2AInterface(protocol="a2a", endpoint="https://security-agent.example"),
        governance=Governance(
            visibility=Visibility.ORGANIZATION,
            status=Status.APPROVED,
        ),
    )
    assert manifest.metadata.name == "security-reviewer"
    assert len(manifest.provides) == 1
    assert manifest.interface.protocol == "a2a"


def test_manifest_skill():
    manifest = Manifest(
        metadata=Metadata(
            api_version="capmesh.io/v1alpha1",
            kind=Kind.SKILL,
            namespace="security",
            name="security-code-review",
            version="1.2.0",
            owner="security-engineering",
        ),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[
            CapabilityRef(capability="repository.read", contract="v1"),
            CapabilityRef(capability="security.scan", contract="v1"),
        ],
        interface=SkillInterface(protocol="skill", instructions="SKILL.md", assets=[]),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )
    assert manifest.metadata.kind == Kind.SKILL
    assert len(manifest.requires) == 2


def test_manifest_tool():
    manifest = Manifest(
        metadata=Metadata(
            api_version="capmesh.io/v1alpha1",
            kind=Kind.TOOL,
            namespace="repository",
            name="github-reader",
            version="1.0.0",
            owner="platform-team",
        ),
        provides=[CapabilityRef(capability="repository.read", contract="v1")],
        requires=[],
        interface=MCPInterface(protocol="mcp", server="github-mcp", tool_name="read_file"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )
    assert manifest.interface.protocol == "mcp"
    assert manifest.interface.tool_name == "read_file"


def test_manifest_rejects_missing_fields():
    with pytest.raises(ValidationError):
        Manifest(
            metadata=Metadata(
                api_version="capmesh.io/v1alpha1",
                kind=Kind.AGENT,
                namespace="security",
                name="test",
                version="1.0.0",
                owner="test",
            ),
            provides=[],
            requires=[],
            # missing interface and governance
        )
```

- [ ] **Step 10: Run tests to verify they fail**

```bash
pytest tests/unit/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'capmesh.models.manifest'`

- [ ] **Step 11: Implement manifest models**

`src/capmesh/models/manifest.py`:
```python
from __future__ import annotations

from pydantic import BaseModel, Field

from capmesh.models.enums import Kind, Visibility, Status
from capmesh.models.interfaces import Interface


class CapabilityRef(BaseModel):
    capability: str
    contract: str


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
```

- [ ] **Step 12: Run tests to verify they pass**

```bash
pytest tests/unit/test_models.py -v
```

Expected: all PASSED

- [ ] **Step 13: Update models __init__.py with public exports**

`src/capmesh/models/__init__.py`:
```python
from capmesh.models.enums import Kind, Status, Visibility
from capmesh.models.interfaces import (
    A2AInterface,
    Interface,
    MCPInterface,
    RESTInterface,
    SkillInterface,
)
from capmesh.models.manifest import (
    CapabilityRef,
    Governance,
    HealthCheck,
    Manifest,
    Metadata,
)

__all__ = [
    "Kind",
    "Status",
    "Visibility",
    "A2AInterface",
    "MCPInterface",
    "SkillInterface",
    "RESTInterface",
    "Interface",
    "CapabilityRef",
    "Governance",
    "HealthCheck",
    "Manifest",
    "Metadata",
]
```

- [ ] **Step 14: Commit**

```bash
git add src/capmesh/models/ tests/unit/test_models.py
git commit -m "feat: add core Pydantic models for manifests, interfaces, and governance"
```

---

### Task 3: YAML Serialization and Digest Computation

**Files:**
- Create: `src/capmesh/models/serialization.py`
- Create: `tests/unit/test_serialization.py`

**Interfaces:**
- Consumes: `Manifest` from Task 2
- Produces:
  - `manifest_to_yaml(manifest: Manifest) -> str` — canonical YAML (sorted keys)
  - `manifest_from_yaml(yaml_str: str) -> Manifest` — parse YAML to Manifest
  - `compute_digest(manifest: Manifest) -> str` — sha256 hex of canonical YAML

- [ ] **Step 1: Write failing tests**

`tests/unit/test_serialization.py`:
```python
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
from capmesh.models.serialization import (
    compute_digest,
    manifest_from_yaml,
    manifest_to_yaml,
)


def _sample_manifest() -> Manifest:
    return Manifest(
        metadata=Metadata(
            kind=Kind.AGENT,
            namespace="security",
            name="security-reviewer",
            version="2.4.0",
            owner="security-engineering",
        ),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[CapabilityRef(capability="repository.read", contract="v1")],
        interface=A2AInterface(protocol="a2a", endpoint="https://security-agent.example"),
        governance=Governance(visibility=Visibility.ORGANIZATION, status=Status.APPROVED),
    )


def test_manifest_to_yaml_returns_string():
    yaml_str = manifest_to_yaml(_sample_manifest())
    assert isinstance(yaml_str, str)
    assert "security-reviewer" in yaml_str


def test_manifest_roundtrip():
    original = _sample_manifest()
    yaml_str = manifest_to_yaml(original)
    restored = manifest_from_yaml(yaml_str)
    assert restored.metadata.name == original.metadata.name
    assert restored.metadata.kind == original.metadata.kind
    assert restored.provides == original.provides
    assert restored.requires == original.requires
    assert restored.interface == original.interface
    assert restored.governance == original.governance


def test_manifest_to_yaml_sorted_keys():
    yaml_str = manifest_to_yaml(_sample_manifest())
    lines = yaml_str.strip().split("\n")
    # Top-level keys should be alphabetically sorted
    top_keys = [l.split(":")[0] for l in lines if not l.startswith(" ") and ":" in l]
    assert top_keys == sorted(top_keys)


def test_compute_digest_is_deterministic():
    m = _sample_manifest()
    d1 = compute_digest(m)
    d2 = compute_digest(m)
    assert d1 == d2
    assert len(d1) == 64  # sha256 hex length


def test_compute_digest_changes_with_content():
    m1 = _sample_manifest()
    m2 = _sample_manifest()
    m2.metadata.version = "3.0.0"
    assert compute_digest(m1) != compute_digest(m2)


def test_digest_excluded_from_canonical_yaml():
    m = _sample_manifest()
    m.metadata.digest = "abc123"
    yaml_str = manifest_to_yaml(m)
    assert "abc123" not in yaml_str
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_serialization.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement serialization**

`src/capmesh/models/serialization.py`:
```python
from __future__ import annotations

import hashlib

import yaml

from capmesh.models.manifest import Manifest


def manifest_to_yaml(manifest: Manifest) -> str:
    """Serialize a Manifest to canonical YAML (sorted keys, digest excluded)."""
    data = manifest.model_dump(mode="json")
    # Exclude digest from canonical form — it's computed from the content
    data.get("metadata", {}).pop("digest", None)
    return yaml.dump(data, sort_keys=True, default_flow_style=False)


def manifest_from_yaml(yaml_str: str) -> Manifest:
    """Deserialize YAML string to a Manifest."""
    data = yaml.safe_load(yaml_str)
    return Manifest.model_validate(data)


def compute_digest(manifest: Manifest) -> str:
    """Compute sha256 hex digest of the canonical YAML representation."""
    canonical = manifest_to_yaml(manifest)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_serialization.py -v
```

Expected: all PASSED

- [ ] **Step 5: Commit**

```bash
git add src/capmesh/models/serialization.py tests/unit/test_serialization.py
git commit -m "feat: add YAML serialization and sha256 digest computation for manifests"
```

---

### Task 4: SQLite Storage Layer

**Files:**
- Create: `src/capmesh/registry/storage.py`
- Create: `tests/unit/test_storage.py`

**Interfaces:**
- Consumes: `Manifest`, `compute_digest`, `manifest_to_yaml`, `manifest_from_yaml` from Tasks 2-3
- Produces:
  - `Storage(root: Path)` — manages `~/.capmesh/` directory structure
  - `Storage.init()` — create dirs + SQLite schema
  - `Storage.save_manifest(manifest: Manifest) -> str` — write YAML + index, returns digest
  - `Storage.load_manifest(namespace: str, name: str, version: str) -> Manifest | None`
  - `Storage.list_artifacts(namespace: str | None, kind: Kind | None) -> list[ArtifactRecord]`
  - `Storage.find_providers(capability: str, contract: str) -> list[ArtifactRecord]`
  - `Storage.search(query: str) -> list[ArtifactRecord]`
  - `Storage.add_tag(namespace: str, name: str, version: str, tag: str) -> None`
  - `Storage.delete_artifact(namespace: str, name: str, version: str) -> None` (soft delete)
  - `Storage.rebuild_index() -> int` — returns count of indexed artifacts
  - `ArtifactRecord(namespace: str, name: str, kind: Kind, version: str, digest: str, manifest_path: str, created_at: str, tags: list[str])`

- [ ] **Step 1: Write failing tests**

`tests/unit/test_storage.py`:
```python
import pytest
from pathlib import Path

from capmesh.models import (
    A2AInterface,
    CapabilityRef,
    Governance,
    Kind,
    Manifest,
    MCPInterface,
    Metadata,
    Status,
    Visibility,
)
from capmesh.registry.storage import Storage, ArtifactRecord, DuplicateVersionError


def _agent_manifest(version: str = "2.4.0") -> Manifest:
    return Manifest(
        metadata=Metadata(
            kind=Kind.AGENT,
            namespace="security",
            name="security-reviewer",
            version=version,
            owner="security-engineering",
        ),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[CapabilityRef(capability="repository.read", contract="v1")],
        interface=A2AInterface(protocol="a2a", endpoint="https://security-agent.example"),
        governance=Governance(visibility=Visibility.ORGANIZATION, status=Status.APPROVED),
    )


def _tool_manifest() -> Manifest:
    return Manifest(
        metadata=Metadata(
            kind=Kind.TOOL,
            namespace="repository",
            name="github-reader",
            version="1.0.0",
            owner="platform-team",
        ),
        provides=[CapabilityRef(capability="repository.read", contract="v1")],
        requires=[],
        interface=MCPInterface(protocol="mcp", server="github-mcp", tool_name="read_file"),
        governance=Governance(visibility=Visibility.PUBLIC, status=Status.APPROVED),
    )


@pytest.fixture
def storage(tmp_path: Path) -> Storage:
    s = Storage(root=tmp_path)
    s.init()
    return s


def test_init_creates_dirs_and_db(tmp_path: Path):
    s = Storage(root=tmp_path)
    s.init()
    assert (tmp_path / "artifacts").is_dir()
    assert (tmp_path / "registry.db").is_file()


def test_save_and_load_manifest(storage: Storage):
    manifest = _agent_manifest()
    digest = storage.save_manifest(manifest)
    assert len(digest) == 64

    loaded = storage.load_manifest("security", "security-reviewer", "2.4.0")
    assert loaded is not None
    assert loaded.metadata.name == "security-reviewer"
    assert loaded.metadata.digest == digest


def test_save_idempotent_same_digest(storage: Storage):
    manifest = _agent_manifest()
    d1 = storage.save_manifest(manifest)
    d2 = storage.save_manifest(manifest)
    assert d1 == d2


def test_save_rejects_different_digest(storage: Storage):
    m1 = _agent_manifest()
    storage.save_manifest(m1)

    m2 = _agent_manifest()
    m2.interface = A2AInterface(protocol="a2a", endpoint="https://different.example")
    with pytest.raises(DuplicateVersionError):
        storage.save_manifest(m2)


def test_load_nonexistent_returns_none(storage: Storage):
    assert storage.load_manifest("nope", "nope", "1.0.0") is None


def test_find_providers(storage: Storage):
    storage.save_manifest(_agent_manifest())
    storage.save_manifest(_tool_manifest())

    providers = storage.find_providers("security.code.review", "v1")
    assert len(providers) == 1
    assert providers[0].name == "security-reviewer"

    providers = storage.find_providers("repository.read", "v1")
    assert len(providers) == 1
    assert providers[0].name == "github-reader"

    providers = storage.find_providers("nonexistent", "v1")
    assert len(providers) == 0


def test_search(storage: Storage):
    storage.save_manifest(_agent_manifest())
    storage.save_manifest(_tool_manifest())

    results = storage.search("security")
    assert len(results) == 1
    assert results[0].name == "security-reviewer"

    results = storage.search("github")
    assert len(results) == 1
    assert results[0].name == "github-reader"

    results = storage.search("nonexistent")
    assert len(results) == 0


def test_list_artifacts(storage: Storage):
    storage.save_manifest(_agent_manifest())
    storage.save_manifest(_tool_manifest())

    all_artifacts = storage.list_artifacts()
    assert len(all_artifacts) == 2

    agents = storage.list_artifacts(kind=Kind.AGENT)
    assert len(agents) == 1
    assert agents[0].kind == Kind.AGENT

    security = storage.list_artifacts(namespace="security")
    assert len(security) == 1


def test_add_tag(storage: Storage):
    storage.save_manifest(_agent_manifest())
    storage.add_tag("security", "security-reviewer", "2.4.0", "stable")

    artifacts = storage.list_artifacts()
    tagged = [a for a in artifacts if "stable" in a.tags]
    assert len(tagged) == 1


def test_delete_soft_deletes(storage: Storage):
    storage.save_manifest(_agent_manifest())
    storage.delete_artifact("security", "security-reviewer", "2.4.0")

    # YAML file still exists
    loaded = storage.load_manifest("security", "security-reviewer", "2.4.0")
    assert loaded is not None

    # But governance status is revoked
    assert loaded.governance.status == Status.REVOKED

    # And it doesn't show up in provider searches
    providers = storage.find_providers("security.code.review", "v1")
    assert len(providers) == 0


def test_rebuild_index(storage: Storage):
    storage.save_manifest(_agent_manifest())
    storage.save_manifest(_tool_manifest())

    count = storage.rebuild_index()
    assert count == 2

    # Verify searches still work after rebuild
    providers = storage.find_providers("security.code.review", "v1")
    assert len(providers) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_storage.py -v
```

Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement storage layer**

`src/capmesh/registry/storage.py`:
```python
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from capmesh.models.enums import Kind, Status
from capmesh.models.manifest import Manifest
from capmesh.models.serialization import (
    compute_digest,
    manifest_from_yaml,
    manifest_to_yaml,
)


class DuplicateVersionError(Exception):
    """Raised when pushing same name+version with different digest."""


@dataclass
class ArtifactRecord:
    namespace: str
    name: str
    kind: Kind
    version: str
    digest: str
    manifest_path: str
    created_at: str
    tags: list[str] = field(default_factory=list)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    namespace TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    version TEXT NOT NULL,
    digest TEXT NOT NULL,
    manifest_path TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(namespace, name, version)
);

CREATE TABLE IF NOT EXISTS capabilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id INTEGER NOT NULL,
    capability TEXT NOT NULL,
    contract TEXT NOT NULL,
    direction TEXT NOT NULL,
    FOREIGN KEY (artifact_id) REFERENCES artifacts(id)
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    FOREIGN KEY (artifact_id) REFERENCES artifacts(id),
    UNIQUE(artifact_id, tag)
);

CREATE TABLE IF NOT EXISTS governance (
    artifact_id INTEGER PRIMARY KEY,
    visibility TEXT NOT NULL,
    status TEXT NOT NULL,
    owner TEXT NOT NULL,
    environment TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY (artifact_id) REFERENCES artifacts(id)
);

CREATE INDEX IF NOT EXISTS idx_capabilities_lookup
ON capabilities(capability, contract, direction);

CREATE INDEX IF NOT EXISTS idx_artifacts_namespace
ON artifacts(namespace);

CREATE INDEX IF NOT EXISTS idx_governance_status
ON governance(status);
"""


class Storage:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._artifacts_dir = root / "artifacts"
        self._db_path = root / "registry.db"
        self._conn: sqlite3.Connection | None = None

    def init(self) -> None:
        self._artifacts_dir.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)

    @property
    def _db(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Storage not initialized. Call init() first.")
        return self._conn

    def _manifest_path(self, namespace: str, name: str, version: str) -> Path:
        return self._artifacts_dir / namespace / name / version / "manifest.yaml"

    def save_manifest(self, manifest: Manifest) -> str:
        meta = manifest.metadata
        digest = compute_digest(manifest)

        # Check for duplicate version with different digest
        row = self._db.execute(
            "SELECT digest FROM artifacts WHERE namespace=? AND name=? AND version=?",
            (meta.namespace, meta.name, meta.version),
        ).fetchone()

        if row is not None:
            if row["digest"] == digest:
                return digest  # Idempotent
            raise DuplicateVersionError(
                f"{meta.namespace}/{meta.name}:{meta.version} already exists with a different digest"
            )

        # Write YAML file
        manifest.metadata.digest = digest
        path = self._manifest_path(meta.namespace, meta.name, meta.version)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(manifest_to_yaml(manifest), encoding="utf-8")

        # Index in SQLite
        cursor = self._db.execute(
            "INSERT INTO artifacts (namespace, name, kind, version, digest, manifest_path) VALUES (?, ?, ?, ?, ?, ?)",
            (meta.namespace, meta.name, meta.kind.value, meta.version, digest, str(path)),
        )
        artifact_id = cursor.lastrowid

        for cap in manifest.provides:
            self._db.execute(
                "INSERT INTO capabilities (artifact_id, capability, contract, direction) VALUES (?, ?, ?, ?)",
                (artifact_id, cap.capability, cap.contract, "provides"),
            )
        for cap in manifest.requires:
            self._db.execute(
                "INSERT INTO capabilities (artifact_id, capability, contract, direction) VALUES (?, ?, ?, ?)",
                (artifact_id, cap.capability, cap.contract, "requires"),
            )

        self._db.execute(
            "INSERT INTO governance (artifact_id, visibility, status, owner, environment) VALUES (?, ?, ?, ?, ?)",
            (
                artifact_id,
                manifest.governance.visibility.value,
                manifest.governance.status.value,
                meta.owner,
                ",".join(manifest.governance.environment),
            ),
        )

        self._db.commit()
        return digest

    def load_manifest(self, namespace: str, name: str, version: str) -> Manifest | None:
        path = self._manifest_path(namespace, name, version)
        if not path.exists():
            return None
        yaml_str = path.read_text(encoding="utf-8")
        manifest = manifest_from_yaml(yaml_str)

        # Load current governance status from DB (may have been soft-deleted)
        row = self._db.execute(
            "SELECT g.status FROM artifacts a JOIN governance g ON a.id = g.artifact_id "
            "WHERE a.namespace=? AND a.name=? AND a.version=?",
            (namespace, name, version),
        ).fetchone()
        if row is not None:
            manifest.governance.status = Status(row["status"])

        # Set digest
        manifest.metadata.digest = compute_digest(manifest)
        return manifest

    def find_providers(self, capability: str, contract: str) -> list[ArtifactRecord]:
        rows = self._db.execute(
            "SELECT a.*, g.status FROM artifacts a "
            "JOIN capabilities c ON a.id = c.artifact_id "
            "JOIN governance g ON a.id = g.artifact_id "
            "WHERE c.capability=? AND c.contract=? AND c.direction='provides' "
            "AND g.status != 'revoked'",
            (capability, contract),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def search(self, query: str) -> list[ArtifactRecord]:
        pattern = f"%{query}%"
        rows = self._db.execute(
            "SELECT DISTINCT a.* FROM artifacts a "
            "LEFT JOIN capabilities c ON a.id = c.artifact_id "
            "LEFT JOIN governance g ON a.id = g.artifact_id "
            "WHERE (a.name LIKE ? OR a.namespace LIKE ? OR c.capability LIKE ?) "
            "AND (g.status IS NULL OR g.status != 'revoked')",
            (pattern, pattern, pattern),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def list_artifacts(
        self, namespace: str | None = None, kind: Kind | None = None
    ) -> list[ArtifactRecord]:
        query = "SELECT a.* FROM artifacts a JOIN governance g ON a.id = g.artifact_id WHERE g.status != 'revoked'"
        params: list[str] = []
        if namespace is not None:
            query += " AND a.namespace=?"
            params.append(namespace)
        if kind is not None:
            query += " AND a.kind=?"
            params.append(kind.value)
        rows = self._db.execute(query, params).fetchall()
        return [self._row_to_record(r) for r in rows]

    def add_tag(self, namespace: str, name: str, version: str, tag: str) -> None:
        row = self._db.execute(
            "SELECT id FROM artifacts WHERE namespace=? AND name=? AND version=?",
            (namespace, name, version),
        ).fetchone()
        if row is None:
            raise ValueError(f"Artifact {namespace}/{name}:{version} not found")
        self._db.execute(
            "INSERT OR IGNORE INTO tags (artifact_id, tag) VALUES (?, ?)",
            (row["id"], tag),
        )
        self._db.commit()

    def delete_artifact(self, namespace: str, name: str, version: str) -> None:
        """Soft delete: mark as revoked in DB and update YAML."""
        row = self._db.execute(
            "SELECT id FROM artifacts WHERE namespace=? AND name=? AND version=?",
            (namespace, name, version),
        ).fetchone()
        if row is None:
            raise ValueError(f"Artifact {namespace}/{name}:{version} not found")
        self._db.execute(
            "UPDATE governance SET status='revoked' WHERE artifact_id=?",
            (row["id"],),
        )
        self._db.commit()

        # Update YAML file
        path = self._manifest_path(namespace, name, version)
        if path.exists():
            manifest = manifest_from_yaml(path.read_text(encoding="utf-8"))
            manifest.governance.status = Status.REVOKED
            path.write_text(manifest_to_yaml(manifest), encoding="utf-8")

    def rebuild_index(self) -> int:
        """Drop and rebuild SQLite index from YAML files."""
        self._db.executescript(
            "DELETE FROM capabilities; DELETE FROM tags; DELETE FROM governance; DELETE FROM artifacts;"
        )
        count = 0
        for manifest_path in self._artifacts_dir.rglob("manifest.yaml"):
            yaml_str = manifest_path.read_text(encoding="utf-8")
            manifest = manifest_from_yaml(yaml_str)
            self.save_manifest(manifest)
            count += 1
        return count

    def _row_to_record(self, row: sqlite3.Row) -> ArtifactRecord:
        artifact_id = row["id"]
        tag_rows = self._db.execute(
            "SELECT tag FROM tags WHERE artifact_id=?", (artifact_id,)
        ).fetchall()
        return ArtifactRecord(
            namespace=row["namespace"],
            name=row["name"],
            kind=Kind(row["kind"]),
            version=row["version"],
            digest=row["digest"],
            manifest_path=row["manifest_path"],
            created_at=row["created_at"],
            tags=[t["tag"] for t in tag_rows],
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_storage.py -v
```

Expected: all PASSED

- [ ] **Step 5: Commit**

```bash
git add src/capmesh/registry/storage.py tests/unit/test_storage.py
git commit -m "feat: add dual-storage registry layer with YAML files and SQLite index"
```

---

### Task 5: Registry Facade

**Files:**
- Create: `src/capmesh/registry/registry.py`
- Modify: `src/capmesh/registry/__init__.py`
- Create: `tests/unit/test_registry.py`

**Interfaces:**
- Consumes: `Storage` from Task 4, `Manifest` from Task 2
- Produces:
  - `Registry(root: Path | None)` — high-level API, defaults root to `~/.capmesh/`
  - `Registry.register(manifest: Manifest) -> str` — returns digest
  - `Registry.get(namespace: str, name: str, version: str) -> Manifest | None`
  - `Registry.providers_for(capability: str, contract: str) -> list[ArtifactRecord]`
  - `Registry.search(query: str) -> list[ArtifactRecord]`
  - `Registry.list(namespace: str | None, kind: Kind | None) -> list[ArtifactRecord]`
  - `Registry.tag(namespace: str, name: str, version: str, tag: str) -> None`
  - `Registry.delete(namespace: str, name: str, version: str) -> None`
  - `Registry.rebuild_index() -> int`

- [ ] **Step 1: Write failing tests**

`tests/unit/test_registry.py`:
```python
import pytest
from pathlib import Path

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
from capmesh.registry import Registry
from capmesh.registry.storage import DuplicateVersionError


def _agent_manifest() -> Manifest:
    return Manifest(
        metadata=Metadata(
            kind=Kind.AGENT,
            namespace="security",
            name="security-reviewer",
            version="2.4.0",
            owner="security-engineering",
        ),
        provides=[CapabilityRef(capability="security.code.review", contract="v1")],
        requires=[CapabilityRef(capability="repository.read", contract="v1")],
        interface=A2AInterface(protocol="a2a", endpoint="https://security-agent.example"),
        governance=Governance(visibility=Visibility.ORGANIZATION, status=Status.APPROVED),
    )


@pytest.fixture
def registry(tmp_path: Path) -> Registry:
    return Registry(root=tmp_path)


def test_register_and_get(registry: Registry):
    digest = registry.register(_agent_manifest())
    assert len(digest) == 64

    manifest = registry.get("security", "security-reviewer", "2.4.0")
    assert manifest is not None
    assert manifest.metadata.name == "security-reviewer"


def test_register_idempotent(registry: Registry):
    d1 = registry.register(_agent_manifest())
    d2 = registry.register(_agent_manifest())
    assert d1 == d2


def test_register_rejects_different_digest(registry: Registry):
    registry.register(_agent_manifest())
    m2 = _agent_manifest()
    m2.interface = A2AInterface(protocol="a2a", endpoint="https://different.example")
    with pytest.raises(DuplicateVersionError):
        registry.register(m2)


def test_providers_for(registry: Registry):
    registry.register(_agent_manifest())
    providers = registry.providers_for("security.code.review", "v1")
    assert len(providers) == 1
    assert providers[0].name == "security-reviewer"


def test_search(registry: Registry):
    registry.register(_agent_manifest())
    results = registry.search("security")
    assert len(results) == 1


def test_list_all(registry: Registry):
    registry.register(_agent_manifest())
    all_items = registry.list()
    assert len(all_items) == 1


def test_tag(registry: Registry):
    registry.register(_agent_manifest())
    registry.tag("security", "security-reviewer", "2.4.0", "stable")
    items = registry.list()
    assert "stable" in items[0].tags


def test_delete(registry: Registry):
    registry.register(_agent_manifest())
    registry.delete("security", "security-reviewer", "2.4.0")
    providers = registry.providers_for("security.code.review", "v1")
    assert len(providers) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_registry.py -v
```

Expected: FAIL — `ImportError: cannot import name 'Registry'`

- [ ] **Step 3: Implement Registry facade**

`src/capmesh/registry/registry.py`:
```python
from __future__ import annotations

from pathlib import Path

from capmesh.models.enums import Kind
from capmesh.models.manifest import Manifest
from capmesh.registry.storage import ArtifactRecord, Storage


class Registry:
    def __init__(self, root: Path | None = None) -> None:
        if root is None:
            root = Path.home() / ".capmesh"
        self._storage = Storage(root)
        self._storage.init()

    def register(self, manifest: Manifest) -> str:
        return self._storage.save_manifest(manifest)

    def get(self, namespace: str, name: str, version: str) -> Manifest | None:
        return self._storage.load_manifest(namespace, name, version)

    def providers_for(self, capability: str, contract: str) -> list[ArtifactRecord]:
        return self._storage.find_providers(capability, contract)

    def search(self, query: str) -> list[ArtifactRecord]:
        return self._storage.search(query)

    def list(
        self, namespace: str | None = None, kind: Kind | None = None
    ) -> list[ArtifactRecord]:
        return self._storage.list_artifacts(namespace=namespace, kind=kind)

    def tag(self, namespace: str, name: str, version: str, tag: str) -> None:
        self._storage.add_tag(namespace, name, version, tag)

    def delete(self, namespace: str, name: str, version: str) -> None:
        self._storage.delete_artifact(namespace, name, version)

    def rebuild_index(self) -> int:
        return self._storage.rebuild_index()
```

- [ ] **Step 4: Update registry __init__.py**

`src/capmesh/registry/__init__.py`:
```python
from capmesh.registry.registry import Registry
from capmesh.registry.storage import ArtifactRecord, DuplicateVersionError

__all__ = ["Registry", "ArtifactRecord", "DuplicateVersionError"]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/test_registry.py -v
```

Expected: all PASSED

- [ ] **Step 6: Commit**

```bash
git add src/capmesh/registry/ tests/unit/test_registry.py
git commit -m "feat: add Registry facade over storage layer"
```

---

### Task 6: Manifest Scaffolding (init command helpers)

**Files:**
- Create: `src/capmesh/cli/scaffold.py`
- Create: `tests/unit/test_scaffold.py`

**Interfaces:**
- Consumes: `Manifest`, `Metadata`, `Governance`, `CapabilityRef`, interface models from Task 2
- Produces:
  - `scaffold_manifest(kind: Kind, namespace: str, name: str, version: str, owner: str) -> Manifest` — returns a starter manifest with sensible defaults
  - `write_scaffold(directory: Path, manifest: Manifest) -> Path` — writes manifest.yaml to directory, returns path

- [ ] **Step 1: Write failing tests**

`tests/unit/test_scaffold.py`:
```python
from pathlib import Path

from capmesh.models import Kind, Visibility, Status
from capmesh.cli.scaffold import scaffold_manifest, write_scaffold


def test_scaffold_agent():
    m = scaffold_manifest(Kind.AGENT, "myorg", "my-agent", "0.1.0", "me")
    assert m.metadata.kind == Kind.AGENT
    assert m.metadata.namespace == "myorg"
    assert m.metadata.name == "my-agent"
    assert m.metadata.version == "0.1.0"
    assert m.metadata.owner == "me"
    assert m.interface.protocol == "a2a"
    assert m.governance.visibility == Visibility.PRIVATE
    assert m.governance.status == Status.APPROVED
    assert m.provides == []
    assert m.requires == []


def test_scaffold_skill():
    m = scaffold_manifest(Kind.SKILL, "myorg", "my-skill", "0.1.0", "me")
    assert m.interface.protocol == "skill"
    assert m.interface.instructions == "SKILL.md"


def test_scaffold_tool():
    m = scaffold_manifest(Kind.TOOL, "myorg", "my-tool", "0.1.0", "me")
    assert m.interface.protocol == "mcp"


def test_write_scaffold(tmp_path: Path):
    m = scaffold_manifest(Kind.AGENT, "myorg", "my-agent", "0.1.0", "me")
    path = write_scaffold(tmp_path, m)
    assert path.exists()
    assert path.name == "manifest.yaml"
    content = path.read_text()
    assert "my-agent" in content
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_scaffold.py -v
```

Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement scaffold**

`src/capmesh/cli/scaffold.py`:
```python
from __future__ import annotations

from pathlib import Path

from capmesh.models.enums import Kind, Status, Visibility
from capmesh.models.interfaces import A2AInterface, MCPInterface, SkillInterface
from capmesh.models.manifest import CapabilityRef, Governance, Manifest, Metadata
from capmesh.models.serialization import manifest_to_yaml


def scaffold_manifest(
    kind: Kind,
    namespace: str,
    name: str,
    version: str,
    owner: str,
) -> Manifest:
    """Create a starter manifest with sensible defaults."""
    metadata = Metadata(
        kind=kind,
        namespace=namespace,
        name=name,
        version=version,
        owner=owner,
    )

    governance = Governance(
        visibility=Visibility.PRIVATE,
        status=Status.APPROVED,
    )

    if kind == Kind.AGENT:
        interface = A2AInterface(protocol="a2a", endpoint="https://your-agent.example")
    elif kind == Kind.SKILL:
        interface = SkillInterface(protocol="skill", instructions="SKILL.md", assets=[])
    else:
        interface = MCPInterface(protocol="mcp", server="your-mcp-server")

    return Manifest(
        metadata=metadata,
        provides=[],
        requires=[],
        interface=interface,
        governance=governance,
    )


def write_scaffold(directory: Path, manifest: Manifest) -> Path:
    """Write a manifest.yaml file to the given directory."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "manifest.yaml"
    path.write_text(manifest_to_yaml(manifest), encoding="utf-8")
    return path
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_scaffold.py -v
```

Expected: all PASSED

- [ ] **Step 5: Commit**

```bash
git add src/capmesh/cli/scaffold.py tests/unit/test_scaffold.py
git commit -m "feat: add manifest scaffolding for init commands"
```

---

### Task 7: CLI Commands — Artifact Management

**Files:**
- Create: `src/capmesh/cli/artifact_commands.py`
- Modify: `src/capmesh/cli/__init__.py`
- Create: `tests/integration/test_cli.py`

**Interfaces:**
- Consumes: `Registry` from Task 5, `scaffold_manifest`, `write_scaffold` from Task 6, `manifest_from_yaml`, `compute_digest` from Task 3
- Produces: CLI commands: `capmesh skill|tool|agent init|build|inspect|register`, `capmesh search`, `capmesh tag`
  - `init` — scaffolds a manifest.yaml in current or specified directory
  - `build` — validates manifest, computes digest, prints it
  - `inspect` — shows manifest details from registry
  - `register` — registers a manifest from a YAML file into the registry
  - `search` — keyword search across registry
  - `tag` — tags an artifact version

- [ ] **Step 1: Write failing CLI integration tests**

`tests/integration/test_cli.py`:
```python
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from capmesh.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def set_capmesh_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point all CLI commands to a temp registry root."""
    monkeypatch.setenv("CAPMESH_ROOT", str(tmp_path))


# --- init ---


def test_agent_init(tmp_path: Path):
    target = tmp_path / "my-agent"
    result = runner.invoke(
        app,
        ["agent", "init", "--namespace", "myorg", "--name", "my-agent",
         "--version", "0.1.0", "--owner", "me", "--directory", str(target)],
    )
    assert result.exit_code == 0, result.output
    assert (target / "manifest.yaml").exists()


def test_skill_init(tmp_path: Path):
    target = tmp_path / "my-skill"
    result = runner.invoke(
        app,
        ["skill", "init", "--namespace", "myorg", "--name", "my-skill",
         "--version", "0.1.0", "--owner", "me", "--directory", str(target)],
    )
    assert result.exit_code == 0, result.output
    assert (target / "manifest.yaml").exists()


def test_tool_init(tmp_path: Path):
    target = tmp_path / "my-tool"
    result = runner.invoke(
        app,
        ["tool", "init", "--namespace", "myorg", "--name", "my-tool",
         "--version", "0.1.0", "--owner", "me", "--directory", str(target)],
    )
    assert result.exit_code == 0, result.output
    assert (target / "manifest.yaml").exists()


# --- build ---


def test_build(tmp_path: Path):
    # First init
    target = tmp_path / "my-agent"
    runner.invoke(
        app,
        ["agent", "init", "--namespace", "myorg", "--name", "my-agent",
         "--version", "0.1.0", "--owner", "me", "--directory", str(target)],
    )

    # Then build
    result = runner.invoke(app, ["agent", "build", "--directory", str(target)])
    assert result.exit_code == 0, result.output
    assert "digest:" in result.output.lower() or "sha256:" in result.output.lower()


# --- register ---


def test_register(tmp_path: Path):
    # Init
    target = tmp_path / "my-agent"
    runner.invoke(
        app,
        ["agent", "init", "--namespace", "myorg", "--name", "my-agent",
         "--version", "0.1.0", "--owner", "me", "--directory", str(target)],
    )

    # Register
    result = runner.invoke(
        app, ["agent", "register", "--file", str(target / "manifest.yaml")]
    )
    assert result.exit_code == 0, result.output
    assert "registered" in result.output.lower()


# --- inspect ---


def test_inspect(tmp_path: Path):
    # Init + register
    target = tmp_path / "my-agent"
    runner.invoke(
        app,
        ["agent", "init", "--namespace", "myorg", "--name", "my-agent",
         "--version", "0.1.0", "--owner", "me", "--directory", str(target)],
    )
    runner.invoke(app, ["agent", "register", "--file", str(target / "manifest.yaml")])

    # Inspect
    result = runner.invoke(app, ["agent", "inspect", "myorg", "my-agent", "0.1.0"])
    assert result.exit_code == 0, result.output
    assert "my-agent" in result.output


def test_inspect_json(tmp_path: Path):
    target = tmp_path / "my-agent"
    runner.invoke(
        app,
        ["agent", "init", "--namespace", "myorg", "--name", "my-agent",
         "--version", "0.1.0", "--owner", "me", "--directory", str(target)],
    )
    runner.invoke(app, ["agent", "register", "--file", str(target / "manifest.yaml")])

    result = runner.invoke(
        app, ["agent", "inspect", "myorg", "my-agent", "0.1.0", "--json"]
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["metadata"]["name"] == "my-agent"


# --- search ---


def test_search(tmp_path: Path):
    # Register an agent
    target = tmp_path / "my-agent"
    runner.invoke(
        app,
        ["agent", "init", "--namespace", "security", "--name", "sec-reviewer",
         "--version", "1.0.0", "--owner", "me", "--directory", str(target)],
    )
    runner.invoke(app, ["agent", "register", "--file", str(target / "manifest.yaml")])

    result = runner.invoke(app, ["search", "security"])
    assert result.exit_code == 0, result.output
    assert "sec-reviewer" in result.output


def test_search_json(tmp_path: Path):
    target = tmp_path / "my-agent"
    runner.invoke(
        app,
        ["agent", "init", "--namespace", "security", "--name", "sec-reviewer",
         "--version", "1.0.0", "--owner", "me", "--directory", str(target)],
    )
    runner.invoke(app, ["agent", "register", "--file", str(target / "manifest.yaml")])

    result = runner.invoke(app, ["search", "security", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["name"] == "sec-reviewer"


# --- tag ---


def test_tag(tmp_path: Path):
    target = tmp_path / "my-agent"
    runner.invoke(
        app,
        ["agent", "init", "--namespace", "myorg", "--name", "my-agent",
         "--version", "0.1.0", "--owner", "me", "--directory", str(target)],
    )
    runner.invoke(app, ["agent", "register", "--file", str(target / "manifest.yaml")])

    result = runner.invoke(app, ["tag", "myorg", "my-agent", "0.1.0", "stable"])
    assert result.exit_code == 0, result.output
    assert "stable" in result.output.lower()


# --- register rejects duplicate with different content ---


def test_register_rejects_different_digest(tmp_path: Path):
    target1 = tmp_path / "v1"
    runner.invoke(
        app,
        ["agent", "init", "--namespace", "myorg", "--name", "my-agent",
         "--version", "0.1.0", "--owner", "me", "--directory", str(target1)],
    )
    runner.invoke(app, ["agent", "register", "--file", str(target1 / "manifest.yaml")])

    # Create a different manifest with the same name+version
    target2 = tmp_path / "v2"
    runner.invoke(
        app,
        ["agent", "init", "--namespace", "myorg", "--name", "my-agent",
         "--version", "0.1.0", "--owner", "different-owner", "--directory", str(target2)],
    )
    result = runner.invoke(
        app, ["agent", "register", "--file", str(target2 / "manifest.yaml")]
    )
    assert result.exit_code != 0 or "error" in result.output.lower() or "already exists" in result.output.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/integration/test_cli.py -v
```

Expected: FAIL — commands not defined

- [ ] **Step 3: Implement CLI commands**

`src/capmesh/cli/artifact_commands.py`:
```python
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from capmesh.models.enums import Kind
from capmesh.models.serialization import compute_digest, manifest_from_yaml, manifest_to_yaml
from capmesh.registry import Registry, DuplicateVersionError
from capmesh.cli.scaffold import scaffold_manifest, write_scaffold

console = Console()


def _get_registry() -> Registry:
    root = os.environ.get("CAPMESH_ROOT")
    return Registry(root=Path(root) if root else None)


def _make_artifact_app(kind: Kind) -> typer.Typer:
    artifact_app = typer.Typer(help=f"Manage {kind.value} artifacts.", no_args_is_help=True)

    @artifact_app.command()
    def init(
        namespace: str = typer.Option(..., help="Artifact namespace"),
        name: str = typer.Option(..., help="Artifact name"),
        version: str = typer.Option("0.1.0", help="Artifact version"),
        owner: str = typer.Option(..., help="Artifact owner"),
        directory: str = typer.Option(".", help="Target directory"),
    ) -> None:
        """Scaffold a new manifest."""
        manifest = scaffold_manifest(kind, namespace, name, version, owner)
        path = write_scaffold(Path(directory), manifest)
        console.print(f"[green]Created {path}[/green]")

    @artifact_app.command()
    def build(
        directory: str = typer.Option(".", help="Directory containing manifest.yaml"),
    ) -> None:
        """Validate manifest and compute digest."""
        manifest_path = Path(directory) / "manifest.yaml"
        if not manifest_path.exists():
            console.print(f"[red]Error: {manifest_path} not found[/red]")
            raise typer.Exit(code=1)
        yaml_str = manifest_path.read_text(encoding="utf-8")
        manifest = manifest_from_yaml(yaml_str)
        digest = compute_digest(manifest)
        console.print(f"[green]Valid {kind.value} manifest[/green]")
        console.print(f"  Name:    {manifest.metadata.namespace}/{manifest.metadata.name}")
        console.print(f"  Version: {manifest.metadata.version}")
        console.print(f"  Digest:  sha256:{digest}")

    @artifact_app.command()
    def register(
        file: str = typer.Option(..., help="Path to manifest.yaml"),
    ) -> None:
        """Register a manifest into the local registry."""
        manifest_path = Path(file)
        if not manifest_path.exists():
            console.print(f"[red]Error: {manifest_path} not found[/red]")
            raise typer.Exit(code=1)
        yaml_str = manifest_path.read_text(encoding="utf-8")
        manifest = manifest_from_yaml(yaml_str)

        if manifest.metadata.kind != kind:
            console.print(
                f"[red]Error: manifest kind is {manifest.metadata.kind.value}, expected {kind.value}[/red]"
            )
            raise typer.Exit(code=1)

        registry = _get_registry()
        try:
            digest = registry.register(manifest)
        except DuplicateVersionError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(code=1)

        console.print(
            f"[green]Registered {manifest.metadata.namespace}/{manifest.metadata.name}:{manifest.metadata.version}[/green]"
        )
        console.print(f"  Digest: sha256:{digest}")

    @artifact_app.command()
    def inspect(
        namespace: str = typer.Argument(..., help="Artifact namespace"),
        name: str = typer.Argument(..., help="Artifact name"),
        version: str = typer.Argument(..., help="Artifact version"),
        output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    ) -> None:
        """Show manifest details from registry."""
        registry = _get_registry()
        manifest = registry.get(namespace, name, version)
        if manifest is None:
            console.print(f"[red]Error: {namespace}/{name}:{version} not found[/red]")
            raise typer.Exit(code=1)

        if output_json:
            print(json.dumps(manifest.model_dump(mode="json"), indent=2))
        else:
            console.print(f"[bold]{namespace}/{name}:{version}[/bold]")
            console.print(f"  Kind:       {manifest.metadata.kind.value}")
            console.print(f"  Owner:      {manifest.metadata.owner}")
            console.print(f"  Digest:     sha256:{manifest.metadata.digest}")
            console.print(f"  Protocol:   {manifest.interface.protocol}")
            console.print(f"  Visibility: {manifest.governance.visibility.value}")
            console.print(f"  Status:     {manifest.governance.status.value}")
            if manifest.provides:
                console.print("  Provides:")
                for cap in manifest.provides:
                    console.print(f"    - {cap.capability}/{cap.contract}")
            if manifest.requires:
                console.print("  Requires:")
                for cap in manifest.requires:
                    console.print(f"    - {cap.capability}/{cap.contract}")

    return artifact_app


def make_search_command() -> typer.Typer:
    """Create the top-level search command."""
    search_app = typer.Typer()

    @search_app.callback(invoke_without_command=True)
    def search(
        query: str = typer.Argument(..., help="Search query"),
        output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    ) -> None:
        """Search for artifacts in the registry."""
        registry = _get_registry()
        results = registry.search(query)

        if output_json:
            data = [
                {
                    "namespace": r.namespace,
                    "name": r.name,
                    "kind": r.kind.value,
                    "version": r.version,
                    "digest": r.digest,
                }
                for r in results
            ]
            print(json.dumps(data, indent=2))
        elif not results:
            console.print("No results found.")
        else:
            table = Table()
            table.add_column("NAMESPACE")
            table.add_column("NAME")
            table.add_column("KIND")
            table.add_column("VERSION")
            for r in results:
                table.add_row(r.namespace, r.name, r.kind.value, r.version)
            console.print(table)

    return search_app


def make_tag_command() -> typer.Typer:
    """Create the top-level tag command."""
    tag_app = typer.Typer()

    @tag_app.callback(invoke_without_command=True)
    def tag(
        namespace: str = typer.Argument(..., help="Artifact namespace"),
        name: str = typer.Argument(..., help="Artifact name"),
        version: str = typer.Argument(..., help="Artifact version"),
        tag_name: str = typer.Argument(..., help="Tag name"),
    ) -> None:
        """Tag an artifact version."""
        registry = _get_registry()
        try:
            registry.tag(namespace, name, version, tag_name)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(code=1)
        console.print(
            f"[green]Tagged {namespace}/{name}:{version} as '{tag_name}'[/green]"
        )

    return tag_app


skill_app = _make_artifact_app(Kind.SKILL)
tool_app = _make_artifact_app(Kind.TOOL)
agent_app = _make_artifact_app(Kind.AGENT)
search_app = make_search_command()
tag_app = make_tag_command()
```

- [ ] **Step 4: Update CLI __init__.py to register commands**

`src/capmesh/cli/__init__.py`:
```python
import typer

from capmesh.cli.artifact_commands import (
    agent_app,
    search_app,
    skill_app,
    tag_app,
    tool_app,
)

app = typer.Typer(
    name="capmesh",
    help="Service discovery for the agentic world.",
    no_args_is_help=True,
)

app.add_typer(skill_app, name="skill")
app.add_typer(tool_app, name="tool")
app.add_typer(agent_app, name="agent")
app.add_typer(search_app, name="search")
app.add_typer(tag_app, name="tag")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/integration/test_cli.py -v
```

Expected: all PASSED

- [ ] **Step 6: Manually verify CLI works**

```bash
capmesh --help
capmesh agent --help
capmesh skill --help
capmesh tool --help
```

Expected: help text shows all subcommands.

- [ ] **Step 7: Commit**

```bash
git add src/capmesh/cli/ tests/integration/test_cli.py
git commit -m "feat: add CLI commands for artifact init, build, register, inspect, search, and tag"
```

---

### Task 8: Full Test Suite Verification and Coverage

**Files:**
- Modify: `pyproject.toml` (add coverage config)

**Interfaces:**
- Consumes: all previous tasks
- Produces: passing test suite with coverage report

- [ ] **Step 1: Add coverage configuration to pyproject.toml**

Append to `pyproject.toml`:
```toml
[tool.coverage.run]
source = ["src/capmesh"]

[tool.coverage.report]
show_missing = true
fail_under = 80
```

- [ ] **Step 2: Run full test suite with coverage**

```bash
pytest tests/ -v --cov=capmesh --cov-report=term-missing
```

Expected: all tests PASS, coverage >= 80%.

- [ ] **Step 3: Fix any failures or low-coverage areas**

If any tests fail, fix them. If coverage is below 80%, add tests for uncovered paths.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add test coverage configuration, verify full Phase 1 test suite"
```

---

## Phase 1 Completion Checklist

After all tasks are complete, verify these Phase 1 acceptance criteria:

- [ ] `pip install -e ".[dev]"` succeeds
- [ ] `capmesh --help` shows skill, tool, agent, search, tag subcommands
- [ ] `capmesh agent init` creates a valid manifest.yaml
- [ ] `capmesh agent build` validates and computes digest
- [ ] `capmesh agent register` stores manifest in YAML + SQLite
- [ ] `capmesh agent inspect` retrieves and displays manifest
- [ ] `capmesh search` finds artifacts by keyword
- [ ] `capmesh tag` tags an artifact version
- [ ] Duplicate version with different digest is rejected
- [ ] Duplicate version with same digest is idempotent
- [ ] `pytest tests/ -v` — all pass
- [ ] Coverage >= 80%
