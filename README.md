# CapMesh

**Service discovery for the agentic world.**

Dynamically discover and bind Agents, Skills and Tools by capability — not by name, not by framework, not by endpoint.

```python
# Your agent code — no tool imports, no hardcoded endpoints
binding = resolver.need("scan for security vulnerabilities")
# -> security/crewai-reviewer:3.1.0 via A2A protocol

binding = resolver.need("read code from a repo")
# -> repository/gitlab-reader:2.0.0 via MCP protocol
```

## Why CapMesh?

Today, every agent hardcodes its tools:

```python
# WITHOUT CapMesh — hardcoded everything
from tools.github import GitHubReader    # locked to GitHub
from tools.snyk import SnykScanner      # locked to Snyk
scanner = SnykScanner()                  # what if you switch to Semgrep?
```

With CapMesh, agents ask for **capabilities**, not tools:

```python
# WITH CapMesh — ask for what you need
repo = resolver.need("read a repository")       # gets GitHub, GitLab, or whatever is best
scanner = resolver.need("security scan")          # gets Snyk, Semgrep, or whatever is approved
```

Swap tools, upgrade versions, restrict access — **zero code changes**.

## Installation

```bash
pip install capmesh                # CLI + library
pip install "capmesh[server]"      # adds FastAPI registry server
```

## Quick Start

### 1. Write a manifest

```yaml
# manifest.yaml — describe what your tool/agent/skill provides
governance:
  status: approved
  visibility: public
interface:
  protocol: mcp
  server: github-mcp
  tool_name: read_file
metadata:
  api_version: capmesh.io/v1alpha1
  kind: tool
  name: github-reader
  namespace: repository
  owner: platform-team
  version: "1.0.0"
provides:
  - capability: repository.read
    contract: v1
    description: Read files and code from a git repository
requires: []
```

### 2. Build and register

```bash
capmesh tool build --directory ./my-tool/           # validate + compute digest
capmesh tool register --file ./my-tool/manifest.yaml  # store in registry
```

### 3. Discover and resolve

```bash
capmesh search "security"                            # find providers
capmesh providers security.code.review               # list all providers
capmesh resolve security.code.review                 # resolve to best provider
capmesh resolve security.code.review --trace         # show full decision trace
capmesh graph security.code.review --json            # dependency graph
```

### 4. Use in code

```python
from capmesh.registry import Registry
from capmesh.resolver import Resolver
from capmesh.policy import default_policy_engine
from capmesh.models.resolution import CallerContext

registry = Registry()
resolver = Resolver(registry=registry, policy_engine=default_policy_engine())

# Natural language
result = resolver.need("scan for security issues")
print(result.binding.protocol)    # "a2a"
print(result.binding.connection)  # {"endpoint": "https://scanner.example.com"}

# Or exact capability ID
from capmesh.models.resolution import ResolveRequest
result = resolver.resolve(ResolveRequest(
    capability="security.code.review",
    contract="v1",
    caller=CallerContext(identity="my-agent"),
))
```

### 5. Run the registry server

```bash
capmesh server start --port 8080
```

Agents call the HTTP API:

```bash
# Register a provider
curl -X POST http://localhost:8080/v1/providers/register \
  -H "Content-Type: application/json" -d @manifest.json

# Resolve a capability
curl -X POST http://localhost:8080/v1/resolve \
  -H "Content-Type: application/json" \
  -d '{"capability": "security.code.review", "contract": "v1",
       "caller": {"identity": "my-agent"}}'

# Query resolution trace
curl http://localhost:8080/v1/resolutions/{trace_id}
```

Or with Docker:
```bash
docker build -t capmesh-server .
docker run -p 8080:8080 -v capmesh-data:/data capmesh-server
```

## The Docker Analogy

```
Docker                          CapMesh
--------------------------      --------------------------
docker build                    capmesh tool build
docker push                     capmesh tool push
docker pull                     capmesh tool pull
docker images                   capmesh search
docker inspect                  capmesh agent inspect
docker tag                      capmesh tag
docker login                    capmesh login

# What Docker doesn't have:
                                capmesh resolve    (capability -> provider)
                                capmesh providers  (who provides X?)
                                capmesh graph      (dependency tree)
```

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Capability** | What a consumer needs (`security.code.review`, `repository.read`) |
| **Provider** | An Agent, Skill, or Tool that provides a capability |
| **Manifest** | YAML file describing a provider's capabilities, interface, and governance |
| **Resolution** | Finding the best provider for a capability (deterministic, auditable) |
| **Binding** | Protocol-specific connection info to call the provider |
| **Trace** | Full audit record of every resolution decision |
| **Contract** | API version for a capability (v1 never silently becomes v2) |

## Three Provider Types

| Type | Protocol | Purpose | Example |
|------|----------|---------|---------|
| **Tool** | MCP, REST | Executable capability | GitHub MCP server, REST API |
| **Agent** | A2A | Autonomous service | LangGraph security reviewer |
| **Skill** | Skill | Procedural instructions | SKILL.md + auto-resolved tool deps |

## Architecture

```
+------------------+       +------------------+       +------------------+
|   Your Agent     |       |  CapMesh Server  |       |  Providers       |
|                  | HTTP  |                  |       |                  |
|  "I need         |------>|  Registry        |       |  MCP servers     |
|   security.scan" |       |  Resolver        |       |  A2A agents      |
|                  |<------|  Policy Engine   |       |  REST APIs       |
|  {provider,      |       |  Trace Store     |       |  Skills          |
|   protocol,      |       +------------------+       +------------------+
|   endpoint}      |              |
+-----|------------+              | SQLite + YAML
      v
  Call provider directly
  using returned binding
```

## Demo

```bash
# Full demo with 34 providers across 5 frameworks
python demo/registry/generate_providers.py
python demo/app.py

# Step-by-step
python demo/01_build.py           # validate manifests
python demo/02_register.py        # register in registry
python demo/03_resolve.py         # resolve capabilities
python demo/04_benefits.py        # WITH vs WITHOUT comparison
python demo/05_production.py      # production architecture
python demo/06_governance.py      # security & governance controls
python demo/07_natural_language.py # natural language discovery
```

## Governance & Security

CapMesh gives organizations **more control**, not less:

| Control | How |
|---------|-----|
| **Approval workflow** | `status: approved/deprecated/revoked` — nothing runs without sign-off |
| **Environment isolation** | `environment: [production]` — staging can't access prod tools |
| **Visibility** | `visibility: private/organization/public` — access control in YAML |
| **Version pinning** | `version_constraint: ">=2.0,<3.0"` — no surprise upgrades |
| **Immutability** | Same version + different content = rejected (digest mismatch) |
| **Deprecation** | Graceful sunset — agents auto-fallback to next best version |
| **Audit trail** | Every resolution traced: who, what, when, why |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache 2.0
