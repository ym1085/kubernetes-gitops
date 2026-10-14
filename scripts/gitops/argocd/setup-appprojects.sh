#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  dev|stg|prod) profile="$1" ;;
  *) echo "Usage: $0 <dev|stg|prod>" >&2; exit 2 ;;
esac

root_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
echo "Kubernetes context: $(kubectl config current-context)"
kubectl apply -f "$root_dir/argocd/bootstrap/$profile/namespaces.yaml"
kubectl apply -f "$root_dir/argocd/bootstrap/$profile/root-project.yaml"
kubectl apply -f "$root_dir/argocd/bootstrap/$profile/projects-root.yaml"
echo "Argo CD will reconcile AppProjects from Git ($profile)."
