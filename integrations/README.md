# CapMesh Real Integration Demo

A real end-to-end integration demo showing CapMesh service discovery with:

- A **real MCP-style file reader server** (REST over HTTP, port 9100)
- A **real A2A code analyzer agent** (FastAPI with Python AST, port 9200)
- An **orchestrator** that starts both servers, registers them in CapMesh, resolves
  capabilities via `mesh.need()`, and chains live HTTP calls

## What it demonstrates

1. **MCP File Reader** (`mcp-file-reader/`) — REST server exposing `read_file` and
   `list_files` tools. Uses the `rest` protocol in its manifest; CapMesh resolves the
   endpoint and the orchestrator calls the real `/tools/*` routes.

2. **A2A Code Analyzer** (`a2a-code-analyzer/`) — FastAPI agent that parses Python
   code with the `ast` module and returns line counts, function/class inventories,
   imports, and TODO/FIXME locations.

3. **Orchestrator** (`orchestrator.py`) — Starts both servers, waits for health checks,
   registers their manifests, calls `mesh.need("read files from filesystem", kind="tool")`
   and `mesh.need("analyze code", kind="agent")`, then follows the resolved endpoints for
   real HTTP calls. Produces a real analysis report of the CapMesh source itself.

## Prerequisites

```
pip install fastapi uvicorn httpx
```

The demo also requires `capmesh` itself (install from the repo root):

```
pip install -e .
```

## Running

```bash
cd integrations
python orchestrator.py
```

The orchestrator will:

1. Start the file reader on port 9100 and the code analyzer on port 9200 (background threads)
2. Register both manifest files into a temporary CapMesh registry
3. Resolve `repository.read` and `code.analyze` through `mesh.need()`
4. Read up to 20 Python files from `src/capmesh/` via the file reader server
5. Send all file contents to the code analyzer and print a real analysis report
6. Print the CapMesh resolution traces (trace IDs, selected providers, protocols)

## File layout

```
integrations/
  mcp-file-reader/
    server.py          # FastAPI REST server, port 9100
    manifest.yaml      # CapMesh manifest (protocol: rest)
  a2a-code-analyzer/
    agent.py           # FastAPI A2A agent, port 9200
    manifest.yaml      # CapMesh manifest (protocol: a2a)
  orchestrator.py      # Starts services, registers, resolves, calls, reports
  README.md            # This file
```

## No mocks

Every step uses real code paths:

- `mesh.register()` parses the YAML and writes to a local SQLite registry
- `mesh.need()` runs keyword/synonym-based capability discovery
- HTTP calls go to actual `uvicorn`-served FastAPI applications
- Code analysis uses `ast.parse()` on the real CapMesh source files
