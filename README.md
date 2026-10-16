# Farm Market GitOps

[Farm Market API](https://github.com/ym1085/farm-market-platform)와 Traefik의 Kubernetes 배포 설정입니다. API 소스와 이미지 빌드는 API 저장소에서 관리합니다.

리소스별 YAML과 필드 설명은 [리소스 스키마](docs/resource-schema/README.md)를 참고하세요.

## 폴더 구조

`{env}`는 실제로 존재하는 `dev`, `stg`, `prod` 세 폴더를 묶어 표시한 것입니다.

```text
.
├── argocd/
│   ├── bootstrap/
│   │   ├── common/argo-cd-install-values.yaml
│   │   └── {env}/
│   │       ├── install/argo-cd-install-values.yaml
│   │       ├── roots/
│   │       │   ├── root-applications-permissions.yaml
│   │       │   ├── projects-root.yaml
│   │       │   └── applications-root.yaml
│   │       └── namespaces/farm-market.yaml
│   ├── projects/{env}/farm-market/
│   │   ├── farm-market.yaml
│   │   └── traefik.yaml
│   └── applications/{env}/farm-market/
│       ├── farm-market-api.yaml
│       └── traefik.yaml
├── charts/farm-market-api/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values-{dev,stg,prod}.yaml
│   ├── values.schema.json
│   └── templates/
│       ├── _helpers.tpl
│       ├── deployment.yaml
│       ├── service.yaml
│       └── ingress.yaml
├── scripts/
│   ├── gitops/
│   │   ├── validate.py
│   │   └── argocd/
│   │       ├── install-argocd.sh
│   │       ├── register-projects-root.sh
│   │       └── register-applications-root.sh
│   ├── k8s/kind-cluster/
│   │   ├── create-cluster.sh
│   │   ├── delete-cluster.sh
│   │   └── nodeport-config.yaml
│   └── aws/eks/
│       ├── associate-iam-oidc-provider.sh
│       └── aws-load-balancer-controller/
│           ├── create-iam-policy.sh
│           ├── create-iam-service-account.sh
│           └── deploy-controller.sh
├── docs/resource-schema/
│   ├── README.md
│   ├── application.md
│   ├── appproject.md
│   ├── deployment.md
│   ├── pod.md
│   ├── service.md
│   └── ingress.md
├── examples/farm-market-api.env.example
├── tests/
│   ├── test_gitops.py
│   └── test_scripts.py
├── .github/
│   ├── workflows/validate.yaml
│   └── ISSUE_TEMPLATE/issue-feature-template.yaml
├── .gitattributes
├── .gitignore
├── AGENTS.md
├── CLAUDE.md
└── README.md
```

## Argo CD 연결 구조

`Application`은 무엇을 어디에 배포할지, `AppProject`는 그 Application이 사용할 수 있는 저장소·배포 대상·리소스 종류를 정합니다. 모든 Application·AppProject 자체는 `argocd` namespace에 있습니다. 아래 파일 경로는 `argocd/` 기준입니다.

| 파일 | 리소스 이름 | 역할 |
| --- | --- | --- |
| `bootstrap/{env}/roots/root-applications-permissions.yaml` | AppProject `gitops-{env}` | 아래 두 root Application의 공통 권한 |
| `bootstrap/{env}/roots/projects-root.yaml` | Application `projects-{env}` | Git의 `argocd/projects/{env}/`를 재귀적으로 읽어 AppProject 등록 |
| `bootstrap/{env}/roots/applications-root.yaml` | Application `applications-{env}` | Git의 `argocd/applications/{env}/`를 재귀적으로 읽어 서비스 Application 등록 |
| `projects/{env}/farm-market/farm-market.yaml` | AppProject `farm-market-{env}` | API 배포 권한 |
| `projects/{env}/farm-market/traefik.yaml` | AppProject `infra-{env}` | Farm Market 전용 Traefik 배포 권한 |
| `applications/{env}/farm-market/farm-market-api.yaml` | Application `farm-market-api-{env}` | 로컬 Helm 차트 `charts/farm-market-api` 배포 |
| `applications/{env}/farm-market/traefik.yaml` | Application `traefik-{env}` | 외부 Helm 차트 `traefik` 41.7.1 배포 |

연결은 파일명이 아닌 `Application.spec.project` → `AppProject.metadata.name`입니다. 두 root는 `gitops-{env}`, API는 `farm-market-{env}`, Traefik은 `infra-{env}`를 참조합니다. 서비스 Application은 root를 참조하지 않습니다.

`bootstrap/{env}/namespaces/farm-market.yaml`은 `farm-market-{env}`와 `traefik-{env}`를 만듭니다. 이 파일과 root 선언은 관리자가 적용합니다. root의 자동 동기화 범위에는 `bootstrap/`이 포함되지 않습니다.

현재 `infra-{env}`는 Traefik 전용 Project의 기존 리소스 이름입니다. 다른 인프라에 다른 권한이 필요하면 별도 Project를 추가합니다.

## 설정 위치

| 변경할 내용 | 파일 |
| --- | --- |
| API 공통 설정 | `charts/farm-market-api/values.yaml` |
| 환경별 이미지 태그, 포트, 도메인 | `charts/farm-market-api/values-{env}.yaml` |
| Deployment, Service, Ingress 구조 | `charts/farm-market-api/templates/` |
| 배포할 Git 브랜치, values 파일, namespace | `argocd/applications/{env}/farm-market/farm-market-api.yaml` |
| Traefik 버전, NodePort | `argocd/applications/{env}/farm-market/traefik.yaml` |
| 배포 가능한 저장소, namespace, 리소스 종류 | `argocd/projects/{env}/farm-market/` |
| Argo CD 설치 설정 | `argocd/bootstrap/common/`, `argocd/bootstrap/{env}/install/` |
| 서비스별 namespace 생성 | `argocd/bootstrap/{env}/namespaces/farm-market.yaml` |
| Project·Application 최초 등록 | `argocd/bootstrap/{env}/roots/` |

`values.yaml`을 기본으로 읽고, `values-{env}.yaml`의 같은 항목으로 덮어씁니다.

`env`는 `name`/`value` 리스트입니다. 환경 파일에서 지정하면 공통 `env` 전체를 대체하므로 필요한 항목을 모두 적습니다. 값은 `"false"`, `"0"`처럼 문자열로 작성합니다.

## 환경

| 환경 | Git 브랜치 | Spring 프로필 | API 포트 | 서비스 배포 |
| --- | --- | --- | --- | --- |
| dev | `dev` | `dev` | 8081 | 자동 |
| stg | `stg` | `dev` | 8081 | 자동 |
| prod | `master` | `prod` | 8082 | 수동 |

API namespace는 `farm-market-{env}`, Helm release와 Service 이름은 `farm-market-api`입니다. Traefik namespace·Helm release·IngressClass는 `traefik-{env}`입니다. stg는 전용 Spring 프로필이 없어 `dev`를 사용합니다.

모든 배포 대상은 Argo CD가 설치된 클러스터(`https://kubernetes.default.svc`)입니다. dev/stg 서비스는 자동 prune·selfHeal을 사용하며 prod 서비스는 수동으로 동기화합니다. 두 root의 선언 등록·수정은 prod에서도 자동입니다.

## 로컬 검증

필요한 도구: Helm 4.1.1, Python 3, PyYAML 6.0.1. 외부 차트 다운로드에는 네트워크가 필요합니다.

```bash
python3 scripts/gitops/validate.py --fixtures --external-charts
python3 -m unittest discover -s tests -v
```

`--external-charts`는 `source.chart`가 있는 모든 Application을 렌더링하고 Project 권한과 리소스 연결을 검사합니다. 외부 차트는 현재 `helm.releaseName`, 인라인 `helm.values`, `helm.skipCrds: true` 형식을 사용해야 합니다. 지원하지 않는 Helm 옵션은 무시하지 않고 검증을 실패시킵니다. 새 차트의 리소스 종류와 배포 방식이 기존 검증 규칙에 맞는지도 확인해야 합니다.

`--fixtures`는 비어 있는 이미지 주소와 태그만 테스트 값으로 채웁니다. 실제 값을 입력한 뒤에는 이 옵션을 빼고 검증합니다. 두 명령 모두 클러스터에 배포하지 않으며, 이미지 존재·API 실행·외부 서비스 연결도 검사하지 않습니다.

검증기는 Application·AppProject를 파일당 하나씩 읽으며 `.yaml`·`.yml`·`.json`을 검사합니다. Namespace 파일은 여러 YAML 문서도 허용합니다. 테스트는 API 차트 연결, 권한, 환경 정책, 스크립트 실패 처리를 확인하며 스크립트의 외부 명령은 대역으로 실행합니다.

## 최초 등록

- **이미지:** 공통 `image.repository`와 환경별 `image.tag` 입력. 현재는 비어 있습니다. 이미지는 non-root 사용자로 실행해야 하며, 차트에서 쓰기용으로 마운트한 경로는 `/tmp`입니다.
- **DB, Redis, JWT 설정:** 공급 방법 결정. 현재 차트는 런타임 Secret을 주입하지 않습니다. 필요한 변수는 [환경변수 예시](examples/farm-market-api.env.example)를 참고하고, 비밀값은 Git에 넣지 않습니다.
- **이미지 저장소:** `/data/uploads/` 설정은 있지만 쓰기 가능한 볼륨은 없습니다. 로컬 업로드를 사용하려면 저장 방식과 볼륨을 먼저 구성해야 합니다. prod의 이미지 제공 주소 `FARMMARKET_IMAGE_BASEURL`도 준비합니다.
- **Git 브랜치:** 위 표의 브랜치에 변경을 반영합니다. 2026-10-16 원격 확인 결과 `dev`·`master`는 있고 `stg`는 없습니다. 로컬 파일 수정만으로 Argo CD가 읽는 원격 내용은 바뀌지 않습니다.

설치에는 kubectl·Helm·클러스터 관리자 권한이 필요합니다. 아래 명령은 저장소 루트에서 실행합니다. **현재 kubectl context에 적용되며, dev/stg는 등록 후 자동 배포됩니다.**

```bash
kubectl config current-context

# Argo CD가 없는 클러스터에서 한 번만 실행하고 dev를 선택
bash scripts/gitops/argocd/install-argocd.sh

bash scripts/gitops/argocd/register-projects-root.sh dev
# projects-dev가 Synced인지, AppProject가 생성되었는지 확인
kubectl -n argocd get application projects-dev
kubectl -n argocd get appproject gitops-dev farm-market-dev infra-dev

bash scripts/gitops/argocd/register-applications-root.sh dev
kubectl -n argocd get applications
```

설치 스크립트는 Argo CD 차트 9.3.4를 사용하며, `argocd` namespace가 이미 있으면 중단합니다. 같은 클러스터에서 다른 환경을 등록할 때는 설치를 반복하지 않고 두 등록 스크립트에 해당 환경을 전달합니다. 등록 스크립트는 기존 리소스에 `apply`하며 삭제·재생성하지 않습니다.

설치 시 선택한 환경의 Argo CD Service 설정은 해당 인스턴스 전체에 적용됩니다. 여러 환경과 prod를 한 인스턴스에서 관리한다면 최초 설치 시 prod 설정(ClusterIP)을 사용합니다.

Git에서 Application·AppProject 선언을 삭제해도 root는 자동 prune하지 않습니다. 삭제 반영은 해당 root에서 수동으로 수행합니다. 현재 Application 선언에는 삭제 finalizer가 없으므로 root가 Application을 prune해도 배포된 Deployment·Service는 남습니다. 실제 서비스 삭제와 namespace 삭제는 별도 작업입니다. [Argo CD 삭제 동작](https://argo-cd.readthedocs.io/en/stable/user-guide/app_deletion/)

기존 ingress-nginx 등 다른 Service가 같은 NodePort를 사용한다면 전환 전에 충돌을 해소해야 합니다.

prod Argo CD 접속: `kubectl -n argocd port-forward svc/argocd-server 8443:443 --address 127.0.0.1` 실행 후 `https://localhost:8443`으로 접속합니다.

## 서비스 추가

1. `bootstrap/{env}/namespaces/{서비스명}.yaml`을 추가하고 관리자가 먼저 적용합니다. 예: `kubectl apply -f argocd/bootstrap/dev/namespaces/`. 이 명령은 해당 폴더 바로 아래 파일을 읽습니다.
2. `projects/{env}/{서비스명}/`에 필요한 권한별 AppProject를 추가합니다. 서비스 Project에는 `argocd` namespace와 Namespace 생성 권한을 주지 않습니다.
3. `applications/{env}/{서비스명}/`에 배포 대상별 Application을 추가하고 해당 Project를 참조합니다. 자체 차트를 사용하면 `charts/`에도 추가합니다.
4. 검증기와 테스트의 서비스별 조건을 함께 확장하고 대상 Git 브랜치에 반영합니다. 현재 Traefik 감시 범위·IngressClass 검증은 Farm Market 기준입니다.

root의 `directory.recurse: true`가 새 서비스 폴더도 읽으므로 서비스마다 root를 추가할 필요는 없습니다. Application·AppProject는 `.yaml` 파일을 기본 규칙으로 사용하며, 검증기는 [Argo CD가 읽는 다른 확장자](https://argo-cd.readthedocs.io/en/stable/user-guide/directory/)도 검사합니다.

## 로컬 kind 클러스터

Docker·kind·kubectl이 필요합니다. `bash scripts/k8s/kind-cluster/create-cluster.sh`는 `nodeport-config.yaml`로 `helm-cluster`를 만들고 노드를 확인합니다. `bash scripts/k8s/kind-cluster/delete-cluster.sh`는 해당 클러스터와 내부 리소스를 삭제합니다.

| 환경 | Traefik HTTP / HTTPS | Argo CD HTTP / HTTPS |
| --- | --- | --- |
| dev | 30080 / 30443 | 30180 / 30543 |
| stg | 31080 / 31443 | 31180 / 31543 |
| prod | 32080 / 32443 | ClusterIP, port-forward 사용 |

Argo CD TLS는 모든 환경에서 켜져 있습니다. kind 설정의 prod Argo CD 포트 32180·32543 매핑은 남아 있지만 현재 Service는 사용하지 않습니다. API Ingress의 TLS 인증서 설정은 별도이며 현재 `ingress.tls`는 비어 있습니다.

## EKS의 AWS Load Balancer Controller

AWS CLI, eksctl, Helm, kubectl이 필요합니다. AWS 인증과 대상 EKS의 kubectl context를 준비하고, `CLUSTER_NAME`, `DEFAULT_REGION`, `ACCOUNT_ID`, `VPC_ID`를 환경변수로 설정합니다. 모든 AWS 스크립트는 리전 변수로 `DEFAULT_REGION`을 사용합니다.

```bash
bash scripts/aws/eks/associate-iam-oidc-provider.sh
bash scripts/aws/eks/aws-load-balancer-controller/create-iam-policy.sh
bash scripts/aws/eks/aws-load-balancer-controller/create-iam-service-account.sh
bash scripts/aws/eks/aws-load-balancer-controller/deploy-controller.sh
```

IAM 정책 생성은 최초 한 번 실행합니다. 컨트롤러 배포는 현재 kubectl context에 설치하거나 업데이트하며, 각 스크립트는 명령 실패 시 중단합니다. 이 스크립트는 Argo CD의 자동 동기화 대상이 아닙니다.

현재 AWS 컨트롤러 차트 버전은 고정하지 않았고 IAM 정책은 upstream `main`에서 받습니다. 실행 시점에 결과가 달라질 수 있으므로 운영에 사용하기 전 두 버전을 함께 고정해야 합니다.
