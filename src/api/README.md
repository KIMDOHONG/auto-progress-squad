# Backend API

FastAPI와 SQLite 기반 백엔드입니다. 차량 프로필, 승인된 로컬 매뉴얼의 추출·청크 저장·출처 검색, 리콜 API 계약, 선택형 실제 경로 조회와 경로 주변 충전·주유소 공통 계약을 제공합니다. 생성형 매뉴얼 답변은 검증 환경에서만 선택적으로 연결합니다. 한국환경공단 전기차 충전소 HTTP 공급자를 선택적으로 연결하며, 수소·주유소와 리콜의 실제 공급자는 아직 연결하지 않습니다.

## 실행

```powershell
uv sync --extra test
uv run fastapi dev
```

- Swagger UI: `http://127.0.0.1:8000/docs`
- 상태 확인: `GET http://127.0.0.1:8000/api/v1/health`

## 테스트

```powershell
uv run pytest
```

## 환경 변수

| 이름 | 기본값 | 설명 |
| --- | --- | --- |
| `APS_DATABASE_PATH` | `src/api/data/auto_progress.db` | SQLite 파일 경로 |
| `APS_CORS_ORIGINS` | 로컬 Vite 주소와 GitHub Pages origin | 쉼표로 구분한 허용 origin |
| `APS_MANUAL_SOURCE_DIR` | `src/api/data/manuals` | 승인된 PDF/TXT와 `manifest.json` 디렉터리 |
| `APS_MANUAL_SEARCH_MODE` | `keyword` | `keyword` 또는 선택형 `embedding` 검색 |
| `APS_MANUAL_ANSWER_MODE` | `extractive` | 기본 원문 핵심 발췌, `source-list`, 또는 선택형 `openvino` 답변 |
| `APS_MANUAL_GENERATION_MODEL_PATH` | 없음 | 운영자가 검토한 로컬 OpenVINO GenAI 모델 경로 |
| `APS_MANUAL_GENERATION_DEVICE` | `CPU` | OpenVINO 추론 장치 |
| `APS_MANUAL_GENERATION_MAX_NEW_TOKENS` | `160` | 생성 출력 토큰 상한 |
| `APS_MANUAL_GROUNDING_MIN_TOKEN_OVERLAP` | `0.55` | claim과 인용 발췌문의 최소 어휘 중첩 비율 |
| `APS_NAVER_MAPS_CLIENT_ID` | 없음 | NAVER Cloud Maps 서버 인증 Client ID |
| `APS_NAVER_MAPS_CLIENT_SECRET` | 없음 | NAVER Cloud Maps 서버 인증 Client Secret |
| `APS_NAVER_MAPS_BROWSER_CLIENT_ID` | 없음 | Dynamic Map 브라우저 공개 Client ID; 콘솔에서 허용 Web 서비스 URL 제한 필요 |
| `APS_NAVER_MAPS_TIMEOUT_SECONDS` | `5` | Geocoding·Reverse Geocoding·Directions 5 요청 제한 시간(초) |
| `APS_STATION_CATALOG_PATH` | 없음 | 출처·조회시각이 포함된 로컬 전기·수소·주유소 정규 JSON 스냅샷 경로 |
| `APS_EV_CHARGER_SERVICE_KEY` | 없음 | 공공데이터포털에서 발급받은 한국환경공단 전기차 충전소 API 서비스키 |
| `APS_EV_CHARGER_TIMEOUT_SECONDS` | `10` | 전기차 충전소 API 요청 제한 시간(초) |
| `APS_EV_CHARGER_CACHE_TTL_SECONDS` | `1800` | 전국 또는 지정 시도 충전소 응답의 메모리 캐시 시간(초) |
| `APS_EV_CHARGER_PAGE_SIZE` | `9999` | 공식 API 한 번당 요청 건수(10~9999) |
| `APS_EV_CHARGER_MAX_PAGES` | `100` | 비정상 페이지 반복을 차단하는 최대 페이지 수 |
| `APS_EV_CHARGER_REGION_CODES` | 없음 | 선택형 쉼표 구분 시도 코드(예: 부산 `26`, 경남 `48`); 없으면 전국 |

## 현재 API

| 경로 | 상태 |
| --- | --- |
| `GET /api/v1/health` | 실제 상태 확인 |
| `GET /api/v1/vehicles` | SQLite 차량 목록 조회 |
| `POST /api/v1/vehicles` | 차량 등록, 최대 3대 |
| `PUT /api/v1/vehicles/{vehicle_id}` | 차량 정보 수정 |
| `PUT /api/v1/vehicles/{vehicle_id}/active` | 활성 차량 전환 |
| `DELETE /api/v1/vehicles/{vehicle_id}` | 차량 삭제, 마지막 1대 보호 |
| `GET /api/v1/vehicles/{vehicle_id}/manual-ingestion` | 차량별 문서 준비 상태 |
| `POST /api/v1/vehicles/{vehicle_id}/manual-ingestion/retry` | 실패 작업을 `pending`으로 재설정 |
| `POST /api/v1/manual/search` | `ready` 차량 문서의 출처 검색 |
| `GET /api/v1/manual-adapters` | 제조사별 식별·연동·저장 정책 조회 |
| `POST /api/v1/manual-adapters/{adapter_id}/resolve` | 승인된 쉐보레·KGM 모델·연식·세대 매핑 조회 |
| `POST /api/v1/vehicles/{vehicle_id}/manual-adapters/{adapter_id}` | 정확한 승인 매핑을 차량 프로필에 연결 |
| `GET /api/v1/vehicles/{vehicle_id}/recalls` | 자동차리콜센터 공급자 미설정 시 `503`; 승인 공급자 후보 중 정확한 정규 차량 키만 반환하고 정상·0건·장애 상태 구분 |
| `POST /api/v1/planner/location/resolve` | 입력 주소를 정규 주소·좌표로 확인 |
| `POST /api/v1/planner/location/reverse` | GPS 좌표를 도로명 주소로 확인 |
| `GET /api/v1/planner/map-config` | Dynamic Map용 공개 Client ID의 설정 여부 반환; 서버 Secret은 반환하지 않음 |
| `POST /api/v1/planner/route` | 확인된 주소 2개를 Geocoding한 뒤 Directions 5의 `trafast`·`traoptimal`·`traavoidtoll` 거리·시간·통행료·좌표 경로 반환; 공급자 미설정·주소 불일치·상류 장애 구분 |
| `POST /api/v1/planner/stations` | 선택 경로 좌표에서 설정 반경 안의 전기·수소·주유소 후보를 근접도순으로 반환; 공급자 미설정·0건·장애와 지정연료 미확인 상태 구분 |

매뉴얼 작업자는 `uv run python -m app.manual_worker`로 실행합니다. manifest에 승인된 공식 HTTPS 출처와 서버 디렉터리 내부 파일만 처리하며, 제조사 PDF를 저장소에 커밋하거나 브라우저로 복제하지 않습니다. 리콜 공급자가 없을 때의 `503`은 미연동 상태를 성공인 것처럼 보이지 않도록 의도적으로 실패 폐쇄한 상태입니다. 공급자 계약과 이용 경계는 [ADR-0008](../../docs/decisions/0008-use-approved-car-recall-center-provider.md)을 따릅니다.

## 외부 라이브러리와 데이터 경계

- 잠금 파일 기준 `pypdf 6.16.2`(BSD-3-Clause)는 서버에서 승인된 PDF의 텍스트를 추출할 때만 사용합니다. 문서 다운로드, 이용 허가 판단, 답변 생성은 수행하지 않습니다.
- NAVER Maps 서버 Client ID와 Client Secret은 FastAPI 프로세스 환경변수에서만 읽고 프런트엔드 응답·로그·저장소에 노출하지 않습니다. Dynamic Map용 별도 Client ID만 지도 설정 응답으로 브라우저에 전달하며, 이는 공개 식별자이므로 NAVER Cloud 콘솔에서 허용 Web 서비스 URL을 제한해야 합니다. Geocoding·Reverse Geocoding·Directions 5가 미설정되거나 실패하면 직접 입력 거리 계산으로 명시적으로 복귀합니다. 실제 계정 키를 사용한 라이브 E2E와 과금 확인은 아직 완료하지 않았습니다.
- 충전·주유소 공통 계약은 검토용 `APS_STATION_CATALOG_PATH` 정규 JSON 스냅샷을 우선하고, 스냅샷이 없고 `APS_EV_CHARGER_SERVICE_KEY`가 있으면 [한국환경공단 전기자동차 충전소 정보](https://www.data.go.kr/data/15013115/standard.do)를 사용합니다. 같은 충전소의 충전기 행을 하나로 묶고 기본 30분 캐시한 뒤 기존 경로 반경 비교에 전달합니다. 경로와 후보 좌표의 근접도는 실제 도로 우회거리나 우회시간이 아니며 대기시간도 포함하지 않습니다. 수소·주유소는 실제 공급자 미설정 상태입니다. 데이터 형식과 실패 경계는 [ADR-0010](../../docs/decisions/0010-normalize-local-energy-station-snapshots.md)을 따릅니다.
- PDF/TXT 파일과 공식 원문 URL은 서버 관리자가 manifest로 제공해야 합니다. 작업자는 허용된 공식 도메인과 `APS_MANUAL_SOURCE_DIR` 내부 경로만 처리합니다.
- 쉐보레·KGM 매핑은 같은 디렉터리의 `adapter-manifest.json`에 별도로 둡니다. 항목에는 `manufacturer_id`, `model`, `model_year`, `generation`, `manual_title`, `official_url`, `source_checked_at`와 `chapters`의 `title`·`url`이 필요합니다. 제조사 API 응답이나 PDF를 저장소에 커밋하지 말고, 이용 조건과 정확한 차량 대응을 검토한 링크만 운영 서버에 배치합니다.
- 같은 차명·연식에 승인된 세대가 둘 이상이면 조회·연결 API는 `409 manual_generation_required`와 `generation`, `manual_title`, `source_checked_at` 후보만 반환합니다. 클라이언트가 사용자의 세대 선택을 받은 뒤 `generation`을 다시 보내야 하며, 오류 응답에는 공식 URL이나 PDF URL을 포함하지 않습니다.
- 제조사 문서는 소스 저장소나 GitHub Pages에 포함하지 않으며, 실제 운영 전에는 각 제조사의 이용 조건과 재사용 범위를 별도로 확인해야 합니다.
- 기본 `extractive` 답변은 검색 1위의 공식 원문에서 질문과 직접 관련된 완결 문장 또는 번호 단계를 최대 3~4개 추립니다. 문장을 생성하거나 바꾸어 쓰지 않으며, 모든 검색 결과는 `공식 원문 근거`에 그대로 남습니다. 안전하게 추출할 수 없으면 `source-list-v1` 안내만 반환합니다.
- OpenVINO GenAI 답변은 `uv sync --locked --extra generation`으로 선택 설치합니다. 모델 가중치는 포함하지 않으며, 실제 검토 모델 경로와 `APS_MANUAL_ANSWER_MODE=openvino`를 모두 지정한 환경에서만 지연 로드합니다.
- 잠금 파일의 `openvino-genai 2026.3.1.0` 실행 라이브러리는 Apache-2.0이며, 이 라이선스가 별도로 준비하는 모델 가중치의 이용 조건까지 허가하지는 않습니다.
- 모델의 구조화 JSON은 사실성 보장이 아니므로 서버가 인용 범위·중복, 근거에 없는 숫자와 최소 어휘 중첩을 다시 검증하고 인용 표기를 직접 렌더링합니다. 생성 또는 검증 실패는 `503`으로 반환하며 기본 출처 안내로 숨기지 않습니다.
- 로컬 모델 다운로드와 CPU 재현 평가는 `uv sync --locked --extra generation-evaluation` 후 `python -m app.manual_generation_evaluation`을 사용합니다. 현재 파일럿의 모델 ID·고정 리비전·SHA-256·측정 결과는 `models/manual-generation-candidates.md`를 참고하세요.
