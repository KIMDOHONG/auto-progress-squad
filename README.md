# 자동진행단 (Auto Progress Squad)

> Intel 융합 DX 6기 팀 프로젝트 저장소

## 웹 데모 바로 보기

[🚗 자동진행단 웹앱 실행하기](https://kimdohong.github.io/auto-progress-squad/)

[![GitHub Pages 배포 상태](https://github.com/KIMDOHONG/auto-progress-squad/actions/workflows/pages.yml/badge.svg)](https://github.com/KIMDOHONG/auto-progress-squad/actions/workflows/pages.yml)

공개 데모는 `main` 브랜치에 변경이 병합될 때마다 테스트와 빌드를 통과한 최신 버전으로 자동 갱신됩니다. Pull Request 검토 중인 변경은 병합되기 전까지 공개 데모에 반영되지 않습니다.

- 팀명: **자동진행단**
- 프로젝트명: **사용자 차량 프로필 기반 통합 자동차 AI 코파일럿**
- 프로젝트 기간: 2026-08-24 ~ 2026-09-09
- 발표 예정일: 2026-09-09
- 현재 단계: 요구사항 및 High Level Design 구체화

## 프로젝트 목표

사용자가 소유 차량을 최대 3대까지 등록하고, 현재 차량을 선택해 유지보수·차량 설명·실생활 지원 기능을 하나의 웹 챗봇에서 이용할 수 있도록 합니다.

## 확정 기능

### 사용자 개인화

- 차량 최대 3대 등록·수정·삭제
- 현재 사용할 차량 선택
- 선택 차량을 대시보드와 챗봇의 공통 문맥으로 사용

### 유지보수

- 경고등·증상 기반 안전 대응 챗봇
- 위험도별 다음 행동 안내
- 답변 근거와 불확실성 표시

### 차량 설명

- 차량 사용설명서 RAG 검색
- 차종별 리콜·안전정보 조회
- 대시보드 리콜 알림과 원문 출처 제공

### 실생활

- 전기차 예상 주행거리·필요 충전량 계산
- 경로 주변 충전소 탐색과 예상 충전·총 소요시간 계산
- 내연기관 차량의 지정연료(일반·고급·초고급 휘발유, 일반·하이세탄 경유) 취급 주유소 탐색
- 중고차 매물·성능점검표·보험이력 기반 위험 분석

## 프런트엔드 MVP 실행

```powershell
cd src/web
corepack enable
corepack prepare pnpm@11.19.0 --activate
pnpm install
pnpm dev
```

현재 MVP는 차량 최대 3대, 활성 차량 전환, 동력원별 플래너 전환과 고정 챗봇 문맥을 브라우저 로컬 저장소로 구현합니다. 외부 지도·충전소·주유소 API와 AI 모델은 아직 연결하지 않았으며 화면에서 샘플 상태로 명시합니다.

## 이번 범위에서 제외

- OBD-II 장비 연동
- 타이어 사진 분석 모델
- 자동차 소음 분류 모델

위 기능은 데이터·장비·검증이 확보된 이후의 확장 항목으로만 관리합니다.

## 기본 화면

- 상단: 현재 선택 차량
- 좌측: 기능 메뉴
- 중앙: 대시보드·지도·분석 결과
- 우측: 항상 표시되는 챗봇

## 문서

| 경로 | 용도 |
| --- | --- |
| [docs/problem-definition.md](docs/problem-definition.md) | 문제, 목표, 범위, 성공 기준 |
| [docs/use-cases.md](docs/use-cases.md) | 핵심 사용자 흐름과 예외 |
| [docs/architecture.md](docs/architecture.md) | High Level Design |
| [docs/roles.md](docs/roles.md) | 역할 분담과 협업 규칙 |
| [docs/decisions](docs/decisions) | 기술·범위 결정 기록 |
| [docs/troubleshooting.md](docs/troubleshooting.md) | 오류와 해결 과정 |

## 개발 원칙

1. 모든 기능은 가능한 한 GitHub Issue에 연결합니다.
2. 구현은 작업 브랜치와 Pull Request를 사용합니다.
3. 사실, 외부 데이터, AI 추정을 답변에서 구분합니다.
4. 자동차 안전·구매 판단은 확정 진단이 아니라 근거 있는 보조정보로 제공합니다.
5. 기술 스택 확정 후 설치·실행·테스트 명령을 이 문서에 추가합니다.

## 참고 자료

- [이전 기수 저장소 모음](https://github.com/pskcci?tab=repositories)
- [DX-03 프로젝트 문서 템플릿](https://github.com/pskcci/DX-03/tree/main/doc/project)

## 팀원

| 이름 | GitHub | 담당 영역 |
| --- | --- | --- |
| 김도홍 | [@KIMDOHONG](https://github.com/KIMDOHONG) | 조율 예정 |
| 팀원 2 | TODO | TODO |
| 팀원 3 | TODO | TODO |
