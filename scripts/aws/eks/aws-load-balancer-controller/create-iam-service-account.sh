#!/bin/bash
set -euo pipefail

: "${CLUSTER_NAME:?CLUSTER_NAME is required}"
: "${ACCOUNT_ID:?ACCOUNT_ID is required}"
: "${DEFAULT_REGION:?DEFAULT_REGION is required}"

# k8s ServiceAccount를 만들고, 그 ServiceAccount와 연결된 IAM Role을 동시에 생성/연결하여
# Pod가 해당 IAM 권한으로 AWS 리소스를 사용할 수 있게 만드는 작업
eksctl create iamserviceaccount \
  --cluster "$CLUSTER_NAME" \
  --namespace kube-system \
  --name aws-load-balancer-controller \
  --attach-policy-arn "arn:aws:iam::${ACCOUNT_ID}:policy/AWSLoadBalancerControllerIAMPolicy" \
  --region "$DEFAULT_REGION" \
  --approve
