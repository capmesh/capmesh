# CapMesh

**Service discovery for the agentic world.**

Dynamically discover and bind Agents, Skills and Tools by capability — not by name, not by framework, not by endpoint.

```python
import capmesh

mesh = capmesh.connect()

# Natural language — find what you need
result = mesh.need("scan for security vulnerabilities")
result = mesh.need("read code from a repo")
result = mesh.need("notify the team")

# Filter by type
result = mesh.need("security review", kind="agent")       # only agents
result = mesh.need("security review", kind="skill")       # only skills
result = mesh.need("read a repo", kind="tool")            # only tools

# Filter by protocol
result = mesh.need("read a repo", protocol="mcp")         # only MCP servers
result = mesh.need("security scan", protocol="a2a")       # only A2A agents
result = mesh.need("analyze code", protocol="rest")       # only REST APIs

# Use the result
print(result.binding.protocol)      # "a2a"
print(result.binding.connection)    # {"endpoint": "https://scanner.example.com"}
```

## Why CapMesh?

```python
# WITHOUT CapMesh — hardcoded everything
from tools.github import GitHubReader    # locked to GitHub
from tools.snyk import SnykScanner      # locked to Snyk

# WITH CapMesh — ask for what you need
mesh = capmesh.connect()
repo = mesh.need("read a repository")       # gets GitHub, GitLab, or whatever is best
scanner = mesh.need("security scan")         # gets Snyk, Semgrep, or whatever is approved
```

Swap tools, upgrade versions, restrict access — **zero code changes**.

## Install

```bash
pip install capmesh                # CLI + library
pip install "capmesh[server]"      # adds registry server
```

## Quick Start

### 1. Write a manifest

```yaml
# manifest.yaml
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
    description: Read files from a git repository
requires: []
```

### 2. Build and register

```bash
capmesh tool build --directory ./my-tool/
capmesh tool register --file ./my-tool/manifest.yaml
```

### 3. Use in code

```python
import capmesh

mesh = capmesh.connect()

# Find and use a capability
result = mesh.need("read a repository")
print(result.provider_name)          # "github-reader"
print(result.binding.protocol)       # "mcp"
print(result.binding.connection)     # {"server": "github-mcp", "tool_name": "read_file"}

# Filter by what you want
agent = mesh.need("security review", kind="agent")           # only agents
tool = mesh.need("read a repo", kind="tool", protocol="mcp") # MCP tools only
skill = mesh.need("code review", kind="skill")               # only skills
```

### 4. Or use the CLI

```bash
# Resolve (natural language or exact ID)
capmesh resolve "security scan"
capmesh resolve security.code.review
capmesh resolve security.code.review --kind agent
capmesh resolve "read a repo" --protocol mcp
capmesh resolve security.code.review --kind agent --protocol a2a

# With trace
capmesh resolve security.code.review --trace

# Other commands
capmesh search "security"
capmesh providers security.code.review
capmesh graph security.code.review
capmesh tag security reviewer 2.4.0 stable
```

### 5. Run the registry server

```bash
capmesh server start --port 8080
```

Agents call via HTTP:
```bash
curl -X POST http://localhost:8080/v1/resolve \
  -H "Content-Type: application/json" \
  -d '{"capability": "security.code.review", "contract": "v1",
       "caller": {"identity": "my-agent"}}'
```

Or Docker:
```bash
docker build -t capmesh-server .
docker run -p 8080:8080 -v capmesh-data:/data capmesh-server
```

## CLI Reference (Docker Analogy)

```
Docker                          CapMesh
--------------------------      --------------------------
docker build                    capmesh tool build
docker push                     capmesh tool push
docker pull                     capmesh tool pull
docker images                   capmesh search
docker inspect                  capmesh tool inspect
docker tag                      capmesh tag
docker login                    capmesh login
docker run (registry)           capmesh server start

                                # CapMesh only:
                                capmesh resolve       (capability -> provider)
                                capmesh resolve -k    (filter by kind)
                                capmesh resolve -p    (filter by protocol)
                                capmesh providers     (who provides X?)
                                capmesh graph         (dependency tree)
```

## Framework Integration

Every framework uses the same pattern:

```python
import capmesh

mesh = capmesh.connect()

# CrewAI
repo = mesh.need("read a repo", protocol="mcp")
# -> MCPTool(server=repo.binding.connection["server"])

# LangGraph
scan = mesh.need("security scan", kind="agent")
# -> @tool wrapper calling scan.binding.connection["endpoint"]

# Strands
tool = mesh.need("read a repo", kind="tool")
# -> MCPTool(tool.binding.connection["server"])

# OpenAI / Google ADK / AutoGen / Semantic Kernel
# Same pattern — resolve, get binding, wrap in framework tool type
```

See [examples/frameworks/](examples/frameworks/) for complete integration code for 8 frameworks.

## Governance

| Control | How |
|---------|-----|
| **Approval** | `status: approved/deprecated/revoked` |
| **Environment** | `environment: [production]` — staging can't access prod |
| **Visibility** | `visibility: private/organization/public` |
| **Version pinning** | `mesh.need("scan", version=">=2.0,<3.0")` |
| **Immutability** | Same version + different content = rejected |
| **Audit** | Every resolution traced: who, what, when, why |

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
python demo/06_governance.py      # security & governance
python demo/07_natural_language.py # natural language discovery
```

## Architecture

```
Your Agent App              CapMesh Server              Providers
+------------------+       +------------------+       +------------------+
|                  |       |                  |       |                  |
|  mesh.need(...)  | ----> |  Registry        |       |  MCP servers     |
|  mesh.resolve(.) |       |  Resolver        |       |  A2A agents      |
|                  | <---- |  Policy Engine   |       |  REST APIs       |
|  {protocol,      |       |  Trace Store     |       |  Skills          |
|   connection}    |       |  Cache           |       |                  |
+-----|------------+       +------------------+       +------------------+
      |
      v
  Call provider directly
  using returned binding
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache 2.0
