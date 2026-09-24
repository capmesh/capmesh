#!/usr/bin/env python3
"""Any language — just HTTP. No SDK required."""

print("""
CapMesh works with ANY language via HTTP.

PYTHON:
    import httpx
    resp = httpx.post("http://capmesh:8080/v1/resolve", json={
        "capability": "security.code.review",
        "contract": "v1",
        "caller": {"identity": "my-app"}
    })
    binding = resp.json()
    # {"provider": "security/reviewer:3.1.0", "protocol": "a2a",
    #  "binding": {"endpoint": "https://scanner.example.com"}}

CURL:
    curl -X POST http://capmesh:8080/v1/resolve \\
      -H "Content-Type: application/json" \\
      -d '{"capability":"security.code.review","contract":"v1",
           "caller":{"identity":"my-app"}}'

JAVASCRIPT:
    const resp = await fetch("http://capmesh:8080/v1/resolve", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        capability: "security.code.review",
        contract: "v1",
        caller: {identity: "my-app"}
      })
    });
    const binding = await resp.json();

GO:
    body := `{"capability":"security.code.review","contract":"v1",
              "caller":{"identity":"my-app"}}`
    resp, _ := http.Post("http://capmesh:8080/v1/resolve",
        "application/json", strings.NewReader(body))

CLI:
    capmesh resolve security.code.review
    capmesh resolve security.code.review --kind agent
    capmesh resolve "read a repo" --protocol mcp
    capmesh resolve security.code.review --kind agent --protocol a2a --trace
""")
