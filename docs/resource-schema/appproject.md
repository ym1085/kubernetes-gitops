# AppProject

[문서 목록](README.md)

dev 설정 기준이며, `[]`는 목록의 각 항목을 뜻합니다.

## 01. AppProject

Application이 사용할 수 있는 소스 저장소, 배포 대상, 리소스 종류를 제한합니다.

소스: [argocd/projects/dev/farm-market/farm-market.yaml](../../argocd/projects/dev/farm-market/farm-market.yaml)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: farm-market-dev
  namespace: argocd
spec:
  description: Farm Market API (dev)
  sourceRepos:
    - https://github.com/ym1085/kubernetes-gitops.git
  destinations:
    - namespace: farm-market-dev
      server: https://kubernetes.default.svc
  clusterResourceWhitelist: []
  namespaceResourceWhitelist:
    - group: apps
      kind: Deployment
    - group: ""
      kind: Service
    - group: networking.k8s.io
      kind: Ingress
```

| 필드 | 설명 |
| --- | --- |
| `apiVersion` | Argo CD AppProject API의 그룹과 버전 |
| `kind` | Application의 배포 권한 범위를 정의하는 AppProject 선언 |
| `metadata.name` | Application의 `spec.project`에서 참조할 이름 |
| `metadata.namespace` | AppProject 자체를 생성할 namespace |
| `spec.description` | Project의 용도를 설명하는 문자열 |
| `spec.sourceRepos[]` | Application이 배포 소스를 가져올 수 있는 저장소 주소 목록 |
| `spec.destinations[]` | 허용할 클러스터와 namespace 조합의 목록 |
| `spec.destinations[].namespace` | 배포를 허용할 대상 namespace |
| `spec.destinations[].server` | 배포를 허용할 Kubernetes API 서버 주소 |
| `spec.clusterResourceWhitelist[]` | Namespace처럼 namespace에 속하지 않는 리소스의 허용 목록<br>빈 목록이면 허용하지 않음 |
| `spec.namespaceResourceWhitelist[]` | namespace에 속하는 리소스 중 Application이 직접 관리하도록 허용할 종류 |
| `spec.namespaceResourceWhitelist[].group` | 리소스의 API 그룹<br>Service 같은 core API 리소스는 빈 문자열을 사용 |
| `spec.namespaceResourceWhitelist[].kind` | 허용할 리소스 종류<br>API는 Deployment, Service, Ingress 선언 |

Pod는 Deployment와 ReplicaSet 컨트롤러가 생성하므로 API Project의 직접 배포 허용 목록에 넣지 않습니다.

Traefik은 별도 [AppProject](../../argocd/projects/dev/farm-market/traefik.yaml)를 사용합니다. namespace 리소스는 Deployment, Service, ServiceAccount를 허용하고, 클러스터 리소스는 IngressClass, ClusterRole, ClusterRoleBinding을 허용합니다. `clusterResourceWhitelist` 항목도 `group`과 `kind`로 구성합니다. 서비스 Project에는 `argocd` namespace나 Namespace 생성 권한을 부여하지 않습니다.
