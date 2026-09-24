# CapMesh Framework Integration Examples

Every framework resolves tools the same way — one HTTP call to CapMesh.

## Supported Frameworks

| Framework | File | Pattern |
|-----------|------|---------|
| **CrewAI** | `crewai_agent.py` | Resolve capabilities, build CrewAI tools from bindings |
| **LangGraph** | `langgraph_agent.py` | Resolve tools, use as LangChain tool functions |
| **AWS Strands** | `strands_agent.py` | Resolve, build MCPTool/HTTPTool from bindings |
| **Microsoft AutoGen** | `autogen_agent.py` | Resolve, register as AutoGen function tools |
| **Google ADK** | `google_adk_agent.py` | Resolve, create ADK FunctionTools |
| **OpenAI Agents** | `openai_agent.py` | Resolve, generate function-calling schemas |
| **Semantic Kernel** | `semantic_kernel_agent.py` | Resolve, create SK kernel functions |
| **Raw HTTP** | `httpx_raw.py` | Any language — Python, JS, Go, Java, curl |

## The Pattern (same for every framework)

```python
# 1. Connect to CapMesh
resolver = Resolver(registry=Registry(), policy_engine=default_policy_engine())

# 2. Resolve capabilities (natural language or exact ID)
binding = resolver.need("read a repository")

# 3. Use the binding in your framework
if binding.binding.protocol == "mcp":
    tool = YourFramework.MCPTool(server=binding.binding.connection["server"])
elif binding.binding.protocol == "a2a":
    tool = YourFramework.A2ATool(endpoint=binding.binding.connection["endpoint"])
elif binding.binding.protocol == "rest":
    tool = YourFramework.HTTPTool(url=binding.binding.connection["endpoint"])
```

The framework-specific code is just the adapter from CapMesh binding to framework tool type. The discovery, versioning, policy, and audit are all handled by CapMesh.
