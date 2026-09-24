"""
MCP File Reader Server — REST API that mimics what an MCP-over-HTTP server exposes.

Runs on port 9100. Exposes two tools:
  - read_file(path): Returns file content
  - list_files(directory, pattern): Returns file listing

No authentication required.
"""
from fastapi import FastAPI
import os
import glob as glob_module

app = FastAPI(title="File Reader MCP Server")


@app.post("/tools/read_file")
async def read_file(request: dict):
    path = request.get("path", "")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {"content": content, "path": path, "size": len(content)}
    except Exception as e:
        return {"error": str(e), "path": path}


@app.post("/tools/list_files")
async def list_files(request: dict):
    directory = request.get("directory", ".")
    pattern = request.get("pattern", "*.py")
    files = glob_module.glob(os.path.join(directory, "**", pattern), recursive=True)
    return {"files": files, "count": len(files), "directory": directory}


@app.get("/health")
async def health():
    return {"status": "ok", "name": "file-reader-mcp"}
