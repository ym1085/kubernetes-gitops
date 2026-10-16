# Application

[문서 목록](README.md)

dev 설정 기준이며, `[]`는 목록의 각 항목을 뜻합니다.

## 01. API Application

배포 소스와 대상 클러스터, namespace, 동기화 정책을 정의합니다.

소스: [argocd/applications/dev/farm-market/farm-market-api.yaml](../../argocd/applications/dev/farm-market/farm-market-api.yaml)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: farm-market-api-dev
  namespace: argocd
  annotations:
    argocd.argoproj.io/compare-options: ServerSideDiff=true
spec:
  project: farm-market-dev
  source:
    repoURL: https://github.com/ym1085/kubernetes-gitops.git
    targetRevision: dev
    path: charts/farm-market-api
    helm:
      releaseName: farm-market-api
      valueFiles:
        - values-dev.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: farm-market-dev
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - ServerSideApply=true
      - PruneLast=true
```

| 필드 | 설명 |
| --- | --- |
| `apiVersion` | Argo CD Application API의 그룹과 버전 |
| `kind` | Argo CD의 배포 관리 단위인 Application 선언 |
| `metadata.name` | Application 이름<br>Helm 릴리스 이름과 별개 |
| `metadata.namespace` | Application 자체를 생성할 namespace<br>애플리케이션의 배포 대상과 구분 |
| `metadata.annotations.argocd.argoproj.io/compare-options` | `ServerSideDiff=true`: 서버 측 Apply의 dry-run 결과로 선언과 실제 상태를 비교 |
| `spec.project` | 이 Application에 적용할 AppProject 이름<br>저장소, 배포 대상, 리소스 종류의 허용 범위를 결정 |
| `spec.source.repoURL` | 배포 소스를 가져올 Git 저장소 주소 |
| `spec.source.targetRevision` | 배포할 Git 브랜치, 태그 또는 커밋 |
| `spec.source.path` | Git 저장소 내부의 Helm 차트 경로 |
| `spec.source.helm.releaseName` | Helm 렌더링에 사용할 릴리스 이름<br>이 차트의 리소스 이름에 사용 |
| `spec.source.helm.valueFiles[]` | 차트 디렉터리를 기준으로 읽을 values 파일<br>차트 기본값에 덮어씀 |
| `spec.destination.server` | 대상 Kubernetes API 서버 주소<br>`https://kubernetes.default.svc`는 Argo CD가 실행 중인 클러스터를 의미 |
| `spec.destination.namespace` | 차트 리소스를 배포할 namespace<br>이 설정만으로 namespace가 생성되지 않음 |
| `spec.syncPolicy.automated` | 자동 동기화 정책<br>dev/stg 서비스는 사용하고 prod 서비스는 이 블록 없이 수동 동기화 |
| `spec.syncPolicy.automated.prune` | 자동 동기화 시 소스에서 사라진 관리 대상 리소스를 클러스터에서도 삭제 |
| `spec.syncPolicy.automated.selfHeal` | 클러스터 리소스가 소스의 선언과 달라지면 자동 동기화로 복구 |
| `spec.syncPolicy.syncOptions[]` | 동기화 적용 방식과 순서를 조정하는 옵션 목록 |
| `ServerSideApply=true` | Kubernetes 서버 측 Apply로 리소스를 적용하고 필드 소유권을 관리 |
| `PruneLast=true` | 다른 리소스의 적용과 정상 상태 확인 후 마지막에 삭제 처리 |

참고: [Argo CD 동기화 옵션](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/)

namespace는 `argocd/bootstrap/{env}/namespaces/` 선언을 관리자가 먼저 적용합니다. API Application은 dev/stg/prod에서 각각 `dev`, `stg`, `master` 브랜치를 참조합니다.

## 02. Traefik Application

Traefik은 외부 Helm 저장소에서 지정한 버전의 차트를 가져옵니다.

소스: [argocd/applications/dev/farm-market/traefik.yaml](../../argocd/applications/dev/farm-market/traefik.yaml)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: traefik-dev
  namespace: argocd
  annotations:
    argocd.argoproj.io/compare-options: ServerSideDiff=true
spec:
  project: infra-dev
  source:
    repoURL: https://traefik.github.io/charts
    chart: traefik
    targetRevision: 41.7.1
    helm:
      releaseName: traefik-dev
      skipCrds: true
      values: |
        ingressClass:
          enabled: true
          isDefaultClass: false
          name: traefik-dev
        providers:
          kubernetesCRD:
            enabled: false
          kubernetesGateway:
            enabled: false
          kubernetesIngress:
            enabled: true
            ingressClass: traefik-dev
            namespaces:
              - farm-market-dev
            strictPrefixMatching: true
        service:
          type: NodePort
        ports:
          web:
            nodePort: 30080
          websecure:
            nodePort: 30443
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            memory: 256Mi
  destination:
    server: https://kubernetes.default.svc
    namespace: traefik-dev
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - ServerSideApply=true
      - PruneLast=true
```

| 필드 | 설명 |
| --- | --- |
| `spec.source.repoURL` | Helm 차트를 다운로드할 저장소 주소 |
| `spec.source.chart` | 저장소에서 가져올 차트 이름<br>Git 소스의 `path` 대신 사용 |
| `spec.source.targetRevision` | 외부 Helm 차트의 고정 버전<br>Git 브랜치가 아님 |
| `spec.source.helm.skipCrds` | 차트의 CRD 설치를 생략<br>기존 CRD를 삭제하는 옵션은 아님 |
| `spec.source.helm.values` | 차트에 전달할 인라인 YAML 문자열 |

아래 옵션은 `spec.source.helm.values` 안에 작성합니다.

| Traefik 옵션 | 설명 |
| --- | --- |
| `ingressClass.enabled` | IngressClass 생성 여부 |
| `ingressClass.isDefaultClass` | 클러스터 기본 IngressClass로 지정할지 여부 |
| `ingressClass.name` | 생성할 IngressClass 이름<br>API Ingress의 `ingressClassName`과 연결 |
| `providers.kubernetesCRD.enabled` | IngressRoute 등 Traefik 전용 CRD 사용 여부 |
| `providers.kubernetesGateway.enabled` | Kubernetes Gateway API 사용 여부 |
| `providers.kubernetesIngress.enabled` | 표준 Kubernetes Ingress를 읽는 provider를 활성화 |
| `providers.kubernetesIngress.ingressClass` | 처리할 Ingress 클래스를 지정 |
| `providers.kubernetesIngress.namespaces[]` | Ingress provider가 감시할 namespace 범위를 지정 |
| `providers.kubernetesIngress.strictPrefixMatching` | Prefix 경로를 Kubernetes 명세의 경로 요소 단위로 매칭 |
| `service.type` | `NodePort`는 노드의 지정 포트로 Traefik Service에 접근 가능 |
| `ports.web.nodePort` | HTTP 진입점에 연결할 노드 포트 |
| `ports.websecure.nodePort` | HTTPS 진입점에 연결할 노드 포트<br>포트 선언만으로 API 인증서가 구성되지 않음 |
| `resources.requests` | Traefik 컨테이너의 스케줄링에 필요한 CPU와 메모리 요청량 |
| `resources.limits` | Traefik 컨테이너의 리소스 사용 상한<br>이 선언은 메모리 상한을 지정 |
