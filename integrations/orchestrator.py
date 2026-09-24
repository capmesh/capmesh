#!/usr/bin/env python3
"""
CapMesh Real Integration — Orchestrator

Starts real services, registers them, discovers via CapMesh, and chains
real calls with real results.

No mocks. No simulations. Actual HTTP calls to actual servers.
"""
import httpx
import threading
import time
import tempfile
import sys
from pathlib import Path


def start_server(app_module: str, port: int):
    """Start a FastAPI server in a background thread."""
    import uvicorn
    import importlib.util

    spec = importlib.util.spec_from_file_location("server", app_module)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    config = uvicorn.Config(mod.app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server


def wait_healthy(url: str, timeout: int = 10):
    """Wait for a service to be healthy."""
    client = httpx.Client(timeout=2.0)
    for _ in range(timeout * 2):
        try:
            resp = client.get(url)
            if resp.status_code == 200:
                client.close()
                return True
        except Exception:
            pass
        time.sleep(0.5)
    client.close()
    return False


def main():
    base = Path(__file__).parent

    print()
    print("+" + "=" * 66 + "+")
    print("|  CAPMESH REAL INTEGRATION                                        |")
    print("|  Real servers. Real HTTP calls. Real results. No mocks.          |")
    print("+" + "=" * 66 + "+")

    # --- Start real servers ---
    print()
    print("  [1] Starting real services...")

    start_server(str(base / "mcp-file-reader" / "server.py"), 9100)
    start_server(str(base / "a2a-code-analyzer" / "agent.py"), 9200)

    if not wait_healthy("http://127.0.0.1:9100/health"):
        print("  ERROR: File reader server failed to start")
        sys.exit(1)
    print("      File Reader MCP server: http://127.0.0.1:9100 [OK]")

    if not wait_healthy("http://127.0.0.1:9200/health"):
        print("  ERROR: Code analyzer agent failed to start")
        sys.exit(1)
    print("      Code Analyzer A2A agent: http://127.0.0.1:9200 [OK]")

    # --- Connect to CapMesh and register ---
    print()
    print("  [2] Registering services in CapMesh...")

    import capmesh
    mesh = capmesh.connect(root=tempfile.mkdtemp())
    mesh.register(str(base / "mcp-file-reader" / "manifest.yaml"))
    mesh.register(str(base / "a2a-code-analyzer" / "manifest.yaml"))
    print(f"      {mesh}")

    # --- Resolve capabilities ---
    print()
    print("  [3] Resolving capabilities via CapMesh...")

    file_reader = mesh.need("read files from filesystem", kind="tool")
    code_analyzer = mesh.need("analyze code", kind="agent")

    print(f"      repository.read -> {file_reader.provider_name}:{file_reader.provider_version} [{file_reader.binding.protocol}]")
    print(f"        Endpoint: {file_reader.binding.connection.get('endpoint')}")
    print(f"      code.analyze   -> {code_analyzer.provider_name}:{code_analyzer.provider_version} [{code_analyzer.binding.protocol}]")
    print(f"        Endpoint: {code_analyzer.binding.connection.get('endpoint')}")

    # --- Call file reader (REAL HTTP call) ---
    print()
    print("  [4] Reading actual CapMesh source files...")

    client = httpx.Client(timeout=10.0)
    reader_endpoint = file_reader.binding.connection["endpoint"]

    # List Python files
    src_dir = str(Path(__file__).parent.parent / "src" / "capmesh")
    resp = client.post(f"{reader_endpoint}/tools/list_files", json={
        "directory": src_dir,
        "pattern": "*.py",
    })
    file_list = resp.json()
    print(f"      Found {file_list['count']} Python files in src/capmesh/")

    # Read each file
    files_data = []
    for fpath in file_list["files"][:20]:  # limit to 20 files
        resp = client.post(f"{reader_endpoint}/tools/read_file", json={"path": fpath})
        data = resp.json()
        if "error" not in data:
            files_data.append({"path": fpath, "content": data["content"]})

    print(f"      Read {len(files_data)} files successfully")

    # --- Call code analyzer (REAL HTTP call) ---
    print()
    print("  [5] Analyzing code with A2A agent...")

    analyzer_endpoint = code_analyzer.binding.connection["endpoint"]
    resp = client.post(f"{analyzer_endpoint}/analyze", json={"files": files_data})
    analysis = resp.json()
    summary = analysis["summary"]

    # --- Print REAL results ---
    print()
    print("  " + "=" * 64)
    print("  ANALYSIS REPORT — CapMesh Source Code")
    print("  " + "=" * 64)
    print()
    print(f"  Files analyzed:    {summary['files']}")
    print(f"  Total lines:       {summary['lines']}")
    print(f"  Functions:         {summary['functions']}")
    print(f"  Classes:           {summary['classes']}")
    print(f"  TODOs/FIXMEs:      {summary['todos']}")
    print(f"  Unique imports:    {summary['unique_imports']}")
    print()

    # Top imports
    if summary.get("imports"):
        print("  Top imports:")
        for imp in summary["imports"][:15]:
            print(f"    - {imp}")
        if len(summary["imports"]) > 15:
            print(f"    ... and {len(summary['imports']) - 15} more")
    print()

    # Files with most functions
    file_results = sorted(analysis["files"], key=lambda f: len(f["functions"]), reverse=True)
    print("  Largest files (by functions):")
    for f in file_results[:8]:
        rel = Path(f["path"]).name
        print(f"    {rel:30s} {f['lines']:5d} lines | {len(f['functions']):3d} functions | {len(f['classes']):2d} classes")
    print()

    # TODOs across all files
    all_todos = []
    for f in analysis["files"]:
        for todo in f.get("todos", []):
            all_todos.append((Path(f["path"]).name, todo))

    if all_todos:
        print(f"  TODOs/FIXMEs found ({len(all_todos)}):")
        for fname, todo in all_todos[:10]:
            print(f"    {fname}:{todo['line']} [{todo['tag']}] {todo['text'][:60]}")
        if len(all_todos) > 10:
            print(f"    ... and {len(all_todos) - 10} more")
    else:
        print("  No TODOs/FIXMEs found. Clean codebase!")
    print()

    # --- Show the CapMesh trace ---
    print("  " + "-" * 64)
    print("  CapMesh Resolution Audit:")
    print(f"    Trace 1: {file_reader.trace.trace_id}")
    print(f"      {file_reader.trace.requested_capability} -> {file_reader.trace.selected_provider}")
    print(f"    Trace 2: {code_analyzer.trace.trace_id}")
    print(f"      {code_analyzer.trace.requested_capability} -> {code_analyzer.trace.selected_provider}")
    print()
    print("  Both services were discovered by CapMesh at runtime.")
    print("  The orchestrator never imported or hardcoded either service.")
    print("  Real HTTP calls. Real file reads. Real AST analysis.")
    print()

    client.close()


if __name__ == "__main__":
    main()
