#!/bin/bash
# Step 1: Build — validate manifests and compute digests
# Like 'docker build' but for agents, tools, and skills

echo "============================================================"
echo "  CAPMESH DEMO - Step 1: Build"
echo "============================================================"
echo ""

echo "--- Build Tools ---"
capmesh tool build --directory demo/providers/tools/github-reader/
echo ""
capmesh tool build --directory demo/providers/tools/gitlab-reader/
echo ""
capmesh tool build --directory demo/providers/tools/rest-code-analyzer/
echo ""

echo "--- Build Agents ---"
capmesh agent build --directory demo/providers/agents/langgraph-security-reviewer/
echo ""
capmesh agent build --directory demo/providers/agents/crewai-security-reviewer/
echo ""
capmesh agent build --directory demo/providers/agents/strands-perf-analyzer/
echo ""

echo "--- Build Skills ---"
capmesh skill build --directory demo/providers/skills/security-code-review/
echo ""

echo "============================================================"
echo "  All manifests valid. Ready to register."
echo "  Next: ./demo/02_register.sh"
echo "============================================================"
