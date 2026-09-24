"""
Code Analyzer A2A Agent — Analyzes Python code using real AST parsing.

Runs on port 9200. Exposes:
  - POST /analyze: Accepts {"files": [{"path": "...", "content": "..."}]}
    Returns real analysis: line count, function count, class count, TODOs, imports.
"""
from fastapi import FastAPI
import ast

app = FastAPI(title="Code Analyzer A2A Agent")


def analyze_python(content: str, path: str) -> dict:
    lines = content.split("\n")
    result = {
        "path": path,
        "lines": len(lines),
        "blank_lines": sum(1 for l in lines if not l.strip()),
        "comment_lines": sum(1 for l in lines if l.strip().startswith("#")),
        "todos": [],
        "functions": [],
        "classes": [],
        "imports": [],
    }

    # Find TODOs/FIXMEs
    for i, line in enumerate(lines, 1):
        for tag in ["TODO", "FIXME", "HACK", "XXX"]:
            if tag in line:
                result["todos"].append({"line": i, "tag": tag, "text": line.strip()})

    # Parse AST
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                result["functions"].append({"name": node.name, "line": node.lineno, "args": len(node.args.args)})
            elif isinstance(node, ast.ClassDef):
                result["classes"].append({"name": node.name, "line": node.lineno})
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    result["imports"].append(node.module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        result["imports"].append(alias.name)
    except SyntaxError:
        result["parse_error"] = True

    return result


@app.post("/analyze")
async def analyze(request: dict):
    files = request.get("files", [])
    results = []
    totals = {"files": 0, "lines": 0, "functions": 0, "classes": 0, "todos": 0, "imports": set()}

    for f in files:
        analysis = analyze_python(f["content"], f["path"])
        results.append(analysis)
        totals["files"] += 1
        totals["lines"] += analysis["lines"]
        totals["functions"] += len(analysis["functions"])
        totals["classes"] += len(analysis["classes"])
        totals["todos"] += len(analysis["todos"])
        totals["imports"].update(analysis["imports"])

    totals["imports"] = sorted(totals["imports"])
    totals["unique_imports"] = len(totals["imports"])

    return {"files": results, "summary": totals}


@app.get("/health")
async def health():
    return {"status": "ok", "name": "code-analyzer-a2a"}
