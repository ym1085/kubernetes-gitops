# Farm Market GitOps 운영 가이드

## 배포 경로

```text
bootstrap/{env}/root-project.yaml          관리자용 gitops-{env} Project
bootstrap/{env}/projects-root.yaml         projects/{env}/ 감시
bootstrap/{env}/applications-root.yaml     applications/{env}/ 감시
                                                    |
                              apps/farm-market-api.yaml
                                                    |
                        charts/farm-market-api + values-{env}.yaml
```

두 등록 스크립트는 `bootstrap/{env}/namespaces.yaml`을 먼저 적용하고, 실패하면 root를 등록하지 않는다. `setup-appprojects.sh`는 이어서 관리자 Project와 projects root를 등록하고, `setup-applications.sh`는 applications root를 등록한다. namespace 생성은 관리자 bootstrap의 책임이며 서비스 Project에는 Namespace 권한을 주지 않는다. 새 namespace가 필요하면 이 파일을 갱신해 root 동기화 전에 적용한다. projects와 applications root가 별도로 동기화되므로 최초에는 자식 Project 생성 전 일시적으로 오류가 보일 수 있으며 Project 생성 뒤 재조정된다.

root는 모든 환경에서 선언의 생성·수정을 자동 반영한다. prod 자식 Application에는 자동 sync가 없어 실제 서비스 반영은 운영자가 실행한다. root 자동 prune은 꺼져 있으며 삭제는 root에서 수동 prune한다. root에 삭제 전파 finalizer를 두지 않았다. root 자체를 삭제해도 자식 서비스가 자동 삭제되지 않는다.

root Project는 argocd namespace의 Application·AppProject를 관리하므로 관리자 권한이다. bootstrap, applications, projects 변경 권한을 보호하고 저장소의 branch protection과 리뷰 정책을 별도로 설정한다. 폴더 분리만으로 Git 쓰기 권한이 격리되지는 않는다. [Argo CD 공식 안내](https://argo-cd.readthedocs.io/en/stable/operator-manual/cluster-bootstrapping/)

## 최초 배포 입력

1. API 저장소에서 Java 17 기반의 api-server 실행 이미지를 빌드·게시한다. 이미지의 실행 사용자는 non-root여야 한다. 이 차트는 루트 파일시스템을 읽기 전용으로 두고 `/tmp`만 쓰기 가능하게 마운트한다.
2. `charts/farm-market-api/values.yaml`의 `image.repository`와 각 `values-{env}.yaml`의 `image.tag`를 실제 값으로 채운다. `latest`, `dev`, `stg`, `prod` 같은 이동 태그는 허용하지 않는다. 레지스트리에서도 릴리스 태그 재사용을 금지한다.
3. 해당 namespace에 DB·Redis·JWT·이미지 URL을 담은 Secret을 만든다. MySQL/Redis 자체의 설치·백업은 이 API 차트에서 관리하지 않는다.
4. Secret과 실제 이미지가 준비되면 fixtures 없이 검증하고, 변경을 해당 Application이 참조하는 브랜치에 반영한다. 현재 작업 브랜치는 Application의 동기화 대상이 아니다.
5. 아래 root 등록 명령을 실행한다. 기존 Argo CD가 있으면 bootstrap 설치를 반복하지 않는다.

```bash
kubectl config current-context
kubectl apply -f argocd/bootstrap/dev/namespaces.yaml
cp examples/farm-market-api.env.example farm-market-dev.env
# 로컬 env 파일에 실제 값을 입력한다. *.env 파일은 Git에서 제외된다.
kubectl -n farm-market-dev create secret generic farm-market-api-runtime \
  --from-env-file=farm-market-dev.env

python3 scripts/gitops/validate.py
bash scripts/gitops/argocd/setup-appprojects.sh dev
bash scripts/gitops/argocd/setup-applications.sh dev
```

각 환경에는 별도 Secret과 DB·Redis 설정을 사용한다. `farm-market-dev.env` 파일을 다른 환경에 그대로 재사용하지 않는다. 사설 레지스트리는 같은 namespace에 pull Secret을 만들고 `imagePullSecrets`에 이름을 지정한다. 이 저장소는 특정 Secret 관리 제품을 설치하지 않는다. 외부 Secret 관리 도구가 있다면 동일한 이름/키의 Kubernetes Secret을 공급하면 된다.

## Argo CD 관리자 접속

모든 환경에서 `server.insecure: false`로 TLS를 켠다. prod 관리 Service는 ClusterIP여서 기존 32180/32543 NodePort를 외부에 열지 않는다. dev/stg의 NodePort 번호와 API/Traefik NodePort는 유지한다. prod의 기존 NodePort 번호는 참조용으로 보관하며 ClusterIP 렌더링에는 포함되지 않는다.

Kubernetes 권한이 있는 운영자는 `kubectl -n argocd port-forward svc/argocd-server 8443:443 --address 127.0.0.1`을 실행한 뒤 `https://localhost:8443`으로 접속한다. 초기에는 Argo CD 자체 서명 인증서가 사용된다. 상시 운영 접속에는 `argocd-server-tls` Secret에 신뢰할 수 있는 인증서를 공급하고, 인증서 이름에 맞는 호스트로 접속한다. [Argo CD TLS 설정](https://argo-cd.readthedocs.io/en/stable/operator-manual/tls/)

이미 설치된 Argo CD에는 bootstrap values의 로컬 수정이 자동 반영되지 않는다. 별도의 관리 창에서 같은 Helm release를 갱신해야 하며, prod NodePort 접속은 그때 종료된다. 먼저 port-forward 접속 권한을 확인한다. 이 문서의 명령은 운영자가 적용할 때를 위한 것이며 저장소 수정 과정에서는 실행하지 않는다.

필수 Secret 키:

| 키 | 용도 |
| --- | --- |
| SPRING_DATASOURCE_URL | 환경별 MySQL JDBC URL |
| SPRING_DATASOURCE_USERNAME | DB 사용자 |
| SPRING_DATASOURCE_PASSWORD | DB 비밀번호 |
| JWT_SECRET | Base64로 인코딩한 최소 32바이트 랜덤 키 |
| REDIS_HOST | 환경별 Redis 주소 |
| REDIS_PASSWORD | Redis 인증 값 |
| FARMMARKET_IMAGE_BASEURL | 상품 이미지의 외부 접근 URL |

Secret 키가 없으면 컨테이너 설정 단계에서 실패한다. 키가 있어도 빈 값이나 잘못된 접속 정보는 애플리케이션 시작 실패로 이어질 수 있다. Secret 수정 후에는 Pod 재시작이 필요하다. Redis 포트가 6379가 아니면 환경 values의 `env.REDIS_PORT`에 문자열로 지정한다.

`FARMMARKET_IMAGE_BASEURL`은 prod에서 누락된 `farm-market.image.base-url`을 공급한다. storage-location은 공통 env에서 공급한다. Spring 환경변수는 점을 밑줄로 바꾸고 하이픈을 제거한다. [Spring Boot 공식 규칙](https://docs.spring.io/spring-boot/3.4/reference/features/external-config.html#features.external-config.typesafe-configuration-properties.relaxed-binding.environment-variables)

## 환경과 라우팅

| 환경 | revision | profile | containerPort | class | NodePort HTTP / HTTPS |
| --- | --- | --- | --- | --- | --- |
| dev | dev | dev | 8081 | traefik-dev | 30080 / 30443 |
| stg | stg | dev | 8081 | traefik-stg | 31080 / 31443 |
| prod | master | prod | 8082 | traefik-prod | 32080 / 32443 |

`stg` 원격 브랜치는 검토일(2026-10-14)에 존재하지 않았다. stg를 연결하려면 먼저 해당 ref에 이 구성을 반영해야 한다. targetRevision은 자동으로 다른 브랜치로 대체하지 않는다.

Ingress의 `/api/v1` 경로로 auth·members·products·orders API를 같은 서버에 연결한다. URL rewrite는 사용하지 않는다. frontend 배포는 포함하지 않는다. host와 TLS는 미설정이므로 실제 도메인·인증서를 환경 values에 입력해야 한다.

dev/stg의 `/images`는 API의 파일 리소스 핸들러로 전달한다. 현재 차트는 `/data/uploads`를 위한 PVC나 상품 이미지 파일을 공급하지 않는다. 이 경로를 쓸 때는 이미지 배포/저장소 연결을 추가해야 한다. prod API에는 이미지 파일 핸들러가 없으므로 외부 이미지 서버/CDN을 `FARMMARKET_IMAGE_BASEURL`로 지정한다.

API에는 Actuator/health endpoint가 없다. 현재 startup/readiness/liveness는 TCP 검사이며 DB·Redis 준비 상태나 요청 처리 성공을 보장하지 않는다. API에 전용 헬스체크가 생기면 HTTP 검사로 전환한다. dev/stg 종료 유예는 45초, prod는 75초로 API의 graceful shutdown 설정보다 길다.

## 이미지 승격과 롤백

개발에서 검증한 이미지 태그를 stg/prod의 `image.tag`에 기록한다. 운영은 PR 검토 후 prod Application을 수동 sync한다. 롤백은 이전에 검증한 태그로 values를 되돌리고 다시 sync한다. DB 스키마 변경은 이미지 롤백만으로 되돌아가지 않는다.

기존 Image Updater 설치 설정과 데모 write-back 파일을 제거했다. 새 API는 명시한 이미지 태그를 Git에서 관리하며 레지스트리의 최신 태그를 자동 선택하지 않는다. 추후 자동화할 때는 환경 values를 수정하는 PR을 생성하도록 연결한다.

## 기존 데모 정리

사용하지 않는 order-service/user-service 차트, 환경별 Application·AppProject, Image Updater 산출물을 저장소에서 제거했다. 이 변경은 기존 클러스터 리소스를 삭제하는 명령을 실행하지 않는다. 예전에 등록한 Application이나 Image Updater Helm release가 클러스터에 남아 있다면 실제 사용 여부를 확인하고 별도로 제거한다. 삭제한 기존 데모 리소스는 새 root의 관리 대상에 포함되지 않는다.

## ingress-nginx에서 Traefik으로 전환

[ingress-nginx 유지보수 종료](https://kubernetes.io/blog/2026/01/29/ingress-nginx-statement/)에 따라 [Traefik 공식 차트](https://github.com/traefik/traefik-helm-chart/releases/tag/v41.7.1) 41.7.1 / Proxy v3.7.14로 교체했다. 표준 Kubernetes Ingress만 사용하고 CRD·Gateway provider는 비활성화한다. API 경로와 NodePort는 위 표대로 유지한다. Application·namespace·IngressClass는 `traefik-{env}`로 새로 생성한다. 기존 IngressClass의 controller 필드를 변경하지 않는다.

infra AppProject는 IngressClass·ClusterRole·ClusterRoleBinding과 Deployment·Service·ServiceAccount만 허용한다. Traefik은 환경의 `farm-market-{env}` namespace와 ingress class만 감시한다. 이 감시 설정이 Kubernetes RBAC 격리를 뜻하지는 않는다. 공식 차트의 ClusterRole에는 클러스터 전체 Secret 읽기 등이 포함되므로 컨트롤러와 infra Project 변경 권한은 관리자에게만 부여한다.

신규 클러스터는 최초 연결 절차를 따른다. 기존 ingress-nginx가 실행 중이면 같은 NodePort를 두 Service가 동시에 사용할 수 없으므로 다음 순서로 점검 시간에 전환한다. 이 절차는 짧은 서비스 중단을 전제로 한다.

1. 대상 환경의 기존 Application 선언과 실제 컨트롤러 리소스를 백업한다. 기존 컨트롤러가 처리하는 다른 Ingress와 nginx 전용 annotation이 있는지 확인한다. 이 저장소 밖의 Ingress는 자동 변환되지 않는다.
2. 기존 root가 있다면 applications root와 projects root의 자동 sync를 중지한 뒤 기존 `ingress-nginx-{env}` Application의 자동 sync도 중지한다. root가 자동 sync를 다시 켜지 않도록 주의한다. 새 Git 구성을 반영하기 전에 수행한다.
3. **기존 infra Project 권한이 남아 있는 동안** 기존 controller Application을 리소스까지 연쇄 삭제한다. 기존 Application에 삭제 finalizer가 없을 수 있으므로 단순 `kubectl delete application`만으로 정리되었다고 판단하지 않는다. Helm으로 설치했다면 해당 Helm release를 제거한다. 백업한 리소스 목록을 기준으로 잔여 Service·IngressClass·RBAC를 확인하고 위 NodePort가 해제되었는지 확인한다.
4. 새 구성을 대상 브랜치에 반영하고 `bootstrap/{env}/namespaces.yaml`을 먼저 적용한다. projects root를 sync해 새 infra Project를 반영한 뒤 applications root를 sync하고 두 root의 자동 sync를 선언대로 복구한다. prod는 `traefik-prod`와 `farm-market-api-prod`를 수동 sync한다. dev/stg는 자식 Application이 자동 sync한다.
5. 컨트롤러 Pod Ready, Service NodePort, API IngressClass와 `/api/v1` 요청을 확인한다. TLS를 설정했다면 HTTPS도 확인한다. 기존 namespace가 비어 있는지 확인한 뒤 필요할 때만 정리한다.

롤백할 때는 새 컨트롤러의 자동 재생성을 먼저 중지하고 리소스를 제거해 NodePort를 해제한다. 백업한 기존 Project·Application·Ingress class 설정을 함께 복원한다. 유지보수가 종료된 컨트롤러 복원은 장애 복구용 임시 조치다. 저장소 수정 과정에서 위 클러스터 작업은 실행하지 않았다.

## 검증 범위와 운영 전 남은 작업

- CI는 Application 12개의 Project/source/destination 계약, 로컬 API 차트 3개 환경의 lint/render와 외부 Traefik 차트 3개 환경의 render, Secret 참조·포트·Ingress 연결, 잘못된 입력 거부와 bootstrap 스크립트를 검사한다. 미게시 이미지는 `--fixtures`에서만 테스트 이미지로 대체한다. 실제 이미지를 pull하거나 클러스터에 적용하지 않는다.
- API에 DB 마이그레이션 도구가 없으며 dev는 schema validate, prod는 ddl-auto none이다. 기존 스키마 또는 별도 마이그레이션 절차가 필요하다.
- API 소스 검토에서 주문 목록/상세 조회의 소유자 검증이 확인되지 않았다. 인터넷 공개 전에 API 저장소에서 인증된 회원 기준으로 조회를 제한해야 한다.

API 계약은 [267200d 커밋](https://github.com/ym1085/farm-market-platform/tree/267200d1d0446201e19bed30c5eacb57ce6eaff9)의 api-server 설정과 컨트롤러를 기준으로 확인했다. 실제 이미지 빌드·DB 접속·부하 테스트·GitHub 보호 규칙은 이 변경에서 검증하지 않았다.
