#!/usr/bin/env python3
"""Microsoft AutoGen + CapMesh — generate tool functions dynamically."""
# pip install autogen-agentchat capmesh

import capmesh

mesh = capmesh.connect()


def capmesh_tool(query: str, **filters):
    """Resolve a capability and return a callable tool function."""
    result = mesh.need(query, **filters)
    conn = result.binding.connection

    def tool_fn(**kwargs):
        if result.binding.protocol == "a2a":
            return {"call": conn["endpoint"], **kwargs}
        elif result.binding.protocol == "mcp":
            return {"call": conn["server"], **kwargs}
        elif result.binding.protocol == "rest":
            return {"call": conn["endpoint"], **kwargs}

    tool_fn.__name__ = query.replace(" ", "_")
    tool_fn.__doc__ = f"{result.provider_name}:{result.provider_version} via {result.binding.protocol}"
    return tool_fn


# Create tools
read_repo = capmesh_tool("read a repository", kind="tool")
scan_code = capmesh_tool("security scan", kind="agent")

# AutoGen integration:
# from autogen import AssistantAgent, UserProxyAgent
# assistant = AssistantAgent("reviewer", llm_config={...})
# assistant.register_function({"read_repo": read_repo, "scan_code": scan_code})

print("AutoGen + CapMesh")
for fn in [read_repo, scan_code]:
    print(f"  {fn.__name__}: {fn.__doc__}")
