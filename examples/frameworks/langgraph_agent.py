#!/usr/bin/env python3
"""LangGraph + CapMesh — resolve tools at graph build time."""
# pip install langgraph capmesh

import capmesh

mesh = capmesh.connect()

# Resolve tools for graph nodes
repo = mesh.need("read repository code", kind="tool")
scan = mesh.need("security review", kind="agent")
notify = mesh.need("send notification", protocol="rest")

# LangGraph integration:
# from langgraph.graph import StateGraph
# from langchain_core.tools import tool
#
# @tool
# def read_repo(repo: str) -> dict:
#     conn = repo.binding.connection
#     return mcp_client.call(conn["server"], {"repo": repo})
#
# @tool
# def security_scan(files: list) -> dict:
#     conn = scan.binding.connection
#     return a2a_client.call(conn["endpoint"], {"files": files})
#
# graph = StateGraph(...)
# graph.add_node("read", read_repo)
# graph.add_node("scan", security_scan)
# graph.add_edge("read", "scan")
# app = graph.compile()

print("LangGraph + CapMesh")
for name, r in [("repo", repo), ("scan", scan), ("notify", notify)]:
    print(f"  {name}: {r.provider_name}:{r.provider_version} via {r.binding.protocol}")
    print(f"    -> {r.binding.connection}")
