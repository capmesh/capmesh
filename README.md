# CapMesh

Service discovery for the agentic world: dynamically discover and bind Agents, Skills and Tools by capability.

## Installation

```bash
pip install capmesh
```

For the registry server:
```bash
pip install "capmesh[server]"
```

## Quick Start

### Register a provider

```bash
# Scaffold a new agent manifest
capmesh agent init --namespace security --name reviewer --version 1.0.0 --owner my-team

# Register it
capmesh agent register --file manifest.yaml
```

### Search and resolve

```bash
# Search for providers
capmesh search "security"

# Resolve a capability to a provider
capmesh resolve security.code.review

# Show full resolution trace
capmesh resolve security.code.review --trace

# List all providers for a capability
capmesh providers security.code.review
```

### Run the registry server

```bash
capmesh server start --port 8080
```

Or with Docker:
```bash
docker run -p 8080:8080 -v capmesh-data:/data capmesh-server
```

### API

```bash
# Register a provider
curl -X POST http://localhost:8080/v1/providers/register \
  -H "Content-Type: application/json" \
  -d @manifest.json

# Resolve a capability
curl -X POST http://localhost:8080/v1/resolve \
  -H "Content-Type: application/json" \
  -d '{"capability": "security.code.review", "contract": "v1", "caller": {"identity": "my-app"}}'
```

## Demo

Run the proof-of-value demo:
```bash
python examples/demo.py
```

## Key Concepts

- **Capability**: What a consumer needs (e.g., `security.code.review`)
- **Provider**: An Agent, Skill, or Tool that provides a capability
- **Resolution**: Finding and selecting the best provider for a capability
- **Binding**: Protocol-specific connection info to use the provider
- **Trace**: Auditable record of every resolution decision

## License

Apache 2.0
