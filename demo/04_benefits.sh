#!/bin/bash
# Step 4: Benefits — live demonstration of what CapMesh gives you
#
# We run the Python script here because the benefits demo needs
# to simulate actual service calls and show real scan results.
# The CLI handles build/register/resolve; the orchestrator code
# that USES resolved bindings is where Python comes in — just
# like how 'docker run' starts your app, but the app is your code.

echo "============================================================"
echo "  CAPMESH DEMO - Step 4: True Benefits"
echo "  Same task, two ways, then change everything"
echo "============================================================"
echo ""

python demo/04_benefits.py
