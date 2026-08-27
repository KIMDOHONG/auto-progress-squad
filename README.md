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
- 현재 단계: 프런트엔드 MVP 완료·백엔드 기반 구축

## 프로젝트 목표

사용자가 소유 차량을 최대 3대까지 등록하고, 현재 차량을 선택해 유지보수·차량 설명·실생활 지원 기능을 하나의 웹 챗봇에서 이용할 수 있도록 합니다.

## 확정 기능

### 사용자 개인화

- 차량 최대 3대 등록·수정·삭제
- AI 코파일럿에서 현대·기아·제네시스 차량을 차명·연식으로 찾고, 세대가 겹치면 공식 차량 이미지로 선택
- 프로필이 3대인 경우 기존 차량을 선택해 교체하고, 삭제 요청은 최종 확인 후 반영
- 현재 사용할 차량 선택
- 선택 차량을 대시보드와 챗봇의 공통 문맥으로 사용

### 유지보수

- 경고등·증상 기반 안전 대응 챗봇
- 위험도별 다음 행동 안내
- 답변 근거와 불확실성 표시

### 차량 설명

- 현대·기아·제네시스 공식 취급설명서 차량 찾기
- 등록된 차종·연식·프로젝트 코드가 일치할 때 공식 디지털 설명서 직접 연결
- 차량 사용설명서 RAG 검색
- 차종별 리콜·안전정보 조회
- 대시보드 리콜 알림과 원문 출처 제공

### 실생활

- 전기차 예상 주행거리·필요 충전량 계산
- 경로 주변 충전소 탐색과 예상 충전·총 소요시간 계산
- 수소전기차의 경로 주변 수소충전소·운영 상태·우회 정보 확인
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

현재 MVP는 `2021 현대 넥쏘`, `2027 제네시스 ELECTRIFIED GV70`, `2021 BMW M3` 프리셋과 차량 최대 3대, 활성 차량 전환, 동력원별 플래너 전환, 공식 취급설명서 연결, 고정 챗봇 문맥을 브라우저 로컬 저장소로 구현합니다. 넥쏘는 `FE · 2021`, ELECTRIFIED GV70은 `JKEV · 2027` 공식 문서로 연결하며, BMW는 VIN 확보 전까지 문서를 추측해 연결하지 않습니다.

AI 코파일럿에서는 현대·기아·제네시스 차명과 연식을 제조사 공식 차량 목록에서 확인한 뒤 프로필 후보를 제시합니다. 같은 연식에 여러 세대가 있으면 공식 차량 이미지와 프로젝트 코드 중 하나를 사용자가 선택해야 하며, 3대가 이미 등록된 경우 교체할 프로필과 최종 삭제·등록 여부를 다시 확인합니다. BMW는 프로필의 차명·연식을 화면에 그대로 표시하고 공식 Driver's Guide로 안내하되, 정확한 문서는 제조사 페이지에서 17자리 VIN으로 식별하도록 합니다. 쉐보레와 KGM은 현재 공식 취급설명서 시작 페이지만 안내하며, 세부 모델·연식 자동 식별은 아직 연결하지 않았습니다. 그 밖의 제조사도 실제로 확인하지 않은 공식 문서가 있는 것처럼 표현하지 않습니다.

외부 지도·전기·수소 충전소·주유소 API, 리콜 데이터와 매뉴얼 RAG 모델은 아직 연결하지 않았으며 화면에서 미연동 상태를 명시합니다. 매뉴얼 RAG는 향후 백엔드에서 문서 수집 상태를 `확인 중 → 사용 가능 → 실패`로 관리하고, 저작권·재배포 조건을 확인한 문서만 서버 저장소와 검색 인덱스에 보관할 예정입니다. GitHub Pages나 브라우저 로컬 저장소에 제조사 PDF를 일괄 복제하지 않습니다.

로컬 FastAPI와 차량 정보를 동기화하려면 `src/web/.env.example`을 `.env.local`로 복사한 뒤 프런트엔드를 실행합니다. 환경 변수가 없는 GitHub Pages 공개 데모는 브라우저 저장 모드로 유지되며 상단 상태 배지에서 저장 위치를 확인할 수 있습니다.

## 백엔드 API 실행

```powershell
cd src/api
uv sync --extra test
uv run fastapi dev
```

- API 문서: `http://127.0.0.1:8000/docs`
- 상태 확인: `http://127.0.0.1:8000/api/v1/health`
- 테스트: `uv run pytest`

현재 백엔드는 차량 프로필 CRUD·활성 차량 전환용 SQLite API와 매뉴얼·리콜 API 계약을 제공합니다. 프런트엔드의 공식 취급설명서 링크는 제조사 원문을 새 탭으로 열며, 매뉴얼 RAG와 리콜 원천 데이터는 아직 연결하지 않았습니다. 백엔드 매뉴얼 검색 요청은 `503` 미연동 오류로 명확하게 반환합니다.

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
- [현대자동차 공식 취급설명서](https://ownersmanual.hyundai.com/main?langCode=ko_KR&countryCode=A99)
- [기아 공식 취급설명서](https://ownersmanual.kia.com/main?langCode=ko_KR&countryCode=A99)
- [제네시스 공식 취급설명서](https://ownersmanual.genesis.com/main?langCode=ko_KR&countryCode=A99)
- [BMW Driver's Guide](https://www.bmw.co.kr/ko/topics/owners/online-manual/bmw-driver-guide.html)
- [쉐보레 공식 취급설명서](https://www.chevrolet.co.kr/owner-manuals)
- [KGM 공식 취급설명서](https://www.kg-mobility.com/sr/update-download/download-center/instruction-manual)

## 팀원

| 이름 | GitHub | 담당 영역 |
| --- | --- | --- |
| 김도홍 | [@KIMDOHONG](https://github.com/KIMDOHONG) | 조율 예정 |
| 팀원 2 | TODO | TODO |
| 팀원 3 | TODO | TODO |
