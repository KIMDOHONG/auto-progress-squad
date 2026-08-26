# Backend API

FastAPI와 SQLite 기반 백엔드 기반입니다. 현재 단계에서는 차량 프로필 저장 구조와 매뉴얼·리콜 API 계약을 제공하며 실제 RAG와 외부 리콜 데이터는 연결하지 않습니다.

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

## 현재 API

| 경로 | 상태 |
| --- | --- |
| `GET /api/v1/health` | 실제 상태 확인 |
| `GET /api/v1/vehicles` | SQLite 차량 목록 조회 |
| `POST /api/v1/manual/search` | 계약만 제공, 현재 `503` |
| `GET /api/v1/vehicles/{vehicle_id}/recalls` | 계약만 제공, 현재 `503` |

`503`은 오류가 아니라 성공인 것처럼 보이지 않도록 의도적으로 실패 폐쇄한 상태입니다.
