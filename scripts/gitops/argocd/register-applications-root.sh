#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  dev|stg|prod) profile="$1" ;;
  *) echo "Usage: $0 <dev|stg|prod>" >&2; exit 2 ;;
esac

root_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
echo "Kubernetes context: $(kubectl config current-context)"
if ! kubectl get appproject "gitops-$profile" -n argocd >/dev/null 2>&1; then
  echo "Run register-projects-root.sh $profile first." >&2
  exit 1
fi
kubectl apply -f "$root_dir/argocd/bootstrap/$profile/namespaces"
kubectl apply -f "$root_dir/argocd/bootstrap/$profile/roots/applications-root.yaml"
echo "Argo CD will reconcile Applications from Git ($profile)."
