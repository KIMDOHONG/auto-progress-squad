# 자동진행단 (Auto Progress Squad)

> Intel 융합 DX 6기 팀 프로젝트 저장소

## 웹 데모 바로 보기

[🚗 자동진행단 웹앱 실행하기](https://kimdohong.github.io/auto-progress-squad/)

[![GitHub Pages 배포 상태](https://github.com/KIMDOHONG/auto-progress-squad/actions/workflows/pages.yml/badge.svg)](https://github.com/KIMDOHONG/auto-progress-squad/actions/workflows/pages.yml)

공개 데모는 `main` 브랜치에 변경이 병합될 때마다 테스트와 빌드를 통과한 최신 버전으로 자동 갱신됩니다. Pull Request 검토 중인 변경은 병합되기 전까지 공개 데모에 반영되지 않습니다.

## 현재 구현 화면 한눈에 보기

모든 화면은 상단의 **활성 차량**을 공통 기준으로 사용하며, 우측 AI 코파일럿은 어느 메뉴에서도 계속 사용할 수 있습니다.

| 화면 | 현재 확인할 수 있는 내용 | 상태 |
| --- | --- | --- |
| 홈 | 활성 차량 정보, 주요 기능 진입, 차량별 동력원 분기 | 구현 완료 |
| 차량 관리 | 차량 최대 3대 등록·수정·삭제, 활성 차량 전환, 필수 트림·세부 구동 사양, 현대·기아·제네시스 주요 전기차 배터리 제원 자동 적용, 내연기관 연료탱크 용량 저장·K5 공식 탱크 자동 적용 | 전기차 현행 카탈로그와 K5 2025·2026 탱크 파일럿 구현, 내연기관 공식 탱크 카탈로그 확대 필요 |
| AI 코파일럿 | 현대·기아·제네시스 공식 차량 검색, 이미지 기반 세대 선택, 트림·세부 구동 사양 확인 후 프로필 등록·교체·삭제 | 구현 완료 |
| 매뉴얼·리콜 | 현대·기아·제네시스 공식 설명서 연결, BMW Driver's Guide 안내, FastAPI 모드의 승인된 쉐보레·KGM 장별 문서 수집 | 매뉴얼 연결·승인 문서 검색 구현·자동차리콜센터 공급자 계약 구현, 실제 API 승인·연결 대기 |
| EV 충전 플래너 | 정확한 주소 확인·GPS 출발지·편도/왕복·복수 NAVER 실제 경로 선택 또는 수동 거리와 배터리·SoC·전비·도착 최소 SoC 기반 도착 가능 여부·필요 충전량, 필요량/출발 전 100% 선택 | 로컬 계산·경로 표시와 한국환경공단 전기차 충전소 위치·출력·상태 어댑터 구현, 공공데이터 서비스키로 활성화 |
| 수소 충전 플래너 | 정확한 주소 확인·GPS 출발지·편도/왕복·복수 NAVER 실제 경로 선택 또는 수동 거리와 현재 주행가능거리 기반 도착 가능 여부·부족 거리, 가득 충전 원칙 고정 안내 | 로컬 계산·경로 공급자·좌표 경로 표시 구현, 실시간 수소충전소 API 미연동 |
| 주유 경로 플래너 | 정확한 주소 확인·GPS 출발지·편도/왕복·복수 NAVER 실제 경로 선택 또는 수동 거리와 탱크 용량·현재 연료량·평균 연비·도착 희망 잔량·단가 기반 필요 주유량·비용 계산, 가득/필요량 선택 | 로컬 주유 계산·경로 공급자·좌표 경로 표시 구현, 주유소 가격·상태 API 미연동 |
| 유지보수 | 경고등·증상 안전 대응 진입 화면 | 다음 구현 단계 |
| 중고차 분석 | 매물·성능점검표·보험이력 분석 진입 화면 | 다음 구현 단계 |

[Pull Request #21](https://github.com/KIMDOHONG/auto-progress-squad/pull/21)은 병합과 GitHub Pages 배포까지 완료되어 위 공개 데모에서 바로 확인할 수 있습니다. 현재 진행 중인 변경은 별도 Pull Request에서 검토한 뒤 `main`에 병합합니다.

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
- 새 프로필은 동력원·세부 구동 사양·트림을 반드시 확인하고, 정확히 승인된 전기차 구성은 배터리 용량과 공식 출처를 자동 저장. 내연기관·하이브리드는 주유량 계산용 연료탱크 용량을 함께 저장 가능
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

## 로컬에서 현재 화면 바로 실행하기

### 1. 프런트엔드만 빠르게 체험

Node.js `22.12.0` 이상이 필요합니다. 저장소를 내려받은 뒤 저장소 최상위 폴더에서 실행합니다.

```powershell
cd src/web
corepack enable
corepack prepare pnpm@11.19.0 --activate
pnpm install
pnpm dev
```

터미널에 표시되는 주소 또는 아래 주소를 브라우저에서 엽니다.

- 로컬 웹앱: `http://127.0.0.1:5173/auto-progress-squad/`
- 종료: 실행 중인 터미널에서 `Ctrl+C`

이 방법은 별도 서버 없이 차량 프로필을 브라우저 로컬 저장소에 보관합니다. 현대·기아·제네시스 차량 검색, 세대 선택, 프로필 교체·삭제, 동력원별 플래너와 공식 매뉴얼 연결을 바로 시험할 수 있습니다.

차량 등록의 자동 제원 카탈로그는 연식·차명·동력원·세부 구동 사양이 모두 일치하고 실제 트림명이 입력되었을 때만 적용됩니다. 배터리 용량이 트림과 무관하면 트림 목록을 중복 저장하지 않고 사용자가 실제 트림명을 입력하게 하며, 용량과 공식 출처는 공통 저장소 정의를 여러 차종 조합이 참조합니다. 현재 승용·SUV 중심 범위는 현대 아이오닉 5·5 N·6·6 N·9·코나 Electric·캐스퍼 일렉트릭, 기아 EV3·EV4·EV5·EV6·EV9와 각 GT 모델·니로 EV·니로 플러스·레이 EV, 제네시스 GV60·GV60 MAGMA·ELECTRIFIED GV70·ELECTRIFIED G80의 카탈로그에 명시된 연식입니다. 근거는 [현대 전기차 배터리 정보](https://www.hyundai.com/kr/ko/service-membership/ev/ev-battery-cell-information), [기아 차종별 공식 제원](https://www.kia.com/kr/vehicles/ev), [니로 플러스 공식 가격 페이지](https://www.kia.com/kr/vehicles/niro-plus/price), [제네시스 전기차 배터리 정보](https://www.genesis.com/kr/ko/support/notice/detail/0000000547.html)입니다. 자동 매핑이 없는 전기차는 사용자가 확인한 배터리 용량을 입력해야 하며 이를 공식 자동 제원처럼 표시하지 않습니다. 상용·PBV·단종 전기차의 모든 과거 연식은 아직 자동 카탈로그 범위가 아닙니다. 내연기관·하이브리드 프로필도 연료탱크 용량을 API와 SQLite까지 저장하며, 공식 파일럿으로 2025·2026 K5 가솔린 1.6 T-GDI·2.0 CVVL은 60 L, K5 2.0 하이브리드는 50 L를 동력원별로 자동 적용합니다. 근거가 확인되지 않은 연식·세대·파워트레인(현재 BMW 320d 포함)은 사용자가 확인한 용량을 입력하며 공식 자동 제원으로 표시하지 않습니다. 하이브리드·PHEV처럼 같은 차명 안에서도 탱크가 달라지는 경우가 있어 차명만으로 추정하지 않습니다.

동력원별 플래너는 지도 API가 없어도 경로 거리를 직접 입력해 사용할 수 있습니다. FastAPI 모드에서 서버에 NAVER Maps 인증값을 설정하면 출발지·목적지의 정확한 주소를 먼저 확인하거나 GPS 좌표를 도로명 주소로 변환한 뒤, 실시간 빠른 길·실시간 최적·무료 우선 경로의 거리·예상 시간·통행료와 실제 좌표 경로를 조회합니다. 편도와 왕복을 선택할 수 있으며 왕복은 가는 길과 오는 길을 각각 조회해 거리·시간·통행료·경로선을 합산합니다. 사용자가 경로를 바꾸면 해당 거리로 에너지 계산도 다시 수행하며, Web Dynamic Map 키가 없을 때도 좌표 경로 SVG를 표시합니다. 조회 실패는 0 km나 계산 성공으로 취급하지 않습니다. EV는 배터리 용량·현재 SoC·전비·도착 최소 SoC로 예상 소비전력과 최소 필요 충전량을 계산합니다. `필요한 만큼 충전`은 현재 SoC로 출발해 경로 중 필요한 총량을 표시하고, `출발 전 100% 충전`은 출발 전 충전량과 이후에도 필요한 경로 중 추가량을 나눠 표시합니다. 수소차는 현재 주행가능거리와 경로 거리를 비교하며, 충전량 선택은 제공하지 않고 국내 운용 관행에 따른 가득 충전 원칙과 충전기 압력·충전소 저장량에 따른 실제 충전량 변동 가능성을 안내합니다. 내연기관·하이브리드는 `소비 연료 = 거리 ÷ 최근 평균 연비`, `최소 필요 주유량 = max(0, 소비 연료 + 도착 희망 잔량 - 현재 연료량)`, `예상 비용 = 계획 주유량 × 입력 단가`로 계산합니다. 출발 전 필요한 만큼 또는 가득 주유를 고를 수 있고, 한 탱크로 부족하면 출발 전 주유량과 경로 중 추가량을 분리합니다. 계산식과 입력 조건은 결과에 표시하며, 충전소·주유소 위치·실시간 가격·영업 상태가 포함되지 않았다는 점을 별도 상태로 구분합니다.

GPS 출발지는 현재 앱을 연 브라우저의 위치 권한과 Windows 위치 서비스를 사용합니다. Wi-Fi 노트북에서는 네트워크 기반 위치를 우선 요청하며, 좌표 획득 후 서버의 Reverse Geocoding으로 주소를 확인합니다. 좌표를 얻었지만 Reverse Geocoding이 설정되지 않은 경우 입력칸에 GPS 좌표를 남기고 주소 미확인 상태를 별도로 안내합니다. Chrome에서 허용한 위치 권한은 Codex 내장 브라우저 등 다른 브라우저에 자동으로 공유되지 않습니다.

> 현재 AI 코파일럿의 차량 식별과 프로필 관리는 제조사 공식 차량 데이터를 사용하는 규칙형 기능입니다. FastAPI 모드에서는 승인된 로컬 매뉴얼의 출처 검색까지 사용할 수 있지만, 실제 LLM 기반 자유 대화와 생성형 답변은 아직 연결하지 않았습니다.

현재 MVP는 `2021 현대 넥쏘`, `2027 제네시스 ELECTRIFIED GV70`, `2021 BMW M3` 프리셋과 차량 최대 3대, 활성 차량 전환, 동력원별 플래너 전환, 공식 취급설명서 연결, 고정 챗봇 문맥을 브라우저 로컬 저장소로 구현합니다. 넥쏘는 `FE · 2021`, ELECTRIFIED GV70은 `JKEV · 2027` 공식 문서로 연결하며, BMW는 VIN 확보 전까지 문서를 추측해 연결하지 않습니다.

AI 코파일럿에서는 현대·기아·제네시스 차명과 연식을 제조사 공식 차량 목록에서 확인한 뒤 프로필 후보를 제시합니다. 같은 연식에 여러 세대가 있으면 공식 차량 이미지와 프로젝트 코드 중 하나를 사용자가 선택해야 하며, 3대가 이미 등록된 경우 교체할 프로필과 최종 삭제·등록 여부를 다시 확인합니다. BMW는 프로필의 차명·연식을 화면에 그대로 표시하고 공식 Driver's Guide로 안내하되, 정확한 문서는 제조사 페이지에서 17자리 VIN으로 식별하도록 합니다. 쉐보레와 KGM은 FastAPI 모드에서 운영자가 승인한 정확한 차명·연식·세대 매핑만 연결하며, 카탈로그가 없거나 정확히 일치하지 않으면 공식 취급설명서 시작 페이지만 안내합니다. 그 밖의 제조사도 실제로 확인하지 않은 공식 문서가 있는 것처럼 표현하지 않습니다.

외부 경로 조회는 선택형 NAVER Maps 서버 어댑터, 정확한 주소·GPS 확인, 복수 경로 선택과 실제 좌표 경로 표시까지 구현했습니다. 2026-09-03 실제 계정 키로 Geocoding·Reverse Geocoding·Directions 5의 로컬 E2E를 확인했으며, 확인 완료된 주소는 경로 조회 때 문자열로 다시 검색하지 않고 확정 좌표를 사용합니다. Dynamic Map은 아직 활성화하지 않아 좌표 경로 SVG를 사용합니다. 충전·주유소 공통 계약과 로컬 정규 스냅샷에 더해 한국환경공단 전기차 충전소 어댑터와 한국석유관리원 수소충전소 운영·실시간정보 결합 어댑터를 연결했습니다. 2026-09-08에는 승인된 실제 계정키로 부산-인제 NAVER 경로 주변 수소충전소의 좌표·상태·압력·대기 대수·튜브트레일러 압력·갱신시각이 화면까지 전달되는 E2E를 완료했습니다. 상세 결과는 [수소충전소 실제 계정키 E2E 기록](docs/hydrogen-station-live-e2e.md)에 남겼습니다. FastAPI 실행 시 각 공공데이터 서비스키가 설정된 에너지원만 공식 후보를 조회하며, 주유소는 아직 공급자 미설정 상태를 유지합니다. 실제 리콜 데이터도 아직 연결하지 않았습니다. 리콜은 사전 협의가 필요한 자동차리콜센터 API만 승인 공급자로 정하고, 공급자 미설정·장애·0건을 서로 다른 상태로 반환하는 서버 계약을 구현했습니다. 공급자 후보는 제조사·차명·연식·세대·프로젝트 코드의 정규 키가 모두 일치할 때만 반환하며 인접 연식이나 세대를 대신 연결하지 않습니다. FastAPI 모드에서는 정확한 공식 매뉴얼이 확인된 차량마다 문서 준비 작업을 `확인 중(pending) → 사용 가능(ready) / 실패(failed)` 상태로 관리합니다. 서버 관리자가 승인한 manifest의 PDF/TXT만 추출·청크화해 SQLite에 저장하며, `ready`가 된 현재 차량 문서에서만 키워드 기반 출처 검색을 제공합니다. 제조사 사이트 자동 다운로드는 아직 수행하지 않고, GitHub Pages나 브라우저 로컬 저장소에도 제조사 PDF를 복제하지 않습니다.

### 2. FastAPI와 함께 로컬 실행

Windows에서는 저장소 루트에서 아래 단일 명령을 사용하는 방법을 권장합니다. NAVER Client ID·Client Secret, 선택형 EV 충전소 서비스키, 선택형 수소충전소 서비스키를 차례로 입력하면 FastAPI(`8000`)와 Vite(`5173`)가 함께 실행되고 브라우저가 열립니다. 활용신청이 아직 승인되지 않은 공공데이터는 해당 입력에서 바로 Enter를 눌러 건너뛸 수 있습니다. 시스템 PATH에 Node.js가 없어도 Codex 데스크톱에 포함된 Node.js를 자동으로 찾습니다. 키는 파일이나 명령행에 저장되지 않으며 이 PowerShell 창에서 `Ctrl+C`를 누르면 두 서버가 함께 종료됩니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-local-app.ps1
```

이미 `5173` 또는 `8000` 포트가 사용 중이면 기존 개발 서버를 먼저 종료하라는 메시지가 표시됩니다.

아래는 두 터미널을 직접 관리해야 할 때 사용하는 수동 실행 방법입니다.

첫 번째 PowerShell 터미널에서 백엔드를 실행합니다.

```powershell
cd src/api
uv sync --extra test
uv run fastapi dev
```

실제 주소·GPS·경로 조회에는 NAVER Cloud Maps 애플리케이션에서 **Geocoding**, **Reverse Geocoding**, **Directions 5**를 활성화합니다. **Dynamic Map**은 NAVER 배경 지도 위에 경로선을 표시할 때만 추가하며, 없어도 좌표 경로 SVG가 표시됩니다. 서버 호출용 Client ID·Client Secret을 환경변수로 설정합니다. 서버 Client Secret은 `.env`, 프런트엔드 코드, 로그 또는 Git에 넣지 않습니다. Dynamic Map을 사용할 때의 웹 지도 Client ID는 브라우저에 전달되는 공개 식별자이므로 NAVER Cloud 콘솔에서 `http://127.0.0.1:5173` 등 실제 사용하는 Web 서비스 URL만 허용해야 합니다.

백엔드만 별도로 실행하려면 인증값을 파일에 남기지 않는 도우미를 사용할 수 있습니다. 두 값을 차례로 붙여 넣으면 백엔드가 기본 `http://127.0.0.1:8000`에서 실행되며, 종료하면 프로세스 환경변수도 제거됩니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-naver-maps-api.ps1
```

```powershell
$env:APS_NAVER_MAPS_CLIENT_ID = "발급받은 Client ID"
$env:APS_NAVER_MAPS_CLIENT_SECRET = "발급받은 Client Secret"
$env:APS_NAVER_MAPS_BROWSER_CLIENT_ID = "Dynamic Map용 Client ID"
uv run fastapi dev
```

두 번째 PowerShell 터미널에서 프런트엔드 환경 파일을 만든 뒤 실행합니다.

```powershell
cd src/web
Copy-Item .env.example .env.local
corepack enable
corepack prepare pnpm@11.19.0 --activate
pnpm install
pnpm dev
```

이 모드에서는 차량 프로필이 로컬 FastAPI와 SQLite에 저장됩니다. 환경 변수가 없는 GitHub Pages 공개 데모는 브라우저 저장 모드로 유지되며, 상단 상태 배지에서 현재 저장 위치를 확인할 수 있습니다.

공식 매뉴얼이 정확히 매칭된 차량은 등록과 동시에 SQLite에 `pending` 준비 작업이 생성됩니다. 매뉴얼 화면은 API 상태를 조회해 **취급설명서를 확인 중입니다**를 표시하며, `ready`가 되기 전에는 질문 전송을 막습니다. 승인 문서를 준비한 뒤 아래 작업자를 실행하면 텍스트 추출·청크 저장과 `ready` 전환이 수행되고, 화면에서 질문과 문서명·페이지·공식 원문 링크를 확인할 수 있습니다.

### 승인된 매뉴얼 준비

현대·기아·제네시스는 공식 차종 API로 연결된 등록 차량을 대상으로 준비 명령을 실행할 수 있습니다. 명령을 실행하는 운영자가 제조사 사이트의 이용 조건을 확인하고 `--confirm-official-source`로 승인해야 하며, 앱의 일반 사용자 요청만으로 원문을 자동 수집하지 않습니다. 공식 API가 PDF를 제공하면 PDF를 사용하고, EV6처럼 웹 설명서만 제공하면 목차의 각 본문을 출처 URL이 보존된 UTF-8 TXT 묶음으로 준비합니다. 준비가 끝나면 같은 명령에서 차량별 검색 인덱스까지 생성합니다.

```powershell
cd src/api
uv run python -m app.official_manual_prepare --vehicle-id <차량 ID> --confirm-official-source
```

연결된 현대·기아·제네시스 차량을 한 번에 준비하려면 `--vehicle-id` 대신 `--all`을 사용합니다. 같은 프로젝트 코드와 연식은 같은 `document_key`를 사용하므로 동일 설명서를 다시 등록해도 기존 청크를 재사용합니다. 다운로드한 원문과 생성된 `manifest.json`은 `APS_MANUAL_SOURCE_DIR` 아래에만 저장되며 Git에서 제외됩니다. 다른 제조사는 화요일 마감 범위에서 제외하고 기존 승인 카탈로그 방식만 유지합니다.

`APS_MANUAL_SOURCE_DIR`(기본값 `src/api/data/manuals`) 안에 매뉴얼 파일과 `manifest.json`을 둡니다. 저장소에는 제조사 PDF를 커밋하지 않습니다.

```json
{
  "documents": [
    {
      "document_key": "hmc:FE:2021",
      "document_name": "넥쏘 2021 취급설명서",
      "source_url": "https://ownersmanual.hyundai.com/manual/example",
      "file": "hmc_fe_2021.pdf"
    }
  ]
}
```

쉐보레·KGM처럼 한 설명서가 여러 PDF로 나뉜 경우에는 단일 `file` 대신 `chapters`를 사용합니다. 각 장에는 제목, 해당 장의 공식 HTTPS 원문 URL과 승인 디렉터리 안의 로컬 파일 경로가 필요합니다. 전체 형식은 [장별 매뉴얼 manifest 예시](docs/examples/manual-manifest.chapter-bundle.example.json)를 참고하세요. 예시에 적힌 파일명은 배치 위치만 나타내며 PDF 자체는 저장소에 포함하지 않습니다.

```powershell
cd src/api
uv run python -m app.manual_worker --vehicle-id sample-nexo
```

작업자는 manifest의 문서 키와 현재 차량의 검증된 문서 키가 정확히 일치하고, 모든 파일이 승인 디렉터리 내부에 있으며, 대표 URL과 장별 URL이 해당 제조사 공식 HTTPS 도메인인 경우에만 처리합니다. 단일 파일 또는 파일 묶음의 총 읽기 크기는 100MB로 제한됩니다. `--vehicle-id`를 생략하면 전체 `pending` 작업을 처리합니다.

같은 `document_key`와 묶음 해시가 이미 준비된 경우에는 PDF/TXT를 다시 추출하지 않고 기존 청크를 재사용합니다. 파일 내용·장 제목·공식 URL 중 하나라도 바뀐 경우에는 새 청크와 해시를 하나의 SQLite 트랜잭션에서 교체하며, 기존 청크는 남기지 않습니다. 장별 문서는 각 장의 제목과 공식 URL을 검색 결과에 보존하고 페이지는 각 원본 파일에서 1부터 표시합니다. 여러 차량이 같은 문서를 공유하면 마지막 차량 참조가 삭제될 때에만 문서와 청크를 정리합니다. 상세 결정은 [ADR-0006](docs/decisions/0006-ingest-operator-approved-manual-chapter-bundles.md)을 따릅니다.

## 백엔드 API 실행

```powershell
cd src/api
uv sync --extra test
uv run fastapi dev
```

- API 문서: `http://127.0.0.1:8000/docs`
- 상태 확인: `http://127.0.0.1:8000/api/v1/health`
- 차량별 매뉴얼 준비 상태: `GET /api/v1/vehicles/{vehicle_id}/manual-ingestion`
- 실패 작업 재시도: `POST /api/v1/vehicles/{vehicle_id}/manual-ingestion/retry`
- 준비 완료 문서 검색: `POST /api/v1/manual/search`
- 제조사 매뉴얼 어댑터 지원 상태: `GET /api/v1/manual-adapters`
- 승인된 쉐보레·KGM 매뉴얼 매핑 조회: `POST /api/v1/manual-adapters/{adapter_id}/resolve`
- 승인 매핑을 기존 차량 프로필에 연결: `POST /api/v1/vehicles/{vehicle_id}/manual-adapters/{adapter_id}`
- 정확한 주소 확인: `POST /api/v1/planner/location/resolve`
- GPS 좌표의 도로명 주소 확인: `POST /api/v1/planner/location/reverse`
- 웹 지도 사용 가능 상태: `GET /api/v1/planner/map-config`
- 복수 실제 경로 거리·시간·통행료·좌표 조회: `POST /api/v1/planner/route`
- 선택 경로 주변 충전·주유소 후보 조회: `POST /api/v1/planner/stations`
- 테스트: `uv run pytest`

플래너 화면은 실제 경로를 선택한 뒤 충전소·수소충전소·주유소 후보를 경로 반경별로 비교 표시합니다. 전기차는 `APS_EV_CHARGER_SERVICE_KEY`가 있으면 한국환경공단 공식 API를 사용하고, 같은 충전소의 여러 충전기는 한 후보로 묶어 최대 출력·통합 상태·가장 최근 상태시각을 표시합니다. 전국 응답은 기본 30분간 메모리에 캐시하며 `APS_EV_CHARGER_REGION_CODES=26,48`처럼 시도 코드를 지정하면 수집 범위를 제한할 수 있습니다.

수소차는 공공데이터포털에서 한국석유관리원 [수소충전소 운영정보](https://www.data.go.kr/data/15133332/openapi.do)와 [수소충전소 실시간정보](https://www.data.go.kr/data/15133338/openapi.do)를 둘 다 활용신청한 뒤 `APS_HYDROGEN_STATION_SERVICE_KEY`를 설정합니다. 어댑터는 공식 명세에 함께 게시된 한국석유관리원 제공기관 주소를 우선 사용하고 공공데이터포털 게이트웨이를 예비 경로로 사용합니다. 관리번호로 두 응답을 결합해 위치·주소·영업 여부·충전기 규격·실시간 운영/POS/혼잡 상태·대기 차량 수·튜브트레일러 압력·갱신시각을 표시하며 기본 5분간 메모리에 캐시합니다. 영업정지·영업마감과 POS 영업중지·점검중·T/T 교체중·기타고장은 `이용 불가`, 혼잡 또는 대기 차량이 있으면 `혼잡`으로 보수적으로 변환합니다. 두 API 중 하나라도 권한이 없거나 장애가 있으면 실시간 상태를 임의로 추정하지 않고 `503`으로 구분합니다. 이 API는 무료·이용허락범위 제한 없음으로 공개되어 있으며, 승인된 실제 계정키 E2E는 2026-09-08에 완료했습니다. 키와 원 API 응답은 파일·Git·로그에 저장하지 않았습니다.

후보의 경로 근접 거리는 도로 우회거리가 아닌 경로선과의 직선거리입니다. 실제 공급자가 설정되지 않은 동력원은 계산 결과를 유지한 채 `공급자 미설정`으로 안내합니다. 검토용 로컬 스냅샷은 `APS_STATION_CATALOG_PATH`로 지정할 수 있으며, 이 설정이 공식 EV·수소 어댑터보다 우선합니다. API 키나 원본 응답은 저장소에 포함하지 않습니다.

현재 키워드 매뉴얼 검색의 재현 가능한 품질 기준은 [매뉴얼 검색 품질 평가 기준](docs/manual-search-evaluation.md)에 기록했습니다. 저장소에 포함된 합성 한국어 질문 세트뿐 아니라, 로컬에 준비한 현대·기아·제네시스 공식 문서 인덱스도 별도 질문 세트로 `Hit@3`, `MRR`, 제조사 출처 격리를 평가할 수 있습니다. PDF 정답은 페이지로, 장마다 페이지가 다시 시작하는 웹 설명서는 공식 장 URL 또는 장 제목으로 판정합니다. 실제 원문은 평가 데이터나 Git에 복제하지 않습니다.

```powershell
cd src/api
uv run python -m app.manual_live_evaluation ../../tests/fixtures/manual-live-evaluation.hkg.v1.json
```

로컬 OpenVINO 임베딩 후보의 설치·실측 결과·라이선스·선택 근거는 [매뉴얼 임베딩 후보 비교](models/manual-embedding-candidates.md)를 참고하세요. 모델 가중치는 Git에 포함하지 않으며 `uv sync --locked --extra embedding`을 실행한 개발 환경의 Hugging Face 캐시에만 저장합니다.

기본 검색 모드는 의도·반대 동작·단위를 구분하는 `keyword`입니다. 검증 서버에서 E5 OpenVINO 의미 검색만 사용하려면 `embedding`, 의도 키워드 검색과 의미 검색을 결합하려면 `hybrid`를 명시합니다.

```powershell
cd src/api
uv sync --locked --extra test --extra embedding
$env:APS_MANUAL_SEARCH_MODE = "embedding"
$env:APS_MANUAL_EMBEDDING_MIN_SCORE = "0.82"
uv run fastapi dev
```

임베딩과 하이브리드 모드는 모델을 처음 검색할 때 지연 로드하고, 문서 내용 지문별 벡터를 메모리에 최대 4개까지 보관합니다. `hybrid`는 키워드 순위에 더 높은 가중치를 두고 의미 검색 순위와 합칩니다. 모델 의존성·가중치·추론 중 하나라도 준비되지 않으면 키워드 검색으로 자동 대체하지 않고 `503 manual_embedding_unavailable`을 반환합니다. 응답의 `search_engine`은 실제 사용한 `keyword-intent-v3`, `openvino-embedding-v1`, `hybrid-intent-openvino-v1` 중 하나를 표시합니다. 키워드 v3는 띄어쓰기·동의어뿐 아니라 열기/닫기, 실제 출발/예약 출발, 충전 출력 단위, 점프 시동, 설정·위치 의도를 구분합니다. `스포츠모드`·`스포츠 모드`·`SPORT 모드`는 같은 드라이브 모드 의도로 처리하며 표나 EV 메뉴보다 스티어링 휠 조작 문장을 우선합니다. 드리프트 모드 진입 질문은 별도 의도로 분리해 양쪽 패들 시프트 조작 근거를 우선합니다. 배포 결정과 실패 폐쇄 원칙은 [ADR-0005](docs/decisions/0005-use-opt-in-openvino-embedding-search.md)를 따릅니다.

기본 매뉴얼 답변은 모델을 사용하지 않는 `extractive` 방식입니다. 검색 1위의 공식 원문에서 질문과 직접 관련된 완결 문장 또는 번호 단계를 최대 3~4개 추려 `[1]` 출처와 함께 보여주고, 아래 `공식 원문 근거`에서 전체 검색 결과를 선택해 펼칠 수 있습니다. 화면은 이를 `공식 원문 핵심 안내`로 표시해 생성형 AI 설명과 구분합니다. 생성형 매뉴얼 답변은 기본적으로 꺼져 있으며, 검토한 OpenVINO GenAI 모델을 로컬에 별도로 준비한 검증 환경에서만 다음과 같이 활성화합니다. 저장소에는 모델 가중치나 제조사 PDF를 넣지 않습니다.

```powershell
cd src/api
uv sync --locked --extra test --extra generation
$env:APS_MANUAL_ANSWER_MODE = "openvino"
$env:APS_MANUAL_GENERATION_MODEL_PATH = "C:\models\reviewed-openvino-llm"
$env:APS_MANUAL_GENERATION_DEVICE = "CPU"
uv run fastapi dev
```

생성 답변은 검색된 1위 출처만 입력받고, 서버가 인용 번호·근거에 없는 숫자·최소 어휘 중첩을 검증한 뒤 인용 표기를 직접 붙입니다. 모델 로드·추론이 실패하거나 출력이 검증을 통과하지 못하면 출처 목록 안내로 자동 대체하지 않고 `503`으로 실패 폐쇄합니다. 응답의 `answer_engine`과 `citations`에서 실제 답변 경로와 사용한 출처 번호를 확인할 수 있습니다. 화면은 검증된 생성 답변을 `AI 설명`으로 먼저 표시하고 제조사 링크·페이지·발췌문은 `공식 원문 근거`에서 선택해 펼치도록 구분합니다. 상세 결정은 [ADR-0007](docs/decisions/0007-use-opt-in-grounded-openvino-manual-answers.md)을 따릅니다.

로컬 CPU 파일럿은 고정 리비전의 `OpenVINO/Qwen2.5-1.5B-Instruct-int4-ov`을 사용해 합성 한국어 근거 8문항을 각 3회 측정했습니다. 합성 24회는 모두 통과했지만, 이후 넥쏘·ELECTRIFIED GV70 실제 문서 대표 질문 3개에서는 1개만 통과했습니다. 실문서 탐색의 첫 호출은 약 34.90초, 이후 호출은 약 8~9초였습니다. 모델 선택 근거·측정 결과·한계는 [매뉴얼 생성 답변 모델 CPU 파일럿](models/manual-generation-candidates.md)에 기록했습니다. 현재 1.5B 후보는 실제 설명서를 안정적으로 요약하지 못하므로 생성형 모드는 선택형으로 유지하고, 운영 기본값은 비생성 `extractive`입니다.

현재 백엔드는 차량 프로필 CRUD·활성 차량 전환, 차량별 매뉴얼 준비 상태·재시도, 승인된 PDF/TXT 추출·청크 저장과 출처 검색을 제공합니다. 프런트엔드의 공식 취급설명서 링크는 제조사 원문을 새 탭으로 열며, `ready` 상태에서는 현재 차량 문서만 질문할 수 있습니다. 정확한 문서가 없거나 준비 중이면 `409`, 준비 실패나 상태·인덱스 불일치는 `503`으로 구분합니다. 기본 검색 응답은 원문 핵심 발췌와 문서명·페이지·공식 원문 URL·발췌문이며, 위 선택 모드에서만 검증된 생성 답변을 추가합니다.

쉐보레·KGM의 모델별 장 목록은 제조사 사이트를 자동 수집하지 않습니다. 서버 관리자가 이용 조건과 정확한 차명·연식·세대를 확인한 뒤 `APS_MANUAL_SOURCE_DIR`의 `adapter-manifest.json`에 승인한 매핑만 조회합니다. API 모드의 취급설명서 화면에서 정확한 단일 매핑을 프로필에 연결하면 결정적인 문서 키의 `pending` 작업이 생성됩니다. 운영자가 같은 키의 `manifest.json`과 승인된 로컬 장별 파일을 준비해야 실제 검색 인덱스가 만들어지며, 이미지 사용 권한을 확인하기 전까지 해당 프로필에는 제조사 이미지를 저장하지 않습니다. 같은 차명·연식에 여러 세대가 있으면 승인 manifest의 세대·문서명·출처 확인일만 후보로 표시하고, 사용자가 한 세대를 명시적으로 고른 뒤 연결합니다. 첫 후보를 자동 선택하거나 다른 연식 문서로 대체하지 않습니다. 상세 형식과 정책은 [ADR-0004](docs/decisions/0004-use-approved-manual-adapter-catalog.md)와 [ADR-0006](docs/decisions/0006-ingest-operator-approved-manual-chapter-bundles.md)을 참고하세요.

공식 근거를 교차 확인한 최소 파일럿은 [쉐보레·KGM 승인 매뉴얼 파일럿 카탈로그](docs/manual-adapter-pilot-catalog.md)에 기록했습니다. 로컬에서는 문서의 명령으로 검토용 JSON을 Git 제외 디렉터리에 복사해 `2025 트랙스 크로스오버`와 `2023 토레스(J100)`의 정확 매핑만 시험할 수 있습니다. 제조사 PDF와 원 API 응답은 포함하지 않습니다.

## 다음 진행 순서

1. **오피넷 주유소 실제 공급자 연결**: 일반 API 키를 발급받아 공식 반경 검색·상세정보를 연결합니다. 공개 제품코드로 확인되는 보통휘발유·고급휘발유·자동차경유만 `취급 확인`으로 표시하고, 별도 코드가 없는 초고급 휘발유·하이세탄 경유는 추정하지 않습니다.
2. **NAVER Maps Dynamic Map 라이브 검증**: 브라우저 Client ID를 별도로 연결해 실제 좌표 경로와 지도 표시를 비교하고 계정 한도·비용을 확인하되 서버 Secret은 서버 환경변수에만 보관
3. **제조사 매뉴얼 어댑터 확장**: [Issue #17](https://github.com/KIMDOHONG/auto-progress-squad/issues/17)의 공통 계약과 BMW VIN 보호 경계 뒤에, 사용 조건이 확인된 제조사부터 정확한 모델·연식 식별을 연결
4. **생성 품질 후보 개선**: 기본 비생성 원문 핵심 안내는 적용했으며, 넥쏘·ELECTRIFIED GV70 실문서 3문항 탐색에서 1.5B 후보가 1/3만 통과했으므로 더 큰 지시 모델을 같은 출처 격리 조건과 확장 질문 세트로 비교
5. **리콜 실제 API 연결**: [Issue #19](https://github.com/KIMDOHONG/auto-progress-squad/issues/19)의 공급자 계약에 승인받은 자동차리콜센터 API를 연결

후속 개선사항은 구현 범위가 섞이지 않도록 다음 GitHub Issue에서 관리합니다.

- [Issue #17](https://github.com/KIMDOHONG/auto-progress-squad/issues/17): BMW·쉐보레·KGM 공식 매뉴얼 어댑터, BMW 차량명·연식 동적 표시와 공식 이미지 대체 규칙
- [Issue #20](https://github.com/KIMDOHONG/auto-progress-squad/issues/20): 코파일럿 차량 등록 문장에서 프로필 별명 분리
- [Issue #22](https://github.com/KIMDOHONG/auto-progress-squad/issues/22): 모바일 코파일럿 플로팅 버튼·부분 화면 채팅 패널·최신 메시지 자동 스크롤·하단 메뉴 균등 배치·채팅 버블과 차량 이미지 폭 개선
- **경로 지도 종횡비 보정**: Dynamic Map 미연결 시 표시하는 좌표 기반 SVG가 화면 폭에 따라 상하로 눌리거나 늘어나지 않도록 위도 보정과 동일 축척 투영을 적용하고, 데스크톱·모바일 화면에서 경로 형상을 비교 검증

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
