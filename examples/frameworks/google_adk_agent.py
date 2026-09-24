#!/usr/bin/env python3
"""
Google Agent Development Kit (ADK) using CapMesh for capability discovery.

Google ADK agents resolve tools from CapMesh at runtime.
"""
# pip install google-adk capmesh

# --- WITHOUT CapMesh (hardcoded) ---
#
# from google.adk import Agent
# from google.adk.tools import google_search, code_execution
# agent = Agent(
#     model="gemini-2.0-flash",
#     tools=[google_search, code_execution],  # HARDCODED to Google tools
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

caller = CallerContext(identity="google-adk-agent", environment="production")


def resolve_tools(*capabilities):
    """Resolve multiple capabilities from CapMesh."""
    tools = []
    for cap in capabilities:
        result = resolver.need(cap, caller=caller)
        tools.append({
            "capability": cap,
            "provider": f"{result.provider_namespace}/{result.provider_name}:{result.provider_version}",
            "protocol": result.binding.protocol,
            "connection": result.binding.connection,
        })
    return tools


# Google ADK integration:
#
# from google.adk import Agent
# from google.adk.tools import FunctionTool
#
# # Resolve tools from CapMesh
# bindings = resolve_tools("read repository", "security scan", "create issue")
#
# # Convert CapMesh bindings to ADK FunctionTools
# adk_tools = []
# for b in bindings:
#     if b["protocol"] == "mcp":
#         adk_tools.append(FunctionTool(
#             name=b["capability"],
#             fn=lambda **kw: mcp_client.call(b["connection"]["server"], kw),
#         ))
#     elif b["protocol"] == "a2a":
#         adk_tools.append(FunctionTool(
#             name=b["capability"],
#             fn=lambda **kw: a2a_client.call(b["connection"]["endpoint"], kw),
#         ))
#
# agent = Agent(
#     model="gemini-2.0-flash",
#     tools=adk_tools,  # DYNAMIC — resolved by CapMesh
# )
# result = agent.run("Review this repository for security issues")

print("Google ADK + CapMesh Integration")
tools = resolve_tools("read a repository", "security scan", "send notification")
for t in tools:
    print(f"  {t['capability']:25s} -> {t['provider']} ({t['protocol']})")
    print(f"    Connection: {t['connection']}")
print()
print("  Google ADK agents use CapMesh-resolved tools.")
print("  Not locked to Google's tool ecosystem — any MCP/A2A/REST provider works.")
