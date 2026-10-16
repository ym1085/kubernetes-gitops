# Kubernetes 리소스 스키마

이 저장소에서 사용하는 리소스의 YAML 소스와 필드 의미를 정리합니다. Application과 AppProject는 dev 선언을 기준으로 하고, Deployment와 Service, Ingress는 실제 Helm 템플릿을 싣습니다. Pod는 Deployment의 Pod 템플릿을 발췌합니다.

`{{ ... }}`는 Helm이 배포 선언을 생성할 때 치환하는 표현식입니다. `.Values`는 공통 `values.yaml`에 환경별 `values-{env}.yaml`을 덮어쓴 값이고, `.Release.Name`과 `.Release.Namespace`는 릴리스 이름과 배포 namespace입니다. 템플릿 원문은 `kubectl apply`로 직접 적용하지 않습니다.

표의 `[]`는 목록의 각 항목을 뜻합니다. 이 문서는 사용 중인 필드의 설명서이며 전체 Kubernetes API 스키마는 아닙니다.

## 01. Application

배포 소스와 대상 클러스터, namespace, 동기화 정책을 정의합니다.

소스: [argocd/applications/dev/farm-market/farm-market-api.yaml](../argocd/applications/dev/farm-market/farm-market-api.yaml)

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

| 필드 또는 옵션 | 설명 |
| --- | --- |
| `apiVersion` | Argo CD Application API의 그룹과 버전입니다. |
| `kind` | Argo CD의 배포 관리 단위인 Application을 선언합니다. |
| `metadata.name` | Application 리소스의 이름입니다. Helm 릴리스 이름과는 별개입니다. |
| `metadata.namespace` | Application 자체를 생성할 namespace입니다. 애플리케이션의 배포 대상과 구분합니다. |
| `metadata.annotations.argocd.argoproj.io/compare-options` | `ServerSideDiff=true`는 서버 측 Apply의 dry-run 결과를 이용해 원하는 상태와 실제 상태의 차이를 비교하도록 설정합니다. |
| `spec.project` | 이 Application에 적용할 AppProject 이름입니다. 저장소, 배포 대상, 리소스 종류의 허용 범위를 결정합니다. |
| `spec.source.repoURL` | 배포 소스를 가져올 Git 저장소 주소입니다. |
| `spec.source.targetRevision` | 배포할 Git 브랜치, 태그 또는 커밋입니다. |
| `spec.source.path` | Git 저장소 내부의 Helm 차트 경로입니다. |
| `spec.source.helm.releaseName` | Helm 렌더링에 사용할 릴리스 이름입니다. 이 차트의 리소스 이름에 사용됩니다. |
| `spec.source.helm.valueFiles[]` | 차트 디렉터리를 기준으로 읽을 values 파일입니다. 차트 기본값에 덮어씁니다. |
| `spec.destination.server` | 대상 Kubernetes API 서버 주소입니다. `https://kubernetes.default.svc`는 Argo CD가 실행 중인 클러스터를 가리킵니다. |
| `spec.destination.namespace` | 차트 리소스를 배포할 namespace입니다. 이 설정만으로 namespace가 생성되지는 않습니다. |
| `spec.syncPolicy.automated` | 자동 동기화 정책입니다. dev/stg 서비스는 사용하고 prod 서비스는 이 블록 없이 수동 동기화합니다. |
| `spec.syncPolicy.automated.prune` | 자동 동기화 시 소스에서 사라진 관리 대상 리소스를 클러스터에서도 삭제합니다. |
| `spec.syncPolicy.automated.selfHeal` | 클러스터 리소스가 소스의 선언과 달라지면 자동 동기화로 복구합니다. |
| `spec.syncPolicy.syncOptions[]` | 동기화 적용 방식과 순서를 조정하는 옵션 목록입니다. |
| `ServerSideApply=true` | Kubernetes 서버 측 Apply로 리소스를 적용하고 필드 소유권을 관리합니다. |
| `PruneLast=true` | 다른 동기화 단계가 완료되고 리소스가 정상 상태가 된 뒤 마지막 단계에서 prune을 수행합니다. |

옵션 설명: [Argo CD Sync Options](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/).

namespace는 `argocd/bootstrap/{env}/namespaces/` 선언을 관리자가 먼저 적용합니다. API Application은 dev/stg/prod에서 각각 `dev`, `stg`, `master` 브랜치를 참조합니다.

## 01-1. 외부 Helm 차트 Application 옵션

Traefik은 Git 경로 대신 외부 Helm 저장소의 차트와 버전을 지정합니다. 아래 표는 API Application과 다른 필드를 설명합니다.

소스: [argocd/applications/dev/farm-market/traefik.yaml](../argocd/applications/dev/farm-market/traefik.yaml)

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

| 필드 또는 옵션 | 설명 |
| --- | --- |
| `spec.source.repoURL` | Helm 차트를 다운로드할 저장소 주소입니다. |
| `spec.source.chart` | 저장소에서 가져올 차트 이름입니다. Git 소스의 `path` 대신 사용합니다. |
| `spec.source.targetRevision` | 외부 Helm 차트의 고정 버전입니다. Git 브랜치가 아닙니다. |
| `spec.source.helm.skipCrds` | 차트의 CRD 설치를 건너뜁니다. 기존 CRD를 삭제하는 옵션은 아닙니다. |
| `spec.source.helm.values` | 차트에 전달할 인라인 YAML 문자열입니다. 아래 필드는 이 문자열 내부의 Traefik values입니다. |
| `ingressClass.enabled` | Traefik 차트에서 IngressClass 리소스를 생성할지 결정합니다. |
| `ingressClass.isDefaultClass` | 생성한 IngressClass를 클러스터 기본 클래스로 표시할지 결정합니다. |
| `ingressClass.name` | 생성할 IngressClass 이름입니다. API Ingress의 `ingressClassName`과 연결합니다. |
| `providers.kubernetesCRD.enabled` | IngressRoute 등 Traefik 전용 CRD provider를 활성화할지 결정합니다. |
| `providers.kubernetesGateway.enabled` | Kubernetes Gateway API provider를 활성화할지 결정합니다. |
| `providers.kubernetesIngress.enabled` | 표준 Kubernetes Ingress를 읽는 provider를 활성화합니다. |
| `providers.kubernetesIngress.ingressClass` | 처리할 Ingress 클래스를 지정합니다. |
| `providers.kubernetesIngress.namespaces[]` | Ingress provider가 감시할 namespace 범위를 지정합니다. |
| `providers.kubernetesIngress.strictPrefixMatching` | Prefix 경로를 Kubernetes 명세의 경로 요소 단위로 매칭하도록 설정합니다. |
| `service.type` | `NodePort`는 노드의 지정 포트로 Traefik Service에 접근하도록 합니다. |
| `ports.web.nodePort` | HTTP 진입점에 연결할 노드 포트입니다. |
| `ports.websecure.nodePort` | HTTPS 진입점에 연결할 노드 포트입니다. 포트 선언만으로 API 인증서가 구성되지는 않습니다. |
| `resources.requests` | Traefik 컨테이너의 스케줄링에 필요한 CPU와 메모리 요청량입니다. |
| `resources.limits` | Traefik 컨테이너의 리소스 사용 상한입니다. 이 선언은 메모리 상한을 지정합니다. |



## 02. AppProject

Application이 사용할 수 있는 소스 저장소, 배포 대상, 리소스 종류를 제한합니다.

소스: [argocd/projects/dev/farm-market/farm-market.yaml](../argocd/projects/dev/farm-market/farm-market.yaml)

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

| 필드 또는 옵션 | 설명 |
| --- | --- |
| `apiVersion` | Argo CD AppProject API의 그룹과 버전입니다. |
| `kind` | Application의 배포 권한 범위를 정의하는 AppProject를 선언합니다. |
| `metadata.name` | Application의 `spec.project`에서 참조할 이름입니다. |
| `metadata.namespace` | AppProject 자체를 생성할 namespace입니다. |
| `spec.description` | Project의 용도를 설명하는 문자열입니다. |
| `spec.sourceRepos[]` | Application이 배포 소스를 가져올 수 있는 저장소 주소 목록입니다. |
| `spec.destinations[]` | 허용할 클러스터와 namespace 조합의 목록입니다. |
| `spec.destinations[].namespace` | 배포를 허용할 대상 namespace입니다. |
| `spec.destinations[].server` | 배포를 허용할 Kubernetes API 서버 주소입니다. |
| `spec.clusterResourceWhitelist[]` | Namespace처럼 namespace에 속하지 않는 리소스의 허용 목록입니다. 빈 목록이면 허용하지 않습니다. |
| `spec.namespaceResourceWhitelist[]` | namespace에 속하는 리소스 중 Application이 직접 관리하도록 허용할 종류입니다. |
| `spec.namespaceResourceWhitelist[].group` | 리소스의 API 그룹입니다. Service 같은 core API 리소스는 빈 문자열을 사용합니다. |
| `spec.namespaceResourceWhitelist[].kind` | 허용할 리소스 종류입니다. API는 Deployment, Service, Ingress를 선언합니다. |

Pod는 Deployment와 ReplicaSet 컨트롤러가 생성하므로 API Project의 직접 배포 허용 목록에 넣지 않습니다.

Traefik은 별도 [AppProject](../argocd/projects/dev/farm-market/traefik.yaml)를 사용합니다. namespace 리소스는 Deployment, Service, ServiceAccount를 허용하고, 클러스터 리소스는 IngressClass, ClusterRole, ClusterRoleBinding을 허용합니다. `clusterResourceWhitelist` 항목도 `group`과 `kind`로 구성합니다. 서비스 Project에는 `argocd` namespace나 Namespace 생성 권한을 부여하지 않습니다.

## 03. Deployment

ReplicaSet을 통해 Pod 수와 Pod 템플릿을 관리합니다. 컨테이너와 볼륨 등 실행 설정은 다음 Pod 항목에서 설명합니다.

소스: [charts/farm-market-api/templates/deployment.yaml](../charts/farm-market-api/templates/deployment.yaml)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "farm-market-api.selectorLabels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "farm-market-api.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "farm-market-api.selectorLabels" . | nindent 8 }}
    spec:
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: {{ .Values.terminationGracePeriodSeconds }}
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      containers:
        - name: api
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: [ALL]
          ports:
            - name: http
              containerPort: {{ .Values.containerPort }}
          env:
            - name: SPRING_PROFILES_ACTIVE
              value: {{ .Values.springProfile | quote }}
            - name: SERVER_PORT
              value: {{ .Values.containerPort | quote }}
            {{- with .Values.env }}
            {{- toYaml . | nindent 12 }}
            {{- end }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          startupProbe:
            {{- toYaml .Values.startupProbe | nindent 12 }}
          readinessProbe:
            {{- toYaml .Values.readinessProbe | nindent 12 }}
          livenessProbe:
            {{- toYaml .Values.livenessProbe | nindent 12 }}
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir: {}
```

| 필드 또는 옵션 | 설명 |
| --- | --- |
| `apiVersion` | Deployment가 속하는 API 그룹과 버전입니다. |
| `kind` | Pod 복제본과 갱신을 관리하는 Deployment를 선언합니다. |
| `metadata.name` | Deployment 이름입니다. 이 차트는 Helm 릴리스 이름을 사용합니다. |
| `metadata.namespace` | Deployment를 생성할 namespace입니다. |
| `metadata.labels` | Deployment 자체에 붙이는 식별용 레이블입니다. |
| `spec.replicas` | `replicaCount`로 지정하는 원하는 Pod 수입니다. |
| `spec.selector.matchLabels` | Deployment가 관리할 Pod를 선택하는 레이블 조건입니다. Pod 템플릿의 레이블과 일치해야 합니다. |
| `spec.template` | 새 Pod를 만들 때 사용하는 메타데이터와 실행 사양입니다. |
| `spec.template.metadata.labels` | 생성되는 Pod에 붙일 레이블입니다. Deployment selector와 Service selector의 연결 기준입니다. |
| `spec.template.spec` | 컨테이너, 보안, 볼륨, 종료 설정을 포함하는 Pod 실행 사양입니다. |

`farm-market-api.selectorLabels`는 [공통 helper](../charts/farm-market-api/templates/_helpers.tpl)에서 차트 이름인 `app.kubernetes.io/name`과 릴리스 이름인 `app.kubernetes.io/instance`를 생성합니다. Deployment, Pod, Service가 같은 helper를 사용합니다.

## 04. Pod

아래 YAML은 Deployment의 `spec.template` 부분입니다. 독립된 Pod 선언 파일은 없으며, 표의 경로는 이 템플릿을 기준으로 합니다. 발췌한 소스의 들여쓰기와 Helm 표현식은 원본 그대로 유지합니다.

소스: [charts/farm-market-api/templates/deployment.yaml](../charts/farm-market-api/templates/deployment.yaml)

```yaml
    metadata:
      labels:
        {{- include "farm-market-api.selectorLabels" . | nindent 8 }}
    spec:
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: {{ .Values.terminationGracePeriodSeconds }}
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      containers:
        - name: api
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: [ALL]
          ports:
            - name: http
              containerPort: {{ .Values.containerPort }}
          env:
            - name: SPRING_PROFILES_ACTIVE
              value: {{ .Values.springProfile | quote }}
            - name: SERVER_PORT
              value: {{ .Values.containerPort | quote }}
            {{- with .Values.env }}
            {{- toYaml . | nindent 12 }}
            {{- end }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          startupProbe:
            {{- toYaml .Values.startupProbe | nindent 12 }}
          readinessProbe:
            {{- toYaml .Values.readinessProbe | nindent 12 }}
          livenessProbe:
            {{- toYaml .Values.livenessProbe | nindent 12 }}
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir: {}
```

| 필드 또는 옵션 | 설명 |
| --- | --- |
| `metadata.labels` | Pod를 식별하고 Service가 대상 Pod를 선택할 때 사용하는 레이블입니다. |
| `spec.automountServiceAccountToken` | `false`이면 서비스 계정 토큰을 Pod에 자동 마운트하지 않습니다. |
| `spec.terminationGracePeriodSeconds` | Pod 종료 시 프로세스가 정리할 수 있는 유예 시간입니다. `terminationGracePeriodSeconds`에서 읽으며 prod에서는 애플리케이션의 60초 종료 시간보다 길어야 합니다. |
| `spec.securityContext.runAsNonRoot` | 컨테이너가 root 사용자로 실행되지 않도록 요구합니다. 이미지에 적절한 실행 사용자가 있어야 합니다. |
| `spec.securityContext.seccompProfile.type` | `RuntimeDefault`는 컨테이너 런타임이 제공하는 기본 seccomp 시스템 호출 필터를 사용합니다. |
| `spec.imagePullSecrets[].name` | 비공개 이미지 저장소 인증용 Secret 이름입니다. `imagePullSecrets`가 있을 때만 생성하며 같은 namespace에 Secret이 필요합니다. |
| `spec.containers[]` | Pod 안에서 실행할 컨테이너 목록입니다. 이 차트는 API 컨테이너 하나를 선언합니다. |
| `spec.containers[].name` | Pod 내부에서 컨테이너를 구분하는 이름입니다. |
| `spec.containers[].image` | `image.repository`와 `image.tag`를 합친 이미지 주소입니다. 두 값이 비어 있으면 차트 검증이 실패합니다. |
| `spec.containers[].imagePullPolicy` | `IfNotPresent`는 로컬에 없을 때 가져오고, `Always`는 실행 때마다 레지스트리에서 이미지를 확인하며, `Never`는 로컬 이미지만 사용합니다. |
| `spec.containers[].securityContext.allowPrivilegeEscalation` | `false`이면 실행 과정에서 상위 프로세스보다 높은 권한을 얻는 것을 제한합니다. |
| `spec.containers[].securityContext.readOnlyRootFilesystem` | 컨테이너의 루트 파일시스템을 읽기 전용으로 사용합니다. 쓰기 경로는 별도 볼륨이 필요합니다. |
| `spec.containers[].securityContext.capabilities.drop` | `ALL`은 컨테이너의 Linux capability를 모두 제거합니다. |
| `spec.containers[].ports[].name` | 컨테이너 포트의 이름입니다. Service와 probe가 `http`라는 이름으로 참조합니다. |
| `spec.containers[].ports[].containerPort` | `containerPort`에서 읽는 애플리케이션 포트입니다. 이 선언 자체가 프로세스를 실행하거나 외부에 포트를 공개하지는 않습니다. |
| `spec.containers[].env[].name` | 환경변수 이름입니다. `SPRING_PROFILES_ACTIVE`와 `SERVER_PORT`는 템플릿이 생성하고 추가 변수는 `env` 목록에서 읽습니다. |
| `spec.containers[].env[].value` | 환경변수의 문자열 값입니다. Spring 프로필은 `springProfile`, 서버 포트는 `containerPort`에서 생성합니다. |
| `spec.containers[].resources.requests` | 스케줄링에 사용할 CPU와 메모리 요청량입니다. |
| `spec.containers[].resources.limits` | CPU와 메모리 사용 상한입니다. CPU는 제한되고 메모리 상한 초과 시 컨테이너가 OOM 종료될 수 있습니다. |
| `spec.containers[].startupProbe` | 시작 완료를 검사합니다. 성공하기 전에는 readiness와 liveness 검사를 시작하지 않으며, 반복 실패하면 컨테이너를 재시작합니다. |
| `spec.containers[].readinessProbe` | 트래픽을 받을 준비가 되었는지 검사합니다. 실패한 Pod는 Service의 정상 트래픽 대상에서 제외됩니다. |
| `spec.containers[].livenessProbe` | 실행 중인 컨테이너의 상태를 검사합니다. 실패가 임계값에 도달하면 컨테이너를 재시작합니다. |
| `spec.containers[].volumeMounts[].name` | 마운트할 `spec.volumes[].name`을 참조합니다. |
| `spec.containers[].volumeMounts[].mountPath` | 컨테이너 안에서 볼륨을 사용할 경로입니다. |
| `spec.volumes[].name` | Pod 내부에서 볼륨을 구분하는 이름입니다. |
| `spec.volumes[].emptyDir` | Pod 수명에 연결된 임시 볼륨입니다. 컨테이너 재시작에는 유지되지만 Pod가 제거되면 데이터도 사라집니다. |

`env`를 환경 values에서 지정하면 공통 목록 전체를 대체합니다. 빈 문자열, `"false"`, `"0"`도 문자열 그대로 전달합니다. 비밀값을 values에 기록하지 않으며 현재 차트에는 런타임 Secret 주입이 없습니다.

쓰기용 볼륨은 `/tmp`에만 연결되어 있습니다. 환경변수의 `/data/uploads/` 경로에는 쓰기 가능한 볼륨이 연결되어 있지 않습니다.

Probe 내부 옵션은 [공통 values](../charts/farm-market-api/values.yaml)에서 설정합니다.

| 옵션 | 설명 |
| --- | --- |
| `tcpSocket.port` | TCP 연결을 검사할 포트입니다. 컨테이너 포트 이름 `http`를 참조합니다. |
| `periodSeconds` | 검사 주기입니다. 단위는 초입니다. |
| `timeoutSeconds` | 한 번의 검사 응답을 기다리는 제한 시간입니다. |
| `failureThreshold` | 실패로 판정할 연속 실패 횟수입니다. |
| `initialDelaySeconds` | 컨테이너 시작 후 첫 검사까지 기다리는 시간입니다. 현재 values에는 없지만 차트 스키마에서 허용합니다. |

현재 probe는 TCP 연결만 검사하므로 DB 연결이나 API 응답의 정상 여부까지 보장하지 않습니다.

## 05. Service

레이블로 선택한 Pod에 안정적인 클러스터 내부 주소와 포트를 제공합니다.

소스: [charts/farm-market-api/templates/service.yaml](../charts/farm-market-api/templates/service.yaml)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ .Release.Name }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "farm-market-api.selectorLabels" . | nindent 4 }}
spec:
  type: ClusterIP
  selector:
    {{- include "farm-market-api.selectorLabels" . | nindent 4 }}
  ports:
    - name: http
      port: {{ .Values.service.port }}
      targetPort: http
```

| 필드 또는 옵션 | 설명 |
| --- | --- |
| `apiVersion` | Service가 사용하는 core API 버전입니다. |
| `kind` | Pod로 트래픽을 전달하는 Service를 선언합니다. |
| `metadata.name` | Service 이름입니다. Ingress backend에서 같은 이름을 참조합니다. |
| `metadata.namespace` | Service를 생성할 namespace입니다. 대상 Pod도 같은 namespace에서 선택합니다. |
| `metadata.labels` | Service 자체를 식별하는 레이블입니다. 대상 Pod 선택 조건과 구분합니다. |
| `spec.type` | `ClusterIP`는 클러스터 내부 IP로 Service를 제공합니다. API 차트에는 이 유형이 고정되어 있습니다. |
| `spec.selector` | 트래픽을 전달할 Pod의 레이블 조건입니다. Pod 템플릿과 같은 helper로 생성합니다. |
| `spec.ports[].name` | Service 포트의 이름입니다. Ingress가 `http`로 참조합니다. |
| `spec.ports[].port` | `service.port`에서 읽는 Service의 수신 포트입니다. |
| `spec.ports[].targetPort` | 대상 Pod의 컨테이너 포트 이름입니다. `http`를 통해 실제 `containerPort`에 연결합니다. |



## 06. Ingress

HTTP 요청의 호스트와 경로를 기준으로 Service에 연결할 라우팅 규칙을 정의합니다. 실제 요청 처리는 Traefik Ingress controller가 담당합니다.

소스: [charts/farm-market-api/templates/ingress.yaml](../charts/farm-market-api/templates/ingress.yaml)

```yaml
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ .Release.Name }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "farm-market-api.selectorLabels" . | nindent 4 }}
spec:
  ingressClassName: {{ .Values.ingress.className }}
  {{- with .Values.ingress.tls }}
  tls:
    {{- toYaml . | nindent 4 }}
  {{- end }}
  rules:
    - {{- with .Values.ingress.host }}
      host: {{ . | quote }}
      {{- end }}
      http:
        paths:
          {{- range .Values.ingress.paths }}
          - path: {{ . | quote }}
            pathType: Prefix
            backend:
              service:
                name: {{ $.Release.Name }}
                port:
                  name: http
          {{- end }}
{{- end }}
```

| 필드 또는 옵션 | 설명 |
| --- | --- |
| `ingress.enabled` | Helm values의 생성 조건입니다. `false`이면 Ingress 리소스 자체를 생성하지 않습니다. |
| `apiVersion` | Ingress API의 그룹과 버전입니다. |
| `kind` | HTTP 라우팅 규칙인 Ingress를 선언합니다. |
| `metadata.name` | Ingress 리소스의 이름입니다. |
| `metadata.namespace` | Ingress를 생성할 namespace입니다. backend Service와 TLS Secret도 이 namespace를 기준으로 참조합니다. |
| `metadata.labels` | Ingress를 식별하는 레이블입니다. |
| `spec.ingressClassName` | `ingress.className`에서 읽는 IngressClass 이름입니다. 이 규칙을 처리할 컨트롤러와 연결합니다. |
| `spec.tls[]` | `ingress.tls`에 항목이 있을 때만 생성하는 TLS 설정 목록입니다. |
| `spec.tls[].hosts[]` | TLS 인증서로 처리할 호스트 목록입니다. 라우팅 호스트와 인증서의 이름이 맞아야 합니다. |
| `spec.tls[].secretName` | TLS 인증서와 개인키를 저장한 Secret 이름입니다. 이 차트는 Secret을 생성하지 않습니다. |
| `spec.rules[]` | 호스트와 HTTP 경로별 라우팅 규칙 목록입니다. |
| `spec.rules[].host` | `ingress.host`가 있을 때만 생성합니다. 생략하면 호스트 이름으로 요청을 제한하지 않습니다. |
| `spec.rules[].http.paths[]` | `ingress.paths`의 각 경로로 생성하는 라우팅 목록입니다. |
| `spec.rules[].http.paths[].path` | 요청을 매칭할 URL 경로입니다. |
| `spec.rules[].http.paths[].pathType` | `Prefix`로 고정되어 있습니다. `/`로 구분한 경로 요소 단위로 매칭하므로 `/api/v1`은 `/api/v1/items`에 매칭되지만 `/api/v10`에는 매칭되지 않습니다. |
| `spec.rules[].http.paths[].backend.service.name` | 요청을 전달할 Service 이름입니다. Helm 릴리스 이름을 사용합니다. |
| `spec.rules[].http.paths[].backend.service.port.name` | 대상 Service의 포트 이름입니다. 컨테이너 포트 번호가 아닌 Service의 `http` 포트를 참조합니다. |

경로와 TLS 동작 참고: [Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/).

현재 `ingress.tls`는 빈 목록입니다. Argo CD 관리 화면의 TLS 설정과 API Ingress의 TLS 설정은 별개입니다.

요청은 Traefik에서 Ingress 규칙을 거쳐 Service의 `http` 포트로 전달되고, Service는 Pod의 `http` 컨테이너 포트에 연결합니다. Ingress 경로 선언 자체는 URL 경로를 다시 쓰지 않습니다.
