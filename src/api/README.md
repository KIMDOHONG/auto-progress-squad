# Backend API

FastAPI와 SQLite 기반 백엔드입니다. 차량 프로필, 승인된 로컬 매뉴얼의 추출·청크 저장·출처 검색과 리콜 API 계약을 제공합니다. 생성형 매뉴얼 답변은 검증 환경에서만 선택적으로 연결합니다. 리콜은 자동차리콜센터 공급자 계약만 구현했으며 승인된 실제 HTTP 공급자는 아직 연결하지 않습니다.

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
| `APS_MANUAL_ANSWER_MODE` | `source-list` | `source-list` 또는 선택형 `openvino` 답변 |
| `APS_MANUAL_GENERATION_MODEL_PATH` | 없음 | 운영자가 검토한 로컬 OpenVINO GenAI 모델 경로 |
| `APS_MANUAL_GENERATION_DEVICE` | `CPU` | OpenVINO 추론 장치 |
| `APS_MANUAL_GENERATION_MAX_NEW_TOKENS` | `256` | 생성 출력 토큰 상한 |
| `APS_MANUAL_GROUNDING_MIN_TOKEN_OVERLAP` | `0.55` | claim과 인용 발췌문의 최소 어휘 중첩 비율 |

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

매뉴얼 작업자는 `uv run python -m app.manual_worker`로 실행합니다. manifest에 승인된 공식 HTTPS 출처와 서버 디렉터리 내부 파일만 처리하며, 제조사 PDF를 저장소에 커밋하거나 브라우저로 복제하지 않습니다. 리콜 공급자가 없을 때의 `503`은 미연동 상태를 성공인 것처럼 보이지 않도록 의도적으로 실패 폐쇄한 상태입니다. 공급자 계약과 이용 경계는 [ADR-0008](../../docs/decisions/0008-use-approved-car-recall-center-provider.md)을 따릅니다.

## 외부 라이브러리와 데이터 경계

- 잠금 파일 기준 `pypdf 6.16.2`(BSD-3-Clause)는 서버에서 승인된 PDF의 텍스트를 추출할 때만 사용합니다. 문서 다운로드, 이용 허가 판단, 답변 생성은 수행하지 않습니다.
- PDF/TXT 파일과 공식 원문 URL은 서버 관리자가 manifest로 제공해야 합니다. 작업자는 허용된 공식 도메인과 `APS_MANUAL_SOURCE_DIR` 내부 경로만 처리합니다.
- 쉐보레·KGM 매핑은 같은 디렉터리의 `adapter-manifest.json`에 별도로 둡니다. 항목에는 `manufacturer_id`, `model`, `model_year`, `generation`, `manual_title`, `official_url`, `source_checked_at`와 `chapters`의 `title`·`url`이 필요합니다. 제조사 API 응답이나 PDF를 저장소에 커밋하지 말고, 이용 조건과 정확한 차량 대응을 검토한 링크만 운영 서버에 배치합니다.
- 같은 차명·연식에 승인된 세대가 둘 이상이면 조회·연결 API는 `409 manual_generation_required`와 `generation`, `manual_title`, `source_checked_at` 후보만 반환합니다. 클라이언트가 사용자의 세대 선택을 받은 뒤 `generation`을 다시 보내야 하며, 오류 응답에는 공식 URL이나 PDF URL을 포함하지 않습니다.
- 제조사 문서는 소스 저장소나 GitHub Pages에 포함하지 않으며, 실제 운영 전에는 각 제조사의 이용 조건과 재사용 범위를 별도로 확인해야 합니다.
- OpenVINO GenAI 답변은 `uv sync --locked --extra generation`으로 선택 설치합니다. 모델 가중치는 포함하지 않으며, 실제 검토 모델 경로와 `APS_MANUAL_ANSWER_MODE=openvino`를 모두 지정한 환경에서만 지연 로드합니다.
- 잠금 파일의 `openvino-genai 2026.3.1.0` 실행 라이브러리는 Apache-2.0이며, 이 라이선스가 별도로 준비하는 모델 가중치의 이용 조건까지 허가하지는 않습니다.
- 모델의 구조화 JSON은 사실성 보장이 아니므로 서버가 인용 범위·중복, 근거에 없는 숫자와 최소 어휘 중첩을 다시 검증하고 인용 표기를 직접 렌더링합니다. 생성 또는 검증 실패는 `503`으로 반환하며 기본 출처 안내로 숨기지 않습니다.
- 로컬 모델 다운로드와 CPU 재현 평가는 `uv sync --locked --extra generation-evaluation` 후 `python -m app.manual_generation_evaluation`을 사용합니다. 현재 파일럿의 모델 ID·고정 리비전·SHA-256·측정 결과는 `models/manual-generation-candidates.md`를 참고하세요.
