# AGENTS.md

## CRITICAL: 작성 규칙

- CRITICAL: 답변, 문서, 커밋 메시지에 가운뎃점(U+00B7)이나 장식용 구분 기호를 사용하지 않는다. 쉼표, 문장 또는 일반 Markdown 목록으로 구분한다.
- CRITICAL: 커밋 메시지에 `Co-authored-by`, `Co-developed-by`, `Generated with` 같은 공동 작성자 표기나 AI 도구 서명을 추가하지 않는다. 변경 내용만 작성한다.

## 프로젝트 성격

이 저장소는 `farm-market-api`와 외부 Helm 차트 `traefik`를 dev/stg/prod에 배포하는 GitOps 저장소다. API 소스는 `https://github.com/ym1085/farm-market-platform`에 있다. 배포 단위는 api-server 하나이며 core는 라이브러리다.

## 수정 위치와 배포 기준

- CRITICAL: 먼저 `argocd/applications/{env}`에서 repoURL, targetRevision, path/chart, valueFiles, destination, project를 확인한다.
- 서비스 스펙은 `charts/farm-market-api`, 환경 차이는 `values-{env}.yaml`, 공통값은 `values.yaml`에서 관리한다.
- Application과 Project는 각각 `argocd/applications/{env}/farm-market`, `argocd/projects/{env}/farm-market`에 모은다. API와 Traefik의 권한은 별도 Project로 관리하며, 새 namespace, 저장소, 리소스 kind가 필요하면 해당 Project도 수정한다.
- Application과 AppProject는 파일당 하나씩 선언하고 `metadata.namespace: argocd`를 명시한다. 검증기는 `.yaml`, `.yml`, `.json`을 재귀적으로 읽는다.
- `argocd/bootstrap/common`과 `argocd/bootstrap/{env}/install/argo-cd-install-values.yaml`은 Argo CD 설치 설정이다.
- `argocd/bootstrap/{env}/namespaces/`의 서비스별 `.yaml`, `.yml`, `.json` 파일은 관리자가 먼저 생성하는 namespace 목록이다. `farm-market.yaml`은 API와 Traefik의 독립된 namespace를 함께 선언한다. workload Project에 Namespace 권한을 주거나 CreateNamespace에 의존하지 않는다.
- Argo CD TLS는 모든 환경에서 켠다. prod 관리 Service는 ClusterIP이며 운영자는 Kubernetes 권한으로 로컬 port-forward한다.
- `argocd/bootstrap/{env}/roots/`의 `root-applications-permissions.yaml`, `projects-root.yaml`, `applications-root.yaml`은 환경 공통 관리자용 최초 연결 선언이다. root는 각각 projects/applications 하위만 재귀적으로 동기화한다.
- root 선언과 AppProject를 바꿀 수 있는 권한은 관리자 권한이다. 서비스 Project에 argocd namespace나 불필요한 cluster 권한을 허용하지 않는다.
- Traefik은 외부 Helm repo의 고정 버전을 사용한다. 표준 Ingress provider만 켜고 CRD 설치를 건너뛴다.

## 환경 계약

| 환경 | targetRevision | API Spring profile | API port | namespace / Project | 서비스 sync |
| --- | --- | --- | --- | --- | --- |
| dev | dev | dev | 8081 | farm-market-dev | prune/selfHeal 자동 |
| stg | stg | dev | 8081 | farm-market-stg | prune/selfHeal 자동 |
| prod | master | prod | 8082 | farm-market-prod | 수동 |

- Application 이름은 `farm-market-api-{env}`, Helm release와 Service 이름은 `farm-market-api`다.
- Traefik 전용 Project 파일은 `traefik.yaml`이며 기존 리소스 이름 `infra-{env}`를 유지한다. namespace는 `traefik-{env}`, ingress class는 `traefik-{env}`다.
- root Project는 `gitops-{env}`이며 argocd namespace의 Application과 AppProject만 관리한다. root는 생성과 수정을 자동 반영하지만 자동 prune은 하지 않는다.
- 로컬 origin과 GitOps 선언의 `repoURL`, `sourceRepos`는 `https://github.com/ym1085/kubernetes-gitops.git`로 통일한다. 로컬 수정만으로 원격 동기화가 바뀐다고 가정하지 않는다.
- 원격 stg ref는 2026-10-16 확인 시 없었다. 실제 배포 전 존재 여부와 대상 내용을 확인한다.
- API에는 stg 프로필이 없어 dev 프로필과 별도 namespace를 사용한다. 전용 프로필이 추가되면 values와 테스트를 함께 수정한다.

## 코드와 값의 계약

- 단일 API 컨테이너의 image, resources, env를 독립된 값으로 관리한다. Kubernetes containers 배열 전체를 values에 복제하지 않는다.
- SERVER_PORT는 containerPort에서 생성한다. Service targetPort와 Ingress backend는 이름 `http`로 연결한다.
- 현재 API 런타임 Secret 주입은 사용하지 않는다. 비밀값을 Git의 values에 넣지 않으며, 실제 배포 전 DB, Redis, JWT 필수 설정의 공급 방법을 준비한다. 입력 키는 examples의 env 양식을 확인한다.
- `farm-market.image.base-url`의 환경변수 이름은 `FARMMARKET_IMAGE_BASEURL`이다. 하이픈을 밑줄로 바꾸지 않는다.
- env는 name/value 리스트이며 환경별로 지정하면 공통 목록 전체를 대체한다. 문자열의 빈 값, `false`, `0`도 보존하고, env 렌더링을 resources 조건에 묶지 않는다.
- 이미지 repository/tag가 없으면 렌더링이 실패하는 것이 의도한 동작이다. 가짜 배포 이미지를 실제 values에 넣지 않는다.
- 이미지 버전은 환경 values에 명시하고 검증된 같은 태그를 승격한다. 기존 데모용 Image Updater 선언과 산출물은 제거했다.
- prod graceful shutdown은 60초이므로 Kubernetes 종료 유예 시간은 이를 초과해야 한다.

## 작업과 검증

1. 해당 환경의 Application과 Project를 먼저 읽는다.
2. 변경되는 values, 템플릿, 스크립트, 문서, 테스트 참조를 함께 확인한다.
3. `python3 scripts/gitops/validate.py --fixtures --external-charts`와 `python3 -m unittest discover -s tests -v`를 실행한다. Helm과 PyYAML, 외부 차트를 다운로드할 네트워크가 필요하다.
4. 실제 이미지가 준비되면 fixtures 없이 검증한다. fixture 검증은 이미지 존재, Secret, DB, 실제 클러스터 정상 동작을 보장하지 않는다.
5. namespace, release/Service 이름, ingress backend, targetRevision, NodePort 체계는 명시적 요청 없이 바꾸지 않는다. 클러스터 적용이나 push는 로컬 파일 수정과 구분한다.
