# CLAUDE.md

프로젝트 구조, 환경 계약, 수정 위치와 검증 명령은 [AGENTS.md](AGENTS.md)를 따른다.

실제 배포 판단은 `argocd/applications/{env}`에서 시작한다. 로컬 파일 수정이 원격 Argo CD 동기화나 클러스터 적용을 의미하지 않는다.
