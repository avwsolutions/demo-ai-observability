#!/bin/bash

# Cleanup Agentic AI Test Scenarios

echo "Cleaning up agentic-demo namespace..."
kubectl delete namespace agentic-demo --ignore-not-found=true

echo "✅ Cleanup complete!"
