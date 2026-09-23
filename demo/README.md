# CapMesh Demo

## Structure

```
demo/
├── providers/                              # YAML manifests (what you write)
│   ├── tools/
│   │   ├── github-reader/manifest.yaml     # MCP tool — repository.read
│   │   ├── gitlab-reader/manifest.yaml     # MCP tool — same capability, different vendor
│   │   └── rest-code-analyzer/manifest.yaml # REST tool — code.analyze
│   ├── agents/
│   │   ├── langgraph-security-reviewer/    # LangGraph agent — security.code.review
│   │   ├── crewai-security-reviewer/       # CrewAI agent — same capability, different framework
│   │   └── strands-perf-analyzer/          # Strands agent — performance.analyze
│   └── skills/
│       └── security-code-review/           # Skill + SKILL.md — declares deps, not tools
│           ├── manifest.yaml
│           └── SKILL.md
├── 01_build.py         # Validate manifests + compute digests
├── 02_register.py      # Register all providers into the registry
└── 03_resolve.py       # Resolve, use, swap, trace — full demo
```

## Run

```bash
python demo/01_build.py       # Build: validate YAMLs, compute digests
python demo/02_register.py    # Register: store in local registry
python demo/03_resolve.py     # Resolve: see CapMesh in action
```

## What you'll see

**Step 1 — Build** (like `docker build`)
- Validates every manifest YAML
- Computes sha256 digests
- Reports errors if any manifest is malformed

**Step 2 — Register** (like `docker load` / `docker push`)
- Stores providers in the local registry (YAML files + SQLite index)
- Shows available capabilities and which providers serve them

**Step 3 — Resolve** (what makes CapMesh different)
- Orchestrator asks for capabilities, gets the best provider
- Real security scan with findings and verdict
- Cross-framework discovery (LangGraph, CrewAI, Strands)
- Dynamic provider addition at runtime
- Provider swap with zero code changes
- Skill dual binding (auto-resolves tool dependencies)
- Policy enforcement (visibility, environment)
- Full audit trail of every resolution
