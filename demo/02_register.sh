#!/bin/bash
# Step 2: Register — store providers in local registry
# Like 'docker load' or 'docker push'

echo "============================================================"
echo "  CAPMESH DEMO - Step 2: Register"
echo "============================================================"
echo ""

echo "--- Register Tools ---"
capmesh tool register --file demo/providers/tools/github-reader/manifest.yaml
capmesh tool register --file demo/providers/tools/gitlab-reader/manifest.yaml
capmesh tool register --file demo/providers/tools/rest-code-analyzer/manifest.yaml
echo ""

echo "--- Register Agents ---"
capmesh agent register --file demo/providers/agents/langgraph-security-reviewer/manifest.yaml
capmesh agent register --file demo/providers/agents/crewai-security-reviewer/manifest.yaml
capmesh agent register --file demo/providers/agents/strands-perf-analyzer/manifest.yaml
echo ""

echo "--- Register Skills ---"
capmesh skill register --file demo/providers/skills/security-code-review/manifest.yaml
echo ""

echo "============================================================"
echo "  Search and inspect"
echo "============================================================"
echo ""

echo "$ capmesh search security"
capmesh search security
echo ""

echo "$ capmesh providers security.code.review"
capmesh providers security.code.review
echo ""

echo "$ capmesh providers repository.read"
capmesh providers repository.read
echo ""

echo "$ capmesh agent inspect security crewai-security-reviewer 3.1.0 --json"
capmesh agent inspect security crewai-security-reviewer 3.1.0 --json
echo ""

echo "$ capmesh graph security.code.review --json"
capmesh graph security.code.review --json
echo ""

echo "============================================================"
echo "  Registry built. Next: ./demo/03_resolve.sh"
echo "============================================================"
