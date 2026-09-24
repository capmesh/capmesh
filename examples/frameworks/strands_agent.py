#!/usr/bin/env python3
"""
AWS Strands Agent using CapMesh for capability discovery.

Strands agents discover tools via CapMesh instead of hardcoding.
"""
# pip install strands-agents capmesh

# --- WITHOUT CapMesh (hardcoded) ---
#
# from strands import Agent
# from strands.tools import MCPTool
# agent = Agent(
#     tools=[MCPTool("github-mcp")],  # HARDCODED MCP server
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

caller = CallerContext(identity="strands-orchestrator", environment="production")

# Strands integration:
#
# from strands import Agent
# from strands.tools import MCPTool, HTTPTool
#
# # Resolve tools from CapMesh
# repo = resolver.need("read a repository", caller=caller)
# scan = resolver.need("security scan", caller=caller)
#
# # Build Strands tools from CapMesh bindings
# tools = []
# for binding in [repo, scan]:
#     b = binding.binding
#     if b.protocol == "mcp":
#         tools.append(MCPTool(b.connection["server"]))
#     elif b.protocol == "rest":
#         tools.append(HTTPTool(b.connection["endpoint"]))
#     elif b.protocol == "a2a":
#         tools.append(A2ATool(b.connection["endpoint"]))
#
# agent = Agent(tools=tools)
# result = agent("Review PR #42 for security issues")

print("Strands + CapMesh Integration")
for cap in ["read a repository", "security scan"]:
    result = resolver.need(cap, caller=caller)
    b = result.binding
    print(f"  {cap:25s} -> {result.provider_name}:{result.provider_version}")
    print(f"    Protocol: {b.protocol}")
    print(f"    Connection: {b.connection}")
print()
print("  Strands agent tools are resolved dynamically.")
print("  MCP servers, A2A agents, REST APIs — all discovered via CapMesh.")
