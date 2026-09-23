#!/bin/bash
# Step 3: Resolve — discover and bind capabilities
# This is what makes CapMesh different from a plain registry

echo "============================================================"
echo "  CAPMESH DEMO - Step 3: Resolve"
echo "============================================================"
echo ""

echo "--- Resolve: security.code.review ---"
echo "$ capmesh resolve security.code.review"
capmesh resolve security.code.review
echo ""

echo "--- Resolve with full trace ---"
echo "$ capmesh resolve security.code.review --trace"
capmesh resolve security.code.review --trace
echo ""

echo "--- Resolve: repository.read ---"
echo "$ capmesh resolve repository.read"
capmesh resolve repository.read
echo ""

echo "--- Resolve: performance.analyze ---"
echo "$ capmesh resolve performance.analyze"
capmesh resolve performance.analyze
echo ""

echo "--- Resolve: code.analyze ---"
echo "$ capmesh resolve code.analyze"
capmesh resolve code.analyze
echo ""

echo "--- Resolve as JSON (for programmatic use) ---"
echo "$ capmesh resolve security.code.review --json"
capmesh resolve security.code.review --json
echo ""

echo "--- Version constraint ---"
echo "$ capmesh resolve security.code.review --version '>=1.0,<2.0'"
capmesh resolve security.code.review --version ">=1.0,<2.0"
echo ""

echo "============================================================"
echo "  Every resolve produces an auditable trace."
echo "  Next: ./demo/04_benefits.sh"
echo "============================================================"
