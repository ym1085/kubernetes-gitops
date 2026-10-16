#!/bin/bash
set -euo pipefail
echo "==================================="
echo " Kubernetes in Docker (kind) Setup "
echo "==================================="
echo
# 스크립트 파일이 위치한 디렉토리의 절대 경로를 구함
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
kind create cluster --config "$SCRIPT_DIR/nodeport-config.yaml"
kubectl --context kind-helm-cluster get nodes
