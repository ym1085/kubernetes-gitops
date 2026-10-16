# 리소스 스키마

리소스별 YAML 소스와 필드 설명

| 문서 | 내용 |
| --- | --- |
| [Application](application.md) | API와 Traefik의 배포 소스, 대상, 동기화 옵션 |
| [AppProject](appproject.md) | 허용 저장소, 배포 대상, 리소스 권한 |
| [Deployment](deployment.md) | Pod 복제본 수와 배포 설정 |
| [Pod](pod.md) | 컨테이너, 환경변수, 보안, 볼륨, 상태 검사 |
| [Service](service.md) | Pod 선택과 포트 연결 |
| [Ingress](ingress.md) | 호스트와 경로별 라우팅, TLS |

## Helm 템플릿 읽기

| 표기 | 의미 |
| --- | --- |
| `{{ ... }}` | Helm이 렌더링할 때 처리하는 표현식 |
| `.Values` | 공통 `values.yaml`에 환경별 `values-{env}.yaml`을 덮어쓴 값 |
| `.Release.Name` | Helm 릴리스 이름 |
| `.Release.Namespace` | 배포할 namespace |
| `[]` | 목록의 각 항목 |

Helm 템플릿은 렌더링한 뒤 적용해야 합니다. 원문을 `kubectl apply`로 직접 적용할 수는 없습니다.
