# Contributing to CapMesh

Thank you for your interest in contributing to CapMesh! This guide will help you get started.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_ORG/capmesh.git
cd capmesh

# Install in development mode with all extras
pip install -e ".[server,dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=capmesh --cov-report=term-missing
```

## Project Structure

```
src/capmesh/
├── models/       # Pydantic data models (manifests, capabilities, resolution)
├── registry/     # Dual storage (YAML files + SQLite index)
├── resolver/     # Deterministic capability resolution pipeline
├── policy/       # Pluggable policy engine (visibility, environment, status)
├── adapters/     # Binding adapters (A2A, MCP, Skill, REST)
├── telemetry/    # Resolution trace storage
├── health/       # Cached health checker
├── server/       # FastAPI registry API
└── cli/          # Typer CLI commands
```

## Development Workflow

1. **Create a branch** for your feature or fix
2. **Write tests first** (TDD) — add failing tests, then implement
3. **Run the full test suite** to ensure no regressions
4. **Keep coverage above 80%** — check with `pytest --cov=capmesh`
5. **Submit a pull request** with a clear description

## Code Style

- Python 3.10+ features (union types with `|`, match statements)
- Pydantic v2 for all data models
- Type annotations on all public functions
- No unnecessary abstractions — YAGNI

## Running the Demo

```bash
python examples/demo.py
```

## Running the Server

```bash
# Local
capmesh server start --port 8080

# Docker
docker build -t capmesh-server .
docker run -p 8080:8080 -v capmesh-data:/data capmesh-server
```

## Test Structure

- `tests/unit/` — fast unit tests, no external I/O
- `tests/integration/` — CLI and server tests with real storage
- `tests/e2e/` — full lifecycle acceptance tests

## Adding a New Adapter

1. Create `src/capmesh/adapters/your_adapter.py`
2. Implement `supports(manifest) -> bool` and `bind(manifest, trace_id) -> Binding`
3. Register in `src/capmesh/adapters/defaults.py`
4. Add tests in `tests/unit/test_adapters.py`

## Adding a New Policy Rule

1. Create a class implementing the `PolicyRule` protocol in `src/capmesh/policy/rules.py`
2. Add to `default_policy_engine()` in `src/capmesh/policy/engine.py`
3. Add tests in `tests/unit/test_policy.py`

## Reporting Issues

Please open an issue on GitHub with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- CapMesh version (`capmesh --version` or `python -c "import capmesh; print(capmesh.__version__)"`)

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
