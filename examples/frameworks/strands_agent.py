#!/usr/bin/env python3
"""AWS Strands + CapMesh — discover MCP tools dynamically."""
# pip install strands-agents capmesh

import capmesh

mesh = capmesh.connect()

# Discover what's available
results = mesh.discover("repository")
print(f"Found {len(results)} capabilities matching 'repository':")
for r in results:
    print(f"  [{r.score:.1f}] {r.capability} — {r.reason}")

# Resolve an MCP tool
repo = mesh.need("read repository", kind="tool", protocol="mcp")

# Strands integration:
# from strands import Agent
# from strands.tools import MCPTool
#
# tool = MCPTool(repo.binding.connection["server"])
# agent = Agent(tools=[tool])
# result = agent("Read the auth module from myorg/webapp")

print(f"\nResolved: {repo.provider_name}:{repo.provider_version}")
print(f"  Protocol: {repo.binding.protocol}")
print(f"  Connection: {repo.binding.connection}")
