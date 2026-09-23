#!/usr/bin/env python3
"""
STEP 1: How to write a Tool

A Tool is an executable capability — an MCP server, REST API, or any
callable service. You describe WHAT it provides, not HOW consumers use it.
"""

print("""
===============================================================
  STEP 1: Writing a Tool Manifest
===============================================================

A Tool manifest is a YAML file that describes:
  - What capability this tool provides
  - How to connect to it (MCP server, REST endpoint, etc.)
  - Who owns it and who can use it
""")

# Create the manifest programmatically
from capmesh.models import (
    MCPInterface, CapabilityRef, Governance, Kind,
    Manifest, Metadata, Status, Visibility,
)
from capmesh.models.serialization import manifest_to_yaml

tool = Manifest(
    metadata=Metadata(
        kind=Kind.TOOL,
        namespace="repository",
        name="github-reader",
        version="1.0.0",
        owner="platform-team",
    ),
    provides=[
        CapabilityRef(capability="repository.read", contract="v1"),
        CapabilityRef(capability="repository.search", contract="v1"),
    ],
    requires=[],
    interface=MCPInterface(
        protocol="mcp",
        server="github-mcp",
        tool_name="read_file",
    ),
    governance=Governance(
        visibility=Visibility.PUBLIC,
        status=Status.APPROVED,
    ),
)

yaml_output = manifest_to_yaml(tool)

print("  manifest.yaml:")
print("  " + "-" * 50)
for line in yaml_output.strip().split("\n"):
    print(f"  {line}")

print("""
  Key points:
  - 'provides' declares what capabilities this tool offers
  - 'interface.protocol: mcp' tells CapMesh this is an MCP tool
  - 'interface.server: github-mcp' is the MCP server name
  - The tool doesn't know or care who will use it
""")

# Or use the CLI
print("  You can also scaffold this with the CLI:")
print("  $ capmesh tool init --namespace repository --name github-reader --version 1.0.0 --owner platform-team")
print()
