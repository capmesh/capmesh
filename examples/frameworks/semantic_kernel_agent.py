#!/usr/bin/env python3
"""
Microsoft Semantic Kernel using CapMesh for capability discovery.

SK plugins/functions are resolved from CapMesh at runtime.
"""
# pip install semantic-kernel capmesh

# --- WITHOUT CapMesh (hardcoded) ---
#
# from semantic_kernel.connectors import GitHubPlugin  # LOCKED
# kernel.add_plugin(GitHubPlugin(), "github")           # HARDCODED

# --- WITH CapMesh ---

from capmesh.resolver import Resolver
from capmesh.registry import Registry
from capmesh.policy import default_policy_engine
from capmesh.models.resolution import CallerContext

resolver = Resolver(
    registry=Registry(),
    policy_engine=default_policy_engine(),
)

caller = CallerContext(identity="semantic-kernel-agent")

# Semantic Kernel integration:
#
# import semantic_kernel as sk
# from semantic_kernel.functions import kernel_function
#
# kernel = sk.Kernel()
#
# # Resolve capabilities from CapMesh
# repo = resolver.need("read a repository", caller=caller)
# scan = resolver.need("security scan", caller=caller)
#
# # Create SK functions from CapMesh bindings
# @kernel_function(name="read_repo", description="Read repository via CapMesh")
# def read_repo(repo_name: str) -> str:
#     conn = repo.binding.connection
#     if repo.binding.protocol == "mcp":
#         return mcp_client.call(conn["server"], {"repo": repo_name})
#     return httpx.get(conn["endpoint"], params={"repo": repo_name}).text
#
# kernel.add_function("tools", read_repo)
# result = await kernel.invoke("tools", "read_repo", repo_name="myorg/app")

print("Semantic Kernel + CapMesh Integration")
for cap in ["read a repository", "security scan", "create issue"]:
    result = resolver.need(cap, caller=caller)
    print(f"  {cap:25s} -> {result.provider_name}:{result.provider_version}")
    print(f"    Protocol: {result.binding.protocol}")
    print(f"    Connection: {result.binding.connection}")
print()
print("  Semantic Kernel plugins are resolved from CapMesh.")
print("  No hardcoded connectors — any provider works.")
