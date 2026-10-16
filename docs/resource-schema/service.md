# Service

[문서 목록](README.md)

## 01. Service

레이블로 선택한 Pod에 안정적인 클러스터 내부 주소와 포트를 제공합니다.

소스: [charts/farm-market-api/templates/service.yaml](../../charts/farm-market-api/templates/service.yaml)

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

| 필드 | 설명 |
| --- | --- |
| `apiVersion` | Service가 사용하는 core API 버전 |
| `kind` | Pod로 트래픽을 전달하는 Service 선언 |
| `metadata.name` | Service 이름<br>Ingress backend에서 같은 이름을 참조 |
| `metadata.namespace` | Service를 생성할 namespace<br>대상 Pod도 같은 namespace에서 선택 |
| `metadata.labels` | Service 자체를 식별하는 레이블<br>대상 Pod 선택 조건과 구분 |
| `spec.type` | `ClusterIP`는 클러스터 내부 IP로 Service를 제공<br>API 차트에는 이 유형이 고정 |
| `spec.selector` | 트래픽을 전달할 Pod의 레이블 조건<br>Pod 템플릿과 같은 helper로 생성 |
| `spec.ports[].name` | Service 포트의 이름<br>Ingress가 `http`로 참조 |
| `spec.ports[].port` | `service.port`에서 읽는 Service의 수신 포트 |
| `spec.ports[].targetPort` | 대상 Pod의 컨테이너 포트 이름<br>`http`를 통해 실제 `containerPort`에 연결 |
