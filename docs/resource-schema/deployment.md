# Deployment

[문서 목록](README.md)

## 01. Deployment

ReplicaSet을 통해 Pod 수와 Pod 템플릿을 관리합니다. 컨테이너와 볼륨 등 실행 설정은 다음 Pod 항목에서 설명합니다.

소스: [charts/farm-market-api/templates/deployment.yaml](../../charts/farm-market-api/templates/deployment.yaml)

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

| 필드 | 설명 |
| --- | --- |
| `apiVersion` | Deployment가 속하는 API 그룹과 버전 |
| `kind` | Pod 복제본과 갱신을 관리하는 Deployment 선언 |
| `metadata.name` | Deployment 이름<br>이 차트는 Helm 릴리스 이름을 사용 |
| `metadata.namespace` | Deployment를 생성할 namespace |
| `metadata.labels` | Deployment 자체에 붙이는 식별용 레이블 |
| `spec.replicas` | `replicaCount`로 지정하는 원하는 Pod 수 |
| `spec.selector.matchLabels` | Deployment가 관리할 Pod를 선택하는 레이블 조건<br>Pod 템플릿의 레이블과 일치해야 함 |
| `spec.template` | 새 Pod를 만들 때 사용하는 메타데이터와 실행 사양 |
| `spec.template.metadata.labels` | 생성되는 Pod에 붙일 레이블<br>Deployment selector와 Service selector의 연결 기준 |
| `spec.template.spec` | 컨테이너, 보안, 볼륨, 종료 설정을 포함하는 Pod 실행 사양 |

`farm-market-api.selectorLabels`는 [공통 helper](../../charts/farm-market-api/templates/_helpers.tpl)에서 차트 이름인 `app.kubernetes.io/name`과 릴리스 이름인 `app.kubernetes.io/instance`를 생성합니다. Deployment, Pod, Service가 같은 helper를 사용합니다.
