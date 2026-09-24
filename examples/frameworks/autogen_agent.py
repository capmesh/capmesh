#!/usr/bin/env python3
"""
Microsoft AutoGen Agent using CapMesh for capability discovery.

AutoGen agents resolve tools from CapMesh instead of hardcoding.
"""
# pip install autogen-agentchat capmesh

# --- WITHOUT CapMesh (hardcoded) ---
#
# from autogen import AssistantAgent, UserProxyAgent
# assistant = AssistantAgent(
#     "security_reviewer",
#     llm_config={"tools": [github_tool_schema]},  # HARDCODED
# )

# --- WITH CapMesh ---

from capmesh.resolver import Resolver
from capmesh.registry import Registry
from capmesh.policy import default_policy_engine
from capmesh.models.resolution import CallerContext

resolver = Resolver(
    registry=Registry(),
    policy_engine=default_policy_engine(),
)

caller = CallerContext(identity="autogen-orchestrator")


def capmesh_tool(capability: str):
    """Create a tool function that calls a CapMesh-resolved provider."""
    result = resolver.need(capability, caller=caller)
    conn = result.binding.connection

    def tool_fn(**kwargs):
        # In real code: call the provider using its protocol
        # if result.binding.protocol == "a2a":
        #     return a2a_client.call(conn["endpoint"], kwargs)
        # elif result.binding.protocol == "mcp":
        #     return mcp_client.call(conn["server"], kwargs)
        return {"provider": result.provider_name, "protocol": result.binding.protocol, **kwargs}

    tool_fn.__name__ = capability.replace(".", "_")
    tool_fn.__doc__ = f"Resolved via CapMesh: {result.provider_name}:{result.provider_version}"
    return tool_fn, result


# AutoGen integration:
#
# from autogen import AssistantAgent, UserProxyAgent
#
# # Resolve tools from CapMesh
# read_repo, read_info = capmesh_tool("repository.read")
# scan_code, scan_info = capmesh_tool("security.code.review")
#
# # Register as AutoGen tools
# assistant = AssistantAgent("reviewer", llm_config={...})
# assistant.register_function({"read_repo": read_repo, "scan_code": scan_code})
#
# user_proxy = UserProxyAgent("user")
# user_proxy.initiate_chat(assistant, message="Review PR #42")

print("AutoGen + CapMesh Integration")
for cap in ["repository.read", "security.code.review", "notification.send"]:
    fn, info = capmesh_tool(cap)
    print(f"  Tool: {fn.__name__}")
    print(f"    {fn.__doc__}")
    print(f"    Protocol: {info.binding.protocol}")
    print(f"    Connection: {info.binding.connection}")
    print()
print("  AutoGen agents get tools resolved from CapMesh.")
print("  Tool functions are generated dynamically — no hardcoded imports.")
