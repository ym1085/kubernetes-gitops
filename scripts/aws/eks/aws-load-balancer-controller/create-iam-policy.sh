#!/bin/bash
set -euo pipefail

policy_file=$(mktemp)
trap 'rm -f "$policy_file"' EXIT

# AWS LoadBalancerController가 ALB/NLB를 생성 및 관리하기 위해 필요한 IAM 권한을 정의한 문서로
# 해당 IAM 정책(권한)을 생성 후 사용하기 위함
curl -fsSL -o "$policy_file" \
  https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json

# AWS LoadBalancerController IAM 정책 생성
aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document "file://$policy_file"
