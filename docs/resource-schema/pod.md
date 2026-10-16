# Pod

[문서 목록](README.md)

## 01. Pod

Deployment의 `spec.template` 부분입니다. 별도 Pod 파일은 없으며, 표의 필드 경로도 `spec.template` 내부를 기준으로 읽으면 됩니다.

소스: [charts/farm-market-api/templates/deployment.yaml](../../charts/farm-market-api/templates/deployment.yaml)

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

| 필드 | 설명 |
| --- | --- |
| `metadata.labels` | Pod를 식별하고 Service가 대상 Pod를 선택할 때 사용하는 레이블 |
| `spec.automountServiceAccountToken` | `false`이면 서비스 계정 토큰을 Pod에 자동 마운트하지 않음 |
| `spec.terminationGracePeriodSeconds` | Pod 종료 유예 시간<br>values의 `terminationGracePeriodSeconds` 사용<br>prod는 애플리케이션 종료 시간인 60초보다 길게 설정 |
| `spec.securityContext.runAsNonRoot` | root 실행 금지<br>이미지에 root가 아닌 실행 사용자 필요 |
| `spec.securityContext.seccompProfile.type` | `RuntimeDefault`: 런타임의 기본 seccomp 필터로 시스템 호출 제한 |
| `spec.imagePullSecrets[].name` | 비공개 이미지 저장소 인증용 Secret 이름<br>`imagePullSecrets`가 있을 때만 생성하며 같은 namespace에 Secret이 필요 |

### 컨테이너

| 필드 | 설명 |
| --- | --- |
| `spec.containers[]` | Pod 안에서 실행할 컨테이너 목록<br>이 차트에서는 API 컨테이너 하나를 실행 |
| `spec.containers[].name` | Pod 내부에서 컨테이너를 구분하는 이름 |
| `spec.containers[].image` | `image.repository`와 `image.tag`를 합친 이미지 주소<br>둘 중 하나라도 비어 있으면 차트 검증 실패 |
| `spec.containers[].imagePullPolicy` | `IfNotPresent`: 로컬에 없으면 다운로드<br>`Always`: 실행할 때 레지스트리에서 이미지 확인<br>`Never`: 로컬 이미지만 사용 |
| `spec.containers[].securityContext.allowPrivilegeEscalation` | `false`: 상위 프로세스보다 높은 권한을 얻지 못하도록 제한 |
| `spec.containers[].securityContext.readOnlyRootFilesystem` | 컨테이너의 루트 파일시스템을 읽기 전용으로 사용<br>쓰기 경로는 별도 볼륨이 필요 |
| `spec.containers[].securityContext.capabilities.drop` | `ALL`은 컨테이너의 Linux capability를 모두 제거 |
| `spec.containers[].ports[].name` | 컨테이너 포트의 이름<br>Service와 probe가 `http`라는 이름으로 참조 |
| `spec.containers[].ports[].containerPort` | `containerPort`에서 읽는 애플리케이션 포트<br>이 선언 자체가 프로세스를 실행하거나 외부에 포트를 공개하지 않음 |
| `spec.containers[].env[].name` | 환경변수 이름<br>`SPRING_PROFILES_ACTIVE`와 `SERVER_PORT`는 템플릿이 생성하고 추가 변수는 `env` 목록에서 읽음 |
| `spec.containers[].env[].value` | 환경변수의 문자열 값<br>Spring 프로필은 `springProfile`, 서버 포트는 `containerPort`에서 생성 |
| `spec.containers[].resources.requests` | 스케줄링에 사용할 CPU와 메모리 요청량 |
| `spec.containers[].resources.limits` | CPU와 메모리 사용 상한<br>CPU는 제한되고 메모리 상한 초과 시 컨테이너가 OOM 종료될 수 있음 |
| `spec.containers[].startupProbe` | 시작 완료를 검사<br>성공하기 전에는 readiness와 liveness 검사를 시작하지 않으며, 반복 실패하면 컨테이너를 재시작 |
| `spec.containers[].readinessProbe` | 트래픽을 받을 준비가 되었는지 검사<br>실패한 Pod는 Service의 정상 트래픽 대상에서 제외 |
| `spec.containers[].livenessProbe` | 실행 중인 컨테이너의 상태를 검사<br>실패가 임계값에 도달하면 컨테이너를 재시작 |
| `spec.containers[].volumeMounts[].name` | 마운트할 `spec.volumes[].name`을 참조 |
| `spec.containers[].volumeMounts[].mountPath` | 컨테이너 안에서 볼륨을 사용할 경로 |

### 볼륨

| 필드 | 설명 |
| --- | --- |
| `spec.volumes[].name` | Pod 내부에서 볼륨을 구분하는 이름 |
| `spec.volumes[].emptyDir` | Pod 수명에 연결된 임시 볼륨<br>컨테이너 재시작에는 유지되지만 Pod가 제거되면 데이터도 삭제됨 |

`env`를 환경 values에서 지정하면 공통 목록 전체를 대체합니다. 빈 문자열, `"false"`, `"0"`도 문자열 그대로 전달합니다. 비밀값을 values에 기록하지 않으며 현재 차트에는 런타임 Secret 주입이 없습니다.

쓰기용 볼륨은 `/tmp`에만 연결되어 있습니다. 환경변수의 `/data/uploads/` 경로에는 쓰기 가능한 볼륨이 연결되어 있지 않습니다.

### 상태 검사

Probe 내부 옵션은 [공통 values](../../charts/farm-market-api/values.yaml)에서 설정합니다.

| 옵션 | 설명 |
| --- | --- |
| `tcpSocket.port` | TCP 연결을 검사할 포트<br>컨테이너 포트 이름 `http`를 참조 |
| `periodSeconds` | 검사 주기, 초 단위 |
| `timeoutSeconds` | 한 번의 검사 응답을 기다리는 제한 시간 |
| `failureThreshold` | 실패로 판정할 연속 실패 횟수 |
| `initialDelaySeconds` | 컨테이너 시작 후 첫 검사까지 기다리는 시간<br>현재 values에는 없지만 차트 스키마에서 허용 |

현재 probe는 TCP 연결만 검사하므로 DB 연결이나 API 응답의 정상 여부까지 보장하지 않습니다.
