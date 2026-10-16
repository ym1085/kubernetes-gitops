#!/bin/bash
set -euo pipefail

: "${CLUSTER_NAME:?CLUSTER_NAME is required}"
: "${DEFAULT_REGION:?DEFAULT_REGION is required}"
: "${VPC_ID:?VPC_ID is required}"

# docs: https://artifacthub.io/packages/helm/aws/aws-load-balancer-controller

# helm install aws-lb-controller eks/aws-load-balancer-controller
# helm install aws-lb-controller https://aws.github.io/eks-charts/aws-load-balancer-controller
helm repo add eks https://aws.github.io/eks-charts
helm repo update
sleep 10

# AWS LoadBalancer Controller는 k8s 리소스를 기반으로 ALB/NLB를 자동 생성 및 관리 해주는 컨트롤러
# upgrade --install: 설치되어 있으면 업그레이드, 없으면 설치 진행
# -n: 어떤 네임스페이스에 설치할 것인지?
# --set clusterName=$CLUSTER_NAME: EKS Cluster 이름
# --set region=$DEFAULT_REGION: EKS Cluster가 위치한 AWS Region
# --set vpcId=$VPC_ID: EKS Cluster가 위치한 VPC ID
# --set serviceAccount.create=false: ServiceAccount 생성 여부
# --set serviceAccount.name=aws-load-balancer-controller: ServiceAccount 이름
helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set "clusterName=$CLUSTER_NAME" \
  --set "region=$DEFAULT_REGION" \
  --set "vpcId=$VPC_ID" \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller

sleep 10
echo

kubectl -n kube-system rollout status deploy/aws-load-balancer-controller
kubectl -n kube-system logs deploy/aws-load-balancer-controller | tail -n 50
