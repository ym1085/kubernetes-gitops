# Ingress

[문서 목록](README.md)

## 01. Ingress

HTTP 요청의 호스트와 경로를 기준으로 Service에 연결할 라우팅 규칙을 정의합니다. 실제 요청 처리는 Traefik Ingress controller가 담당합니다.

소스: [charts/farm-market-api/templates/ingress.yaml](../../charts/farm-market-api/templates/ingress.yaml)

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

| 필드 | 설명 |
| --- | --- |
| `ingress.enabled` | Helm values의 생성 조건<br>`false`이면 Ingress 리소스 자체를 생성하지 않음 |
| `apiVersion` | Ingress API의 그룹과 버전 |
| `kind` | HTTP 라우팅 규칙인 Ingress 선언 |
| `metadata.name` | Ingress 리소스의 이름 |
| `metadata.namespace` | Ingress를 생성할 namespace<br>backend Service와 TLS Secret도 이 namespace를 기준으로 참조 |
| `metadata.labels` | Ingress를 식별하는 레이블 |
| `spec.ingressClassName` | `ingress.className`에서 읽는 IngressClass 이름<br>이 규칙을 처리할 컨트롤러와 연결 |
| `spec.tls[]` | `ingress.tls`에 항목이 있을 때만 생성하는 TLS 설정 목록 |
| `spec.tls[].hosts[]` | TLS 인증서로 처리할 호스트 목록<br>라우팅 호스트와 인증서의 이름이 일치해야 함 |
| `spec.tls[].secretName` | TLS 인증서와 개인키를 저장한 Secret 이름<br>이 차트는 Secret을 생성하지 않음 |
| `spec.rules[]` | 호스트와 HTTP 경로별 라우팅 규칙 목록 |
| `spec.rules[].host` | `ingress.host`가 있을 때만 생성<br>생략하면 호스트 이름으로 요청을 제한하지 않음 |
| `spec.rules[].http.paths[]` | `ingress.paths`의 각 경로로 생성하는 라우팅 목록 |
| `spec.rules[].http.paths[].path` | 요청을 매칭할 URL 경로 |
| `spec.rules[].http.paths[].pathType` | `Prefix`로 고정<br>`/`로 구분한 경로 요소 단위로 매칭하므로 `/api/v1`은 `/api/v1/items`에 매칭되지만 `/api/v10`에는 매칭되지 않음 |
| `spec.rules[].http.paths[].backend.service.name` | 요청을 전달할 Service 이름<br>Helm 릴리스 이름을 사용 |
| `spec.rules[].http.paths[].backend.service.port.name` | 대상 Service의 포트 이름<br>컨테이너 포트 번호가 아닌 Service의 `http` 포트를 참조 |

참고: [Kubernetes Ingress 경로와 TLS](https://kubernetes.io/docs/concepts/services-networking/ingress/)

현재 `ingress.tls`는 빈 목록입니다. Argo CD 관리 화면의 TLS 설정과 API Ingress의 TLS 설정은 별개입니다.

요청은 Traefik에서 Ingress 규칙을 거쳐 Service의 `http` 포트로 전달되고, Service는 Pod의 `http` 컨테이너 포트에 연결합니다. Ingress 경로 선언 자체는 URL 경로를 다시 쓰지 않습니다.
