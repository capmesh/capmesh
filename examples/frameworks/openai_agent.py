#!/usr/bin/env python3
"""
OpenAI Agents SDK using CapMesh for capability discovery.

OpenAI agents resolve tools from CapMesh instead of hardcoding function schemas.
"""
# pip install openai capmesh

# --- WITHOUT CapMesh (hardcoded) ---
#
# from openai import OpenAI
# tools = [
#     {"type": "function", "function": {"name": "read_repo", ...}},  # HARDCODED
#     {"type": "function", "function": {"name": "scan_code", ...}},  # HARDCODED
# ]

# --- WITH CapMesh ---

from capmesh.resolver import Resolver
from capmesh.registry import Registry
from capmesh.policy import default_policy_engine
from capmesh.models.resolution import CallerContext

resolver = Resolver(
    registry=Registry(),
    policy_engine=default_policy_engine(),
)

caller = CallerContext(identity="openai-agent")


def make_tool_handler(capability: str):
    """Resolve a capability and return a handler + schema for OpenAI function calling."""
    result = resolver.need(capability, caller=caller)
    conn = result.binding.connection

    def handler(**kwargs):
        # Call the resolved provider
        # if result.binding.protocol == "a2a":
        #     return a2a_client.call(conn["endpoint"], kwargs)
        # elif result.binding.protocol == "mcp":
        #     return mcp_client.call(conn["server"], kwargs)
        return {"provider": result.provider_name, **kwargs}

    schema = {
        "type": "function",
        "function": {
            "name": capability.replace(".", "_"),
            "description": f"Resolved via CapMesh: {result.provider_name}:{result.provider_version} ({result.binding.protocol})",
            "parameters": {"type": "object", "properties": {}},
        }
    }
    return handler, schema, result


# OpenAI integration:
#
# from openai import OpenAI
# client = OpenAI()
#
# # Resolve tools from CapMesh
# read_fn, read_schema, _ = make_tool_handler("repository.read")
# scan_fn, scan_schema, _ = make_tool_handler("security.code.review")
#
# response = client.chat.completions.create(
#     model="gpt-4",
#     messages=[{"role": "user", "content": "Review PR #42"}],
#     tools=[read_schema, scan_schema],  # DYNAMIC schemas from CapMesh
# )
#
# # When OpenAI calls the tool, dispatch to CapMesh-resolved provider
# for tool_call in response.choices[0].message.tool_calls:
#     if tool_call.function.name == "repository_read":
#         result = read_fn(**json.loads(tool_call.function.arguments))

print("OpenAI Agents + CapMesh Integration")
for cap in ["repository.read", "security.code.review", "notification.send"]:
    handler, schema, info = make_tool_handler(cap)
    print(f"  Tool: {schema['function']['name']}")
    print(f"    {schema['function']['description']}")
    print(f"    Connection: {info.binding.connection}")
print()
print("  OpenAI function-calling tools are resolved from CapMesh.")
print("  Tool schemas are generated dynamically — providers can change anytime.")
