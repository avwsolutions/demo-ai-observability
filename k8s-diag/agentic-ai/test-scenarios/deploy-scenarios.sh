#!/bin/bash

# Deploy Agentic AI Test Scenarios
# This script deploys 3 broken pods that demonstrate autonomous learning

set -e

echo "================================================"
echo "Deploying Agentic AI Test Scenarios"
echo "================================================"
echo ""

# Create namespace
echo "Creating namespace: agentic-demo"
kubectl create namespace agentic-demo --dry-run=client -o yaml | kubectl apply -f -
echo ""

# Deploy Scenario 1: CrashLoop with missing env
echo "Scenario 1: Deploying mysql-client (CrashLoopBackOff - missing env)"
kubectl apply -f scenario-1-crashloop-missing-env.yaml
echo "   Expected: Pod will crash due to missing MYSQL_HOST and MYSQL_ROOT_PASSWORD"
echo ""

# Deploy Scenario 2: OOM
echo "Scenario 2: Deploying memory-hungry (OOMKilled - insufficient memory)"
kubectl apply -f scenario-2-oom-progressive.yaml
echo "   Expected: Pod will be OOMKilled when memory exceeds 128Mi"
echo ""

# Deploy Scenario 3: Image typos
echo "Scenario 3: Deploying web-server and alpine-app (ImagePullBackOff - typos)"
kubectl apply -f scenario-3-image-typo.yaml
echo "   Expected: Pods will fail to pull images due to typos (latst, apline)"
echo ""

echo "================================================"
echo "Deployment Complete!"
echo "================================================"
echo ""
echo "Wait 30 seconds for issues to appear, then check:"
echo "  kubectl get pods -n agentic-demo"
echo ""
echo "Expected failures:"
echo "  - mysql-client:   CrashLoopBackOff"
echo "  - memory-hungry:  OOMKilled"
echo "  - web-server:     ImagePullBackOff"
echo "  - alpine-app:     ImagePullBackOff"
echo ""
