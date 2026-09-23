# CapMesh Demo

## Structure

```
demo/
├── providers/                              # YAML manifests (what you write)
│   ├── tools/
│   │   ├── github-reader/manifest.yaml     # MCP tool
│   │   ├── gitlab-reader/manifest.yaml     # MCP tool (same capability, v2)
│   │   └── rest-code-analyzer/manifest.yaml # REST tool
│   ├── agents/
│   │   ├── langgraph-security-reviewer/    # LangGraph agent
│   │   ├── crewai-security-reviewer/       # CrewAI agent
│   │   └── strands-perf-analyzer/          # Strands agent
│   └── skills/
│       └── security-code-review/           # Skill + SKILL.md
├── 01_build.sh         # capmesh build — validate + digest
├── 02_register.sh      # capmesh register — store in registry
├── 03_resolve.sh       # capmesh resolve — discover + bind
├── 04_benefits.sh      # Side-by-side: WITHOUT vs WITH CapMesh
└── 04_benefits.py      # Orchestrator code showing real results
```

## Run

```bash
export CAPMESH_ROOT=$(mktemp -d)    # fresh registry

./demo/01_build.sh                  # Build: validate YAMLs, compute digests
./demo/02_register.sh               # Register: store in local registry
./demo/03_resolve.sh                # Resolve: discover + bind capabilities
./demo/04_benefits.sh               # Benefits: same task, two ways, then change everything
```

## The Docker Analogy

```
docker build      →  capmesh tool build / capmesh agent build / capmesh skill build
docker push       →  capmesh tool push / capmesh agent push
docker pull       →  capmesh tool pull / capmesh agent pull
docker images     →  capmesh search
docker inspect    →  capmesh agent inspect
docker tag        →  capmesh tag
docker login      →  capmesh login

# What Docker doesn't have — CapMesh's differentiator:
capmesh resolve   →  "I need X capability" → best provider
capmesh providers →  "Who provides X?"
capmesh graph     →  "What does X depend on?"
```

## What you'll see

**Step 1 — Build** (`capmesh build`)
- Validates every manifest YAML
- Computes sha256 digests (like Docker image digests)
- Reports errors if malformed

**Step 2 — Register** (`capmesh register` + `capmesh search`)
- Stores providers in registry (YAML files + SQLite index)
- Search, inspect, tag — all via CLI

**Step 3 — Resolve** (`capmesh resolve`)
- Ask for a capability, get the best provider
- Full resolution trace showing candidates + selection logic
- JSON output for programmatic use
- Version constraints

**Step 4 — Benefits** (the real payoff)
- Same security review: WITHOUT CapMesh (hardcoded) vs WITH (dynamic)
- 3 requirement changes: swap GitHub→GitLab, upgrade scanner, restrict access
- WITHOUT: 3 code changes, 3 redeployments, days of work
- WITH: 0 code changes, 0 redeployments, 30 seconds each
