# Farm Market GitOps

[Farm Market API](https://github.com/ym1085/farm-market-platform)와 Traefik의 Kubernetes 배포 설정입니다. API 소스와 이미지 빌드는 API 저장소에서 관리합니다.

## 설정 위치

| 변경할 내용 | 파일 |
| --- | --- |
| API 공통 설정 | `charts/farm-market-api/values.yaml` |
| 환경별 이미지 태그, 포트, 도메인 | `charts/farm-market-api/values-{env}.yaml` |
| Deployment, Service, Ingress 구조 | `charts/farm-market-api/templates/` |
| 배포할 Git 브랜치, values 파일, namespace | `argocd/applications/{env}/apps/farm-market-api.yaml` |
| Traefik 버전, NodePort | `argocd/applications/{env}/infra/traefik.yaml` |
| 배포 가능한 저장소, namespace, 리소스 종류 | `argocd/projects/{env}/` |
| Argo CD 설치, namespace 생성, 최초 등록 | `argocd/bootstrap/` |

`{env}`는 `dev`, `stg`, `prod`입니다. `values.yaml`을 기본으로 읽고, `values-{env}.yaml`의 같은 항목으로 덮어씁니다.

`env`는 `name`/`value` 리스트입니다. 환경 파일에서 지정하면 공통 `env` 전체를 대체하므로 필요한 항목을 모두 적습니다. 값은 `"false"`, `"0"`처럼 문자열로 작성합니다.

## 환경

| 환경 | Git 브랜치 | Spring 프로필 | API 포트 | 서비스 배포 |
| --- | --- | --- | --- | --- |
| dev | `dev` | `dev` | 8081 | 자동 |
| stg | `stg` | `dev` | 8081 | 자동 |
| prod | `master` | `prod` | 8082 | 수동 |

API namespace는 `farm-market-{env}`, Helm release와 Service 이름은 `farm-market-api`입니다. stg는 전용 Spring 프로필이 없어 `dev`를 사용합니다.

## 로컬 검증

필요한 도구: Helm 4.1.1, Python 3, PyYAML 6.0.1. 외부 차트 다운로드에는 네트워크가 필요합니다.

```bash
python3 scripts/gitops/validate.py --fixtures --external-charts
python3 -m unittest discover -s tests -v
```

`--fixtures`는 비어 있는 이미지 주소, 태그를 테스트 값으로 채웁니다. 실제 값을 입력한 뒤에는 이 옵션을 빼고 검증합니다. 두 명령 모두 클러스터에 배포하지 않으며, API 실행 여부도 검사하지 않습니다.

## 최초 등록

- **이미지:** 공통 `image.repository`와 환경별 `image.tag` 입력. 현재는 비어 있습니다. 이미지는 non-root 사용자로 실행해야 하며, 차트에서 쓰기용으로 마운트한 경로는 `/tmp`입니다.
- **DB, Redis, JWT 설정:** 공급 방법 결정. 현재 차트는 런타임 Secret을 주입하지 않습니다. 필요한 변수는 [환경변수 예시](examples/farm-market-api.env.example)를 참고하고, 비밀값은 Git에 넣지 않습니다.
- **Git 브랜치:** 위 표의 브랜치에 설정 반영. `stg` 브랜치는 2026-10-15 확인 시 없었습니다.

아래는 dev 등록 예시입니다. **현재 kubectl context에 적용되며, dev/stg는 등록 후 자동 배포됩니다.**

```bash
# Argo CD가 없는 클러스터에서만 실행
bash scripts/gitops/argocd/bootstrap-argocd.sh

bash scripts/gitops/argocd/setup-appprojects.sh dev
bash scripts/gitops/argocd/setup-applications.sh dev
```

Application과 AppProject의 추가 및 수정은 Git에서 자동 반영됩니다. 삭제는 root Application에서 수동 prune합니다. 기존 ingress-nginx가 실행 중이면 Traefik과 NodePort가 겹치므로 별도 전환 작업이 필요합니다.

prod Argo CD 접속: `kubectl -n argocd port-forward svc/argocd-server 8443:443 --address 127.0.0.1` 실행 후 `https://localhost:8443`으로 접속합니다.
