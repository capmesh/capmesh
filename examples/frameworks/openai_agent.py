#!/usr/bin/env python3
"""OpenAI Agents + CapMesh — dynamic function-calling schemas."""
# pip install openai capmesh

import capmesh

mesh = capmesh.connect()


def make_openai_tool(query: str, **filters):
    """Generate an OpenAI function-calling schema from a CapMesh resolution."""
    result = mesh.need(query, **filters)
    return {
        "type": "function",
        "function": {
            "name": query.replace(" ", "_").replace(".", "_"),
            "description": f"{result.provider_name}:{result.provider_version} via {result.binding.protocol}",
            "parameters": {"type": "object", "properties": {
                "input": {"type": "string"}
            }},
        },
        "_binding": result.binding,
    }


tools = [
    make_openai_tool("repository.read", kind="tool"),
    make_openai_tool("security.code.review", kind="agent"),
]

# OpenAI integration:
# from openai import OpenAI
# client = OpenAI()
# response = client.chat.completions.create(
#     model="gpt-4", messages=[...], tools=tools,
# )
# for call in response.choices[0].message.tool_calls:
#     binding = tools[call.function.name]["_binding"]
#     result = dispatch(binding, call.function.arguments)

print("OpenAI + CapMesh")
for t in tools:
    print(f"  {t['function']['name']}: {t['function']['description']}")
