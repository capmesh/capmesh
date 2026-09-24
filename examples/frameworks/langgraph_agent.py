#!/usr/bin/env python3
"""
LangGraph Agent using CapMesh for capability discovery.

The agent's tools are resolved at runtime, not hardcoded.
"""
# pip install langgraph capmesh

# --- WITHOUT CapMesh (hardcoded) ---
#
# from langchain_community.tools import GitHubSearchTool  # LOCKED
# from langchain_community.tools import SlackSendMessage  # LOCKED
# tools = [GitHubSearchTool(), SlackSendMessage()]         # HARDCODED

# --- WITH CapMesh ---

from capmesh.resolver import Resolver
from capmesh.registry import Registry
from capmesh.policy import default_policy_engine
from capmesh.models.resolution import CallerContext

resolver = Resolver(
    registry=Registry(),
    policy_engine=default_policy_engine(),
)

caller = CallerContext(identity="langgraph-orchestrator", environment="production")


def resolve_tool(capability: str):
    """Resolve a CapMesh capability and return tool config."""
    result = resolver.need(capability, caller=caller)
    return {
        "provider": f"{result.provider_namespace}/{result.provider_name}:{result.provider_version}",
        "protocol": result.binding.protocol,
        "connection": result.binding.connection,
    }


# LangGraph integration:
#
# from langgraph.graph import StateGraph
# from langchain_core.tools import tool
#
# # Resolve tools from CapMesh
# repo_config = resolve_tool("read repository code")
# scan_config = resolve_tool("security scan")
# notify_config = resolve_tool("send notification")
#
# @tool
# def read_repo(repo: str) -> dict:
#     """Read repository files."""
#     if repo_config["protocol"] == "mcp":
#         return mcp_client.call(repo_config["connection"]["server"], {"repo": repo})
#     elif repo_config["protocol"] == "rest":
#         return httpx.get(repo_config["connection"]["endpoint"], params={"repo": repo}).json()
#
# @tool
# def security_scan(files: list) -> dict:
#     """Run security scan via resolved provider."""
#     return a2a_client.call(scan_config["connection"]["endpoint"], {"files": files})
#
# # Build graph
# graph = StateGraph(...)
# graph.add_node("read", read_repo)
# graph.add_node("scan", security_scan)
# graph.add_edge("read", "scan")
# app = graph.compile()

print("LangGraph + CapMesh Integration")
for cap in ["read repository", "security scan", "send notification"]:
    config = resolve_tool(cap)
    print(f"  {cap:25s} -> {config['provider']} ({config['protocol']})")
    print(f"    Connection: {config['connection']}")
print()
print("  LangGraph tools are resolved at runtime.")
print("  The graph definition never changes when providers change.")
