#!/bin/bash

echo "Deleting existing deployments..."
kubectl delete -f k8s-manifests/deploy-all.yaml -n ai-apps --ignore-not-found

echo " Applying deployments..."
kubectl apply -f k8s-manifests/deploy-all.yaml -n ai-apps

echo "✅ Done."

