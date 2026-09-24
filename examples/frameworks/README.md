# CapMesh Framework Integration Examples

Every framework uses the same 3-line pattern:

```python
import capmesh

mesh = capmesh.connect()
result = mesh.need("what I need", kind="tool")  # or kind="agent", protocol="mcp", etc.
# Use result.binding.connection to call the provider
```

## Examples

| Framework | File | Key line |
|-----------|------|----------|
| **CrewAI** | `crewai_agent.py` | `mesh.need("read a repo", kind="tool", protocol="mcp")` |
| **LangGraph** | `langgraph_agent.py` | `mesh.need("security review", kind="agent")` |
| **AWS Strands** | `strands_agent.py` | `mesh.need("read repo", kind="tool", protocol="mcp")` |
| **AutoGen** | `autogen_agent.py` | `mesh.need("security scan", kind="agent")` |
| **Google ADK** | `google_adk_agent.py` | `mesh.need("read a repo", kind="tool")` |
| **OpenAI** | `openai_agent.py` | `mesh.need("repository.read", kind="tool")` |
| **Semantic Kernel** | `semantic_kernel_agent.py` | `mesh.need("read a repo", kind="tool")` |
| **Any language** | `httpx_raw.py` | `POST /v1/resolve` (Python, JS, Go, Java, curl) |

## CLI

```bash
capmesh resolve "security scan"                           # any
capmesh resolve "security scan" --kind agent              # agents only
capmesh resolve "read a repo" --protocol mcp              # MCP only
capmesh resolve security.code.review -k agent -p a2a      # exact + filters
capmesh resolve security.code.review --trace              # with decision trace
```
