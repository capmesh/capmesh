# CapMesh Demo

## Structure

```
demo/
├── providers/                          # YAML manifests (what you write)
│   ├── tools/
│   │   ├── github-reader/              # MCP tool — repository.read
│   │   ├── gitlab-reader/              # MCP tool — same capability, different vendor
│   │   └── rest-code-analyzer/         # REST tool — code.analyze
│   ├── agents/
│   │   ├── langgraph-security-reviewer/  # LangGraph agent — security.code.review
│   │   ├── crewai-security-reviewer/     # CrewAI agent — same capability, different framework
│   │   └── strands-perf-analyzer/        # Strands agent — performance.analyze
│   └── skills/
│       └── security-code-review/       # Skill + SKILL.md — declares deps, not tools
├── 01_register.py                      # Register all manifests, build the registry
└── 02_resolve.py                       # Resolve, use, swap, trace — full demo
```

## Run

```bash
python demo/01_register.py    # Load all YAML manifests into registry
python demo/02_resolve.py     # See CapMesh in action
```

## What you'll see

1. **Register** — 7 providers loaded from YAML (tools, agents, skills)
2. **Resolve** — Orchestrator asks for capabilities, gets the best provider
3. **Results** — Real security scan with findings and verdict
4. **Cross-framework** — LangGraph, CrewAI, Strands agents in one registry
5. **Dynamic discovery** — Add a provider at runtime, no restart
6. **Provider swap** — Replace GitHub with GitLab, zero code changes
7. **Skill dual binding** — Skill auto-resolves its tool dependencies
8. **Policy** — Private providers blocked for unauthorized callers
9. **Audit trail** — Every resolution decision traced
