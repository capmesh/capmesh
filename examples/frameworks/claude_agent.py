#!/usr/bin/env python3
"""
Claude + CapMesh — the most natural integration.

Claude has three things that map directly to CapMesh:
  1. Tools (function calling)  -> CapMesh resolves which tools to attach
  2. MCP servers               -> CapMesh resolves which MCP servers to connect
  3. Skills (system prompt)    -> CapMesh resolves which skill to load + its tool deps

Three patterns shown:
  Pattern A: Claude API with tool_use (function calling)
  Pattern B: Claude with MCP servers
  Pattern C: Claude with Skills (system prompt + auto-resolved tools)
"""
# pip install anthropic capmesh

import capmesh
import tempfile
from pathlib import Path

mesh = capmesh.connect(root=tempfile.mkdtemp())

# Register example providers (in production, these are already in the registry)
examples = Path(__file__).parent.parent
for manifest in [
    "security-agent/manifest.yaml",
    "github-tool/manifest.yaml",
    "security-review-skill/manifest.yaml",
]:
    path = examples / manifest
    if path.exists():
        mesh.register(str(path))

# ==================================================================
# PATTERN A: Claude API — CapMesh resolves tools for function calling
# ==================================================================

print("=" * 65)
print("  PATTERN A: Claude API + CapMesh (function calling)")
print("=" * 65)
print()
print("  CapMesh resolves tools. Claude calls them via tool_use.")
print()

# Resolve capabilities
repo = mesh.need("read a repository", kind="tool", protocol="mcp")
scan = mesh.need("security scan", kind="agent", protocol="a2a")

print(f"  Resolved: read repo -> {repo.provider_name} ({repo.binding.protocol})")
print(f"  Resolved: security  -> {scan.provider_name} ({scan.binding.protocol})")
print()

# Build Claude tool schemas from CapMesh bindings
def binding_to_claude_tool(name, description, binding, input_schema):
    return {
        "name": name,
        "description": f"{description} [via {binding.provider}]",
        "input_schema": input_schema,
        "_capmesh_binding": binding,  # keep for dispatch
    }

tools = [
    binding_to_claude_tool(
        "read_repo", "Read files from a code repository",
        repo.binding,
        {"type": "object", "properties": {"repo": {"type": "string"}, "path": {"type": "string"}}},
    ),
    binding_to_claude_tool(
        "security_scan", "Scan code for security vulnerabilities",
        scan.binding,
        {"type": "object", "properties": {"files": {"type": "array", "items": {"type": "string"}}}},
    ),
]

print("  Claude tool schemas generated from CapMesh bindings:")
for t in tools:
    b = t["_capmesh_binding"]
    print(f"    {t['name']}: {b.protocol} -> {b.connection}")
print()

# # How to use with Claude API:
# import anthropic
# client = anthropic.Anthropic()
#
# response = client.messages.create(
#     model="claude-sonnet-4-20250514",
#     system="You are a security reviewer.",
#     messages=[{"role": "user", "content": "Review PR #42 in myorg/webapp"}],
#     tools=tools,
#     max_tokens=4096,
# )
#
# # When Claude calls a tool, dispatch to the CapMesh-resolved provider:
# for block in response.content:
#     if block.type == "tool_use":
#         binding = next(t["_capmesh_binding"] for t in tools if t["name"] == block.name)
#         if binding.protocol == "mcp":
#             result = mcp_client.call(binding.connection["server"], block.input)
#         elif binding.protocol == "a2a":
#             result = a2a_client.call(binding.connection["endpoint"], block.input)
#         elif binding.protocol == "rest":
#             result = httpx.post(binding.connection["endpoint"], json=block.input).json()

print("  Usage:")
print("    response = client.messages.create(")
print("        model='claude-sonnet-4-20250514',")
print("        tools=tools,   # generated from CapMesh bindings")
print("        messages=[...],")
print("    )")
print("    # Claude calls tools -> you dispatch to resolved providers")
print()

# ==================================================================
# PATTERN B: Claude + MCP — CapMesh resolves which MCP servers
# ==================================================================

print("=" * 65)
print("  PATTERN B: Claude + MCP servers (resolved by CapMesh)")
print("=" * 65)
print()
print("  Instead of hardcoding MCP servers in claude_desktop_config.json,")
print("  CapMesh tells you which MCP servers to connect.")
print()

# Resolve all MCP tools needed
mcp_tools = [
    mesh.need("repository read", protocol="mcp"),
    mesh.need("repository search", protocol="mcp"),
]

mcp_servers = set()
for t in mcp_tools:
    server = t.binding.connection.get("server")
    if server:
        mcp_servers.add(server)
    print(f"  Resolved: {t.provider_name} -> MCP server: {server}")

print()
print(f"  MCP servers to attach: {mcp_servers}")
print()

# # With Claude Agent SDK:
# from claude_agent_sdk import Agent
#
# # Resolve MCP servers from CapMesh
# mcp_bindings = [mesh.need(cap, protocol="mcp") for cap in ["read repo", "search code"]]
# mcp_server_names = [b.binding.connection["server"] for b in mcp_bindings]
#
# # Attach resolved MCP servers to the agent
# agent = Agent(
#     model="claude-sonnet-4-20250514",
#     mcp_servers=mcp_server_names,   # DYNAMIC -- resolved by CapMesh
# )

print("  # Claude Agent SDK integration:")
print("  agent = Agent(")
print("      model='claude-sonnet-4-20250514',")
print(f"      mcp_servers={list(mcp_servers)},  # resolved by CapMesh")
print("  )")
print()
print("  The MCP servers are unchanged. CapMesh just told you WHICH ones")
print("  to attach. Swap GitHub for GitLab? CapMesh resolves the new one.")
print()

# ==================================================================
# PATTERN C: Claude + Skill — the full stack
# ==================================================================

print("=" * 65)
print("  PATTERN C: Claude + Skill (system prompt + auto-resolved tools)")
print("=" * 65)
print()
print("  This is the most powerful pattern. CapMesh resolves a Skill,")
print("  which gives you:")
print("    1. SKILL.md content -> load as system prompt")
print("    2. Required tools   -> auto-resolved to MCP/A2A providers")
print()

# Resolve a skill
skill = mesh.need("security code review", kind="skill")

print(f"  Resolved skill: {skill.provider_name}:{skill.provider_version}")
print(f"  Protocol:       {skill.binding.protocol}")
print()

conn = skill.binding.connection
instructions = conn.get("instructions", "N/A")
tool_bindings = conn.get("tool_bindings", [])

print(f"  Instructions:   {instructions}")
print(f"  Tool bindings:  {len(tool_bindings)} auto-resolved")
for tb in tool_bindings:
    if "error" not in tb:
        print(f"    {tb['capability']} -> {tb['protocol']} ({tb['provider']})")
    else:
        print(f"    {tb['capability']} -> UNRESOLVED")
print()

# # Full Claude integration:
# import anthropic
#
# client = anthropic.Anthropic()
#
# # Step 1: Resolve the skill
# skill = mesh.need("security code review", kind="skill")
#
# # Step 2: Load SKILL.md as system prompt
# system_prompt = skill.binding.connection["instructions"]
# # In real usage, you'd read the actual SKILL.md file content
#
# # Step 3: Attach the auto-resolved tools
# tool_bindings = skill.binding.connection["tool_bindings"]
# mcp_servers = [tb["connection"]["server"]
#                for tb in tool_bindings if tb["protocol"] == "mcp"]
#
# # Step 4: Create Claude session with everything wired up
# response = client.messages.create(
#     model="claude-sonnet-4-20250514",
#     system=system_prompt,          # from Skill
#     tools=build_tools(tool_bindings),  # from CapMesh resolution
#     messages=[{"role": "user", "content": "Review PR #42"}],
# )

# Extract MCP servers from tool bindings
mcp_from_skill = [tb.get("connection", {}).get("server")
                  for tb in tool_bindings
                  if tb.get("protocol") == "mcp" and "error" not in tb]

print("  Full Claude setup from one CapMesh call:")
print()
print("    skill = mesh.need('security code review', kind='skill')")
print()
print("    # System prompt:")
print(f"    system = '{instructions}'")
print()
print("    # MCP servers to attach:")
print(f"    mcp_servers = {mcp_from_skill}")
print()
print("    # Claude session:")
print("    response = client.messages.create(")
print("        model='claude-sonnet-4-20250514',")
print("        system=system,                    # from Skill")
print(f"        mcp_servers={mcp_from_skill},  # auto-resolved")
print("        messages=[{'role': 'user', 'content': 'Review PR #42'}],")
print("    )")
print()

# ==================================================================
# SUMMARY
# ==================================================================

print("=" * 65)
print("  SUMMARY: Claude + CapMesh")
print("=" * 65)
print()
print("  Pattern A: Claude API + tool_use")
print("    mesh.need(...) -> tool schema -> Claude calls it")
print("    You dispatch tool calls to the resolved provider")
print()
print("  Pattern B: Claude + MCP")
print("    mesh.need(..., protocol='mcp') -> MCP server name")
print("    Attach to Claude session. MCP server unchanged.")
print()
print("  Pattern C: Claude + Skill (the full stack)")
print("    mesh.need(..., kind='skill') -> SKILL.md + auto-resolved tools")
print("    System prompt + MCP servers in ONE call.")
print("    Swap GitHub for GitLab? Skill YAML never changes.")
print()
print("  All three patterns: zero hardcoded tools, full audit trail.")
print()
