#!/bin/bash
set -euo pipefail
echo "==================================="
echo " Kubernetes in Docker (kind) Stop  "
echo "==================================="
kind delete cluster --name helm-cluster
