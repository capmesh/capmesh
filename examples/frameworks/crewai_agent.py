#!/usr/bin/env python3
"""CrewAI + CapMesh — discover tools dynamically."""
# pip install crewai capmesh

import capmesh

mesh = capmesh.connect()

# Discover tools for a CrewAI agent
repo = mesh.need("read a repository", kind="tool", protocol="mcp")
scan = mesh.need("security scan", kind="agent", protocol="a2a")

# CrewAI integration:
# from crewai import Agent, Task, Crew
# from crewai_tools import MCPTool
#
# repo_tool = MCPTool(server=repo.binding.connection["server"])
#
# agent = Agent(
#     role="Security Reviewer",
#     tools=[repo_tool],    # DYNAMIC — resolved by CapMesh
# )
# task = Task(description="Review PR #42", agent=agent)
# crew = Crew(agents=[agent], tasks=[task])
# result = crew.kickoff()

print("CrewAI + CapMesh")
print(f"  repo tool: {repo.provider_name}:{repo.provider_version} via {repo.binding.protocol}")
print(f"    -> {repo.binding.connection}")
print(f"  scanner:   {scan.provider_name}:{scan.provider_version} via {scan.binding.protocol}")
print(f"    -> {scan.binding.connection}")
