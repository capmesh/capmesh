#!/usr/bin/env python3
"""
PRODUCTION ARCHITECTURE DEMO

This shows how CapMesh actually runs:

1. CapMesh Registry Server runs in background (like Docker Registry)
2. Platform team registers providers via HTTP API
3. Agents discover and resolve capabilities via HTTP API
4. Live: add providers, swap tools, enforce policy — all while agents are running

Architecture:
  +------------------+       +------------------+       +------------------+
  |   Agent App      |       |  CapMesh Server   |       |  Providers       |
  |  (your code)     |------>|  (registry +      |       |  (A2A/MCP/REST)  |
  |                  |  HTTP |   resolver)       |       |                  |
  |  "I need         |       |  POST /v1/resolve |       |  security-agent  |
  |   security.scan" |       |  GET /v1/providers|       |  github-mcp      |
  |                  |<------|                   |       |  sonarqube       |
  |  binding: a2a    |       +------------------+       +------------------+
  |  endpoint: ...   |               |
  +-----|------------+               | SQLite + YAML
        |                            | (local storage)
        v
  Call the actual provider
  using the returned binding
"""
import json
import os
import sqlite3
import sys
import tempfile
import threading
import time
from pathlib import Path

# =====================================================================
# STEP 0: Start the CapMesh server in background
# =====================================================================

def run(coro):
    """Run async code from sync context."""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class CapMeshClient:
    """HTTP client wrapper that simulates calling the CapMesh server API.
    In production: httpx.Client pointing at http://capmesh:8080
    In this demo: httpx.AsyncClient with ASGI transport (same HTTP API, no TCP)."""

    def __init__(self, app):
        import httpx
        self._transport = httpx.ASGITransport(app=app)

    def get(self, path):
        import httpx
        async def _get():
            async with httpx.AsyncClient(transport=self._transport, base_url="http://capmesh:8080") as c:
                return await c.get(path)
        return run(_get())

    def post(self, path, json=None):
        import httpx
        async def _post():
            async with httpx.AsyncClient(transport=self._transport, base_url="http://capmesh:8080") as c:
                return await c.post(path, json=json)
        return run(_post())


def main():
    from capmesh.server.app import create_app

    ROOT = Path(tempfile.mkdtemp(prefix="capmesh-prod-"))

    print()
    print("+" + "=" * 68 + "+")
    print("|  CAPMESH PRODUCTION ARCHITECTURE DEMO                              |")
    print("|  Server running -> Agents discover via HTTP -> Live operations     |")
    print("+" + "=" * 68 + "+")

    # ---- Start server ----
    print()
    print("  [SERVER] Starting CapMesh registry server...")
    print("  $ capmesh server start --port 8080")
    app = create_app(root=ROOT)
    client = CapMeshClient(app)

    print("  [OK] Server running at http://capmesh:8080")
    print(f"  [OK] Registry storage: {ROOT}")

    # Verify server is up
    resp = client.get("/healthz")
    print(f"  [OK] Health check: {resp.json()}")
    print()

    # =====================================================================
    # STEP 1: Platform team registers providers via HTTP API
    # =====================================================================

    print("-" * 70)
    print("  STEP 1: Platform team registers providers (via HTTP API)")
    print("-" * 70)
    print()
    print("  Just like 'docker push' sends images to Docker Hub,")
    print("  'POST /v1/providers/register' sends manifests to CapMesh.")
    print()

    providers = [
        # Tools
        {
            "metadata": {"api_version": "capmesh.io/v1alpha1", "kind": "tool",
                         "namespace": "repository", "name": "github-reader",
                         "version": "1.0.0", "owner": "platform"},
            "provides": [{"capability": "repository.read", "contract": "v1"}],
            "requires": [],
            "interface": {"protocol": "mcp", "server": "github-mcp", "tool_name": "read"},
            "governance": {"visibility": "public", "status": "approved"},
        },
        {
            "metadata": {"api_version": "capmesh.io/v1alpha1", "kind": "tool",
                         "namespace": "repository", "name": "gitlab-reader",
                         "version": "2.0.0", "owner": "platform"},
            "provides": [{"capability": "repository.read", "contract": "v1"}],
            "requires": [],
            "interface": {"protocol": "mcp", "server": "gitlab-mcp", "tool_name": "read"},
            "governance": {"visibility": "public", "status": "approved"},
        },
        {
            "metadata": {"api_version": "capmesh.io/v1alpha1", "kind": "tool",
                         "namespace": "notifications", "name": "slack-notifier",
                         "version": "1.0.0", "owner": "platform"},
            "provides": [{"capability": "notification.send", "contract": "v1"}],
            "requires": [],
            "interface": {"protocol": "rest", "endpoint": "https://slack.example.com/api",
                         "auth_type": "bearer", "request_mapping": {}, "response_mapping": {}},
            "governance": {"visibility": "public", "status": "approved"},
        },
        {
            "metadata": {"api_version": "capmesh.io/v1alpha1", "kind": "tool",
                         "namespace": "issues", "name": "jira-tracker",
                         "version": "1.0.0", "owner": "platform"},
            "provides": [{"capability": "issue.create", "contract": "v1"}],
            "requires": [],
            "interface": {"protocol": "rest", "endpoint": "https://jira.example.com/api",
                         "auth_type": "bearer", "request_mapping": {}, "response_mapping": {}},
            "governance": {"visibility": "public", "status": "approved"},
        },
        {
            "metadata": {"api_version": "capmesh.io/v1alpha1", "kind": "tool",
                         "namespace": "observability", "name": "grafana-metrics",
                         "version": "1.0.0", "owner": "platform"},
            "provides": [{"capability": "metrics.query", "contract": "v1"}],
            "requires": [],
            "interface": {"protocol": "rest", "endpoint": "https://grafana.example.com/api",
                         "auth_type": "bearer", "request_mapping": {}, "response_mapping": {}},
            "governance": {"visibility": "public", "status": "approved"},
        },
        # Agents (different frameworks)
        {
            "metadata": {"api_version": "capmesh.io/v1alpha1", "kind": "agent",
                         "namespace": "security", "name": "langgraph-reviewer",
                         "version": "2.4.0", "owner": "security-team"},
            "provides": [{"capability": "security.code.review", "contract": "v1"}],
            "requires": [{"capability": "repository.read", "contract": "v1"}],
            "interface": {"protocol": "a2a", "endpoint": "https://langgraph-sec.example.com"},
            "governance": {"visibility": "public", "status": "approved",
                          "labels": {"framework": "langgraph"}},
        },
        {
            "metadata": {"api_version": "capmesh.io/v1alpha1", "kind": "agent",
                         "namespace": "security", "name": "crewai-reviewer",
                         "version": "3.1.0", "owner": "security-team"},
            "provides": [{"capability": "security.code.review", "contract": "v1"}],
            "requires": [{"capability": "repository.read", "contract": "v1"}],
            "interface": {"protocol": "a2a", "endpoint": "https://crewai-sec.example.com"},
            "governance": {"visibility": "public", "status": "approved",
                          "labels": {"framework": "crewai"}},
        },
        {
            "metadata": {"api_version": "capmesh.io/v1alpha1", "kind": "agent",
                         "namespace": "reliability", "name": "strands-incident-bot",
                         "version": "1.0.0", "owner": "sre-team"},
            "provides": [{"capability": "incident.respond", "contract": "v1"}],
            "requires": [{"capability": "metrics.query", "contract": "v1"},
                        {"capability": "notification.send", "contract": "v1"}],
            "interface": {"protocol": "a2a", "endpoint": "https://strands-incident.example.com"},
            "governance": {"visibility": "public", "status": "approved",
                          "labels": {"framework": "strands"}},
        },
        # Private agent (only owner can access)
        {
            "metadata": {"api_version": "capmesh.io/v1alpha1", "kind": "agent",
                         "namespace": "internal", "name": "secret-scanner",
                         "version": "1.0.0", "owner": "security-team"},
            "provides": [{"capability": "security.deep-scan", "contract": "v1"}],
            "requires": [],
            "interface": {"protocol": "a2a", "endpoint": "https://internal-scanner.example.com"},
            "governance": {"visibility": "private", "status": "approved"},
        },
    ]

    for p in providers:
        resp = client.post("/v1/providers/register", json=p)
        m = p["metadata"]
        caps = ", ".join(c["capability"] for c in p["provides"])
        framework = p["governance"].get("labels", {}).get("framework", "")
        fw = f" [{framework}]" if framework else ""
        print(f"  POST /v1/providers/register")
        print(f"    -> {m['namespace']}/{m['name']}:{m['version']} ({m['kind']}){fw}")
        print(f"       Provides: {caps}")
        if resp.status_code == 200:
            print(f"       Digest: {resp.json().get('digest', '')[:20]}...")
        print()

    # =====================================================================
    # STEP 2: Agent App discovers capabilities via HTTP API
    # =====================================================================

    print("-" * 70)
    print("  STEP 2: Agent app resolves capabilities (via HTTP API)")
    print("-" * 70)
    print()
    print("  This is YOUR agent code. It doesn't import any tools or frameworks.")
    print("  It just calls POST /v1/resolve with a capability name.")
    print()
    print("  +----------------------------------------------------------+")
    print("  |  # Your agent code — ZERO tool/framework imports         |")
    print("  |                                                          |")
    print("  |  binding = http.post('/v1/resolve', {                    |")
    print("  |      'capability': 'security.code.review',              |")
    print("  |      'contract': 'v1',                                  |")
    print("  |      'caller': {'identity': 'my-agent'}                 |")
    print("  |  })                                                      |")
    print("  |                                                          |")
    print("  |  # Use the returned binding to call the provider         |")
    print("  |  result = a2a_call(binding['endpoint'], task)            |")
    print("  +----------------------------------------------------------+")
    print()

    # --- Resolve: security.code.review ---
    print("  [AGENT] I need 'security.code.review/v1'...")
    resp = client.post("/v1/resolve", json={
        "capability": "security.code.review",
        "contract": "v1",
        "caller": {"identity": "pr-review-agent", "environment": "production"},
    })
    data = resp.json()
    print(f"  [CAPMESH] POST /v1/resolve -> {resp.status_code}")
    print(f"    Provider: {data['provider']}")
    print(f"    Protocol: {data['protocol']}")
    print(f"    Binding:  {json.dumps(data['binding'])}")
    print(f"    Trace:    {data['trace_id']}")
    print()
    print(f"  The agent now calls {data['binding']['endpoint']} via A2A protocol.")
    print(f"  It doesn't know or care that it's a CrewAI agent.")
    print()

    # --- Resolve: repository.read ---
    print("  [AGENT] I need 'repository.read/v1'...")
    resp = client.post("/v1/resolve", json={
        "capability": "repository.read",
        "contract": "v1",
        "caller": {"identity": "pr-review-agent"},
    })
    data = resp.json()
    print(f"  [CAPMESH] -> {data['provider']} ({data['protocol']})")
    print(f"    Binding: server={data['binding']['server']}")
    print()

    # --- Resolve: metrics.query ---
    print("  [AGENT] I need 'metrics.query/v1'...")
    resp = client.post("/v1/resolve", json={
        "capability": "metrics.query",
        "contract": "v1",
        "caller": {"identity": "incident-bot"},
    })
    data = resp.json()
    print(f"  [CAPMESH] -> {data['provider']} ({data['protocol']})")
    print(f"    Binding: endpoint={data['binding']['endpoint']}")
    print()

    # =====================================================================
    # STEP 3: Live operations — add/swap/restrict while agents are running
    # =====================================================================

    print("-" * 70)
    print("  STEP 3: Live operations (server keeps running)")
    print("-" * 70)

    # --- 3a: Add new capability at runtime ---
    print()
    print("  [3a] ADD: New 'performance.analyze' agent — no restart needed")
    print()
    resp = client.post("/v1/providers/register", json={
        "metadata": {"api_version": "capmesh.io/v1alpha1", "kind": "agent",
                     "namespace": "performance", "name": "perf-analyzer",
                     "version": "1.0.0", "owner": "platform"},
        "provides": [{"capability": "performance.analyze", "contract": "v1"}],
        "requires": [],
        "interface": {"protocol": "a2a", "endpoint": "https://perf.example.com"},
        "governance": {"visibility": "public", "status": "approved"},
    })
    print(f"  POST /v1/providers/register -> {resp.status_code}")

    resp = client.post("/v1/resolve", json={
        "capability": "performance.analyze", "contract": "v1",
        "caller": {"identity": "orchestrator"},
    })
    data = resp.json()
    print(f"  POST /v1/resolve performance.analyze -> {data['provider']}")
    print(f"  Available INSTANTLY. No restart. No redeploy.")

    # --- 3b: Swap provider ---
    print()
    print("  [3b] SWAP: Upgrade security scanner (3.1.0 -> 4.0.0)")
    print()
    print("  Before:")
    resp = client.post("/v1/resolve", json={
        "capability": "security.code.review", "contract": "v1",
        "caller": {"identity": "agent"},
    })
    before = resp.json()
    print(f"    security.code.review -> {before['provider']}")

    # Register newer version
    client.post("/v1/providers/register", json={
        "metadata": {"api_version": "capmesh.io/v1alpha1", "kind": "agent",
                     "namespace": "security", "name": "next-gen-reviewer",
                     "version": "4.0.0", "owner": "security-team"},
        "provides": [{"capability": "security.code.review", "contract": "v1"}],
        "requires": [],
        "interface": {"protocol": "a2a", "endpoint": "https://nextgen-sec.example.com"},
        "governance": {"visibility": "public", "status": "approved",
                      "labels": {"framework": "custom"}},
    })

    print("  After (registered next-gen-reviewer:4.0.0):")
    resp = client.post("/v1/resolve", json={
        "capability": "security.code.review", "contract": "v1",
        "caller": {"identity": "agent"},
    })
    after = resp.json()
    print(f"    security.code.review -> {after['provider']}")
    print(f"  Swapped! Agent code: UNCHANGED. Endpoint changed automatically.")

    # --- 3c: Policy enforcement ---
    print()
    print("  [3c] POLICY: Private provider blocked for unauthorized callers")
    print()
    resp = client.post("/v1/resolve", json={
        "capability": "security.deep-scan", "contract": "v1",
        "caller": {"identity": "random-intern"},
    })
    print(f"  random-intern -> security.deep-scan: {resp.status_code} {resp.json().get('detail', '')[:50]}")

    resp = client.post("/v1/resolve", json={
        "capability": "security.deep-scan", "contract": "v1",
        "caller": {"identity": "security-team"},
    })
    data = resp.json()
    print(f"  security-team -> security.deep-scan: {resp.status_code} -> {data['provider']}")

    # --- 3d: Query traces ---
    print()
    print("  [3d] AUDIT: Query resolution traces via API")
    print()
    # Get a trace ID from our last resolve
    trace_id = data["trace_id"]
    resp = client.get(f"/v1/resolutions/{trace_id}")
    trace = resp.json()
    print(f"  GET /v1/resolutions/{trace_id}")
    print(f"    Capability: {trace['requested_capability']}/{trace['requested_contract']}")
    print(f"    Caller:     {trace['caller']['identity']}")
    print(f"    Candidates: {len(trace['candidates'])}")
    for c in trace["candidates"]:
        status = "PASS" if c["passed"] else f"FAIL ({c['rejection_reason']})"
        print(f"      {c['provider']}:{c['version']} [{status}]")
    print(f"    Selected:   {trace['selected_provider']}")
    print(f"    Outcome:    {trace['outcome']}")

    # --- 3e: Search and discovery ---
    print()
    print("  [3e] DISCOVERY: Search and list via API")
    print()
    resp = client.post("/v1/search", json={"query": "security"})
    results = resp.json()
    print(f"  POST /v1/search {{'query': 'security'}} -> {len(results)} results")
    for r in results:
        print(f"    {r['namespace']}/{r['name']}:{r['version']} ({r['kind']})")

    print()
    resp = client.get("/v1/capabilities/security.code.review/providers")
    providers = resp.json()
    print(f"  GET /v1/capabilities/security.code.review/providers -> {len(providers)} providers")
    for p in providers:
        print(f"    {p['namespace']}/{p['name']}:{p['version']}")

    # =====================================================================
    # STEP 4: Full agent workflow via HTTP
    # =====================================================================

    print()
    print("-" * 70)
    print("  STEP 4: Full agent workflow — PR Review Pipeline via HTTP")
    print("-" * 70)
    print()
    print("  An agent app receives: 'Review PR #42'")
    print("  It chains 4 capability resolutions — all via HTTP to CapMesh.")
    print()

    caller = {"identity": "pr-review-bot", "environment": "production"}
    steps = [
        ("repository.read", "Read the PR diff"),
        ("security.code.review", "Run security review"),
        ("issue.create", "Create findings ticket"),
        ("notification.send", "Notify the team"),
    ]

    for cap, description in steps:
        resp = client.post("/v1/resolve", json={
            "capability": cap, "contract": "v1", "caller": caller,
        })
        if resp.status_code == 200:
            data = resp.json()
            print(f"  Step: {description}")
            print(f"    POST /v1/resolve {{capability: '{cap}'}}")
            print(f"    -> {data['provider']} via {data['protocol']}")
            conn = data["binding"]
            detail = conn.get("endpoint") or conn.get("server") or ""
            if detail:
                print(f"    -> Connect to: {detail}")
            print(f"    -> Trace: {data['trace_id']}")
            print()
        else:
            print(f"  Step: {description}")
            print(f"    -> FAILED: {resp.json().get('detail', 'unknown error')}")
            print()

    # =====================================================================
    # SUMMARY
    # =====================================================================

    print("+" + "=" * 68 + "+")
    print("|  HOW IT WORKS IN PRODUCTION                                       |")
    print("+" + "=" * 68 + "+")
    print()
    print("  1. DEPLOY: capmesh server start (or Docker container)")
    print("     Just like Docker Registry — runs as a service")
    print()
    print("  2. REGISTER: Platform team pushes provider manifests")
    print("     POST /v1/providers/register  (or: capmesh agent push)")
    print("     Tools, agents, skills — any protocol, any framework")
    print()
    print("  3. RESOLVE: Agent apps call the HTTP API")
    print("     POST /v1/resolve {capability: 'X', contract: 'v1'}")
    print("     Returns: provider name, protocol, connection binding")
    print("     Agent uses binding to call the actual provider")
    print()
    print("  4. LIVE OPS: While agents are running...")
    print("     Add new providers    -> agents discover them instantly")
    print("     Upgrade a provider   -> agents get the new version automatically")
    print("     Restrict access      -> change visibility in manifest YAML")
    print("     Audit everything     -> GET /v1/resolutions/{trace_id}")
    print()
    print("  WHAT YOUR AGENT CODE LOOKS LIKE:")
    print("  +----------------------------------------------------------+")
    print("  |  import httpx                                            |")
    print("  |                                                          |")
    print("  |  capmesh = httpx.Client(base_url='http://capmesh:8080')  |")
    print("  |                                                          |")
    print("  |  # Discover and bind — no tool imports needed            |")
    print("  |  resp = capmesh.post('/v1/resolve', json={               |")
    print("  |      'capability': 'security.code.review',              |")
    print("  |      'contract': 'v1',                                  |")
    print("  |      'caller': {'identity': 'my-agent'}                 |")
    print("  |  })                                                      |")
    print("  |  binding = resp.json()                                   |")
    print("  |                                                          |")
    print("  |  # Call the provider using the returned binding          |")
    print("  |  if binding['protocol'] == 'a2a':                       |")
    print("  |      result = a2a_client.call(binding['endpoint'], task) |")
    print("  |  elif binding['protocol'] == 'mcp':                     |")
    print("  |      result = mcp_client.call(binding['server'], task)   |")
    print("  +----------------------------------------------------------+")
    print()
    print("  NO tool SDKs. NO framework imports. NO hardcoded endpoints.")
    print("  One HTTP call to CapMesh. Get back everything you need.")
    print()

    # client cleanup handled by context managers


if __name__ == "__main__":
    main()
