#!/usr/bin/env python3
"""
CrewAI Agent using CapMesh for capability discovery.

Instead of hardcoding tools, the agent resolves them via CapMesh.
"""
# pip install crewai capmesh

# --- WITHOUT CapMesh (hardcoded) ---
#
# from crewai import Agent, Task, Crew
# from crewai_tools import GithubSearchTool  # LOCKED to GitHub
#
# github_tool = GithubSearchTool()            # HARDCODED
# agent = Agent(
#     role="Security Reviewer",
#     tools=[github_tool],                     # HARDCODED
# )

# --- WITH CapMesh ---

from capmesh.resolver import Resolver
from capmesh.registry import Registry
from capmesh.policy import default_policy_engine
from capmesh.models.resolution import CallerContext

# Connect to CapMesh (once at startup)
resolver = Resolver(
    registry=Registry(),
    policy_engine=default_policy_engine(),
)

# Resolve capabilities — framework-agnostic
repo_binding = resolver.need("read a repository")
scan_binding = resolver.need("security scan")

# CrewAI integration: use resolved bindings as tool config
# from crewai import Agent, Task, Crew
#
# # Build tool from CapMesh binding
# if repo_binding.binding.protocol == "mcp":
#     repo_tool = MCPTool(server=repo_binding.binding.connection["server"])
# elif repo_binding.binding.protocol == "rest":
#     repo_tool = APITool(endpoint=repo_binding.binding.connection["endpoint"])
#
# agent = Agent(
#     role="Security Reviewer",
#     goal="Review code for security vulnerabilities",
#     tools=[repo_tool],  # DYNAMIC — resolved by CapMesh
# )
#
# task = Task(description="Review PR #42", agent=agent)
# crew = Crew(agents=[agent], tasks=[task])
# result = crew.kickoff()

print("CrewAI + CapMesh Integration")
print(f"  Repository tool: {repo_binding.provider_name} via {repo_binding.binding.protocol}")
print(f"    Connection: {repo_binding.binding.connection}")
print(f"  Security scan:  {scan_binding.provider_name} via {scan_binding.binding.protocol}")
print(f"    Connection: {scan_binding.binding.connection}")
print()
print("  The CrewAI agent doesn't know which MCP server or API it's using.")
print("  Swap GitHub for GitLab? Register new provider. CrewAI code: unchanged.")
