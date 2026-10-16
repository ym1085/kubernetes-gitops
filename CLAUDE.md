# CLAUDE.md

- CRITICAL: 답변, 문서, 커밋 메시지에 가운뎃점(U+00B7)이나 장식용 구분 기호를 사용하지 않는다. 쉼표, 문장 또는 일반 Markdown 목록으로 구분한다.
- CRITICAL: 커밋 메시지에 `Co-authored-by`, `Co-developed-by`, `Generated with` 같은 공동 작성자 표기나 AI 도구 서명을 추가하지 않는다. 변경 내용만 작성한다.

프로젝트 구조, 환경 계약, 수정 위치와 검증 명령은 [AGENTS.md](AGENTS.md)를 따른다.

실제 배포 판단은 `argocd/applications/{env}`에서 시작한다. 로컬 파일 수정이 원격 Argo CD 동기화나 클러스터 적용을 의미하지 않는다.
