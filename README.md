# Farm Market GitOps

[Farm Market API](https://github.com/ym1085/farm-market-platform)의 단일 Spring Boot 서버와 Traefik을 관리합니다. 애플리케이션 소스와 이미지 빌드는 API 저장소에서 관리합니다.

배포 판단 기준은 `argocd/applications/{env}`입니다. 현재 API 이미지 주소·태그는 미입력 상태이며, 입력 전에는 Helm 검증이 실패하도록 구성했습니다.

```text
argocd/
  bootstrap/{env}/       # Argo CD 설치 override, 관리자 Project, root Applications
  applications/{env}/   # apps: API / infra: 외부 Helm 차트
  projects/{env}/       # 서비스·플랫폼별 배포 권한
charts/farm-market-api/ # 공통 차트 + values-{env}.yaml
scripts/gitops/         # 최초 등록과 로컬 검증
examples/              # 비밀값이 없는 Secret 입력 양식
tests/                 # 렌더링 계약과 등록 스크립트 테스트
.github/workflows/     # PR 검증
```

| 환경 | Git revision | API profile / port | API namespace / Project | 서비스 배포 |
| --- | --- | --- | --- | --- |
| dev | dev | dev / 8081 | farm-market-dev | 자동 |
| stg | stg | dev / 8081 | farm-market-stg | 자동 |
| prod | master | prod / 8082 | farm-market-prod | 수동 |

stg는 API에 전용 프로필이 없어 dev 프로필을 사용하며 DB·Redis·JWT 설정은 stg namespace의 Secret으로 분리합니다. 원격 `stg` 브랜치는 검토 시 존재하지 않았으므로 등록 전에 준비해야 합니다.

## 검증

Helm 4.1.1, Python 3, PyYAML 6.0.1을 사용합니다.

```bash
python3 scripts/gitops/validate.py --fixtures --external-charts
python3 -m unittest discover -s tests -v
```

`--fixtures`는 비어 있는 이미지 필드만 테스트 값으로 채웁니다. 배포 가능 여부를 확인할 때는 이미지 주소·태그를 입력한 후 `python3 scripts/gitops/validate.py`를 실행합니다. 검증기는 모든 Application의 Project·source·destination을 검사하고 로컬 API 차트와 버전이 고정된 외부 Traefik 차트를 환경별로 렌더링합니다. 외부 차트 검증에는 네트워크가 필요하며, 실제 클러스터는 검사하지 않습니다.

## 최초 연결

이미지·Secret·외부 DB/Redis를 준비하고 변경을 대상 Git 브랜치에 반영한 다음 실행합니다. 상세 입력값과 전환 절차는 [운영 가이드](argocd/docs/README.md)를 확인합니다.

```bash
# Argo CD가 없을 때 한 번만 설치
bash scripts/gitops/argocd/bootstrap-argocd.sh

# 현재 kubectl context에 dev용 root 선언 등록
bash scripts/gitops/argocd/setup-appprojects.sh dev
bash scripts/gitops/argocd/setup-applications.sh dev
```

이후 Application·AppProject 추가와 수정은 root Applications가 Git에서 반영합니다. 서비스 배포는 위 환경별 정책을 따릅니다. root의 자동 prune은 꺼져 있어 선언 삭제는 별도 수동 prune이 필요합니다.

## 확장

새 실행 서비스를 추가할 때 차트와 환경 values, `applications/{env}/apps` 선언을 추가합니다. 같은 권한 범위라면 기존 Project를 사용하고, namespace 또는 저장소가 달라지면 Project도 함께 수정합니다. 공통 배포 스크립트에는 서비스 이름을 추가하지 않습니다.

Traefik 차트 41.7.1을 사용하며 기존 환경별 NodePort를 유지합니다. 기존 ingress-nginx가 설치되어 있다면 [전환 절차](argocd/docs/README.md#ingress-nginx에서-traefik으로-전환)를 먼저 따릅니다.
