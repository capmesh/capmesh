#!/usr/bin/env python3
"""
Raw HTTP — no framework, just httpx calling CapMesh server API.

This is the simplest integration. Any language, any framework.
Just HTTP calls.
"""
# pip install httpx

print("""
Raw HTTP + CapMesh Integration
==============================

Any language, any framework. Just call the CapMesh HTTP API.


PYTHON:
-------
import httpx

capmesh = httpx.Client(base_url="http://capmesh:8080")

# Resolve a capability
resp = capmesh.post("/v1/resolve", json={
    "capability": "security.code.review",
    "contract": "v1",
    "caller": {"identity": "my-app", "environment": "production"}
})
binding = resp.json()
# binding = {
#     "provider": "security/crewai-reviewer:3.1.0",
#     "protocol": "a2a",
#     "binding": {"endpoint": "https://crewai-security.example.com"},
#     "trace_id": "res_8444e343826b"
# }

# Call the resolved provider
if binding["protocol"] == "a2a":
    result = httpx.post(binding["binding"]["endpoint"], json={"task": "review PR #42"})
elif binding["protocol"] == "mcp":
    result = mcp_client.call(binding["binding"]["server"], args)


CURL:
-----
# Resolve
curl -X POST http://capmesh:8080/v1/resolve \\
  -H "Content-Type: application/json" \\
  -d '{"capability": "security.code.review", "contract": "v1",
       "caller": {"identity": "my-app"}}'

# Response:
# {"provider": "security/crewai-reviewer:3.1.0",
#  "protocol": "a2a",
#  "binding": {"endpoint": "https://crewai-security.example.com"},
#  "trace_id": "res_8444e343826b"}


JAVASCRIPT/TYPESCRIPT:
----------------------
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
// Use binding.binding.endpoint to call the provider


GO:
---
body := `{"capability": "security.code.review", "contract": "v1",
          "caller": {"identity": "my-app"}}`
resp, _ := http.Post("http://capmesh:8080/v1/resolve",
    "application/json", strings.NewReader(body))
// Parse response, use binding.endpoint


JAVA:
-----
HttpResponse<String> resp = HttpClient.newHttpClient().send(
    HttpRequest.newBuilder()
        .uri(URI.create("http://capmesh:8080/v1/resolve"))
        .POST(HttpRequest.BodyPublishers.ofString(
            "{\"capability\": \"security.code.review\", " +
            "\"contract\": \"v1\", " +
            "\"caller\": {\"identity\": \"my-app\"}}"))
        .header("Content-Type", "application/json")
        .build(),
    HttpResponse.BodyHandlers.ofString());
// Parse JSON, use binding.endpoint


ANY LANGUAGE:
-------------
CapMesh is a REST API. POST /v1/resolve with JSON.
Get back: provider name, protocol, connection binding.
Call the provider directly using the returned info.
No SDK required. No framework lock-in.
""")
