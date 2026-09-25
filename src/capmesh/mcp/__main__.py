"""Run CapMesh MCP server: python -m capmesh.mcp"""
from capmesh.mcp.server import create_mcp_server

server = create_mcp_server()
server.run(transport="stdio")
