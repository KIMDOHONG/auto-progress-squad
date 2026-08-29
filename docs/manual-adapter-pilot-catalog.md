# 쉐보레·KGM 승인 매뉴얼 파일럿 카탈로그

- 확인일: 2026-08-29
- 관련 이슈: #17
- 상태: 운영자 검토용 파일럿 2건

## 포함 범위

`docs/examples/adapter-manifest.pilot.json`에는 공식 원문에서 차명·세대·연식 근거와 장별 PDF를 함께 확인한 다음 두 매핑만 포함합니다.

| 제조사 | 프로필의 정확한 차명 | 연식 | 세대 | 공식 설명서 |
| --- | --- | ---: | --- | --- |
| 쉐보레 | 트랙스 크로스오버 | 2025 | TRAX CROSSOVER (2023년 국내 출시 세대) | 쉐보레 `TRAX CROSSOVER` 차량취급설명서 |
| KGM | 토레스 | 2023 | J100 | 토레스 - 취급설명서 (2022.07) |

차량 프로필의 차명과 연식이 표의 값과 정확히 일치할 때만 연결합니다. `TRAX CROSSOVER`, `더 뉴 토레스`, 2024년형처럼 다른 문자열이나 연식은 같은 차량으로 추정하지 않습니다.

## 확인 근거

### 쉐보레 트랙스 크로스오버 2025

- 쉐보레 공식 [TRAX CROSSOVER 차량취급설명서](https://www.chevrolet.co.kr/owner-manuals/trax-crossover)에서 모델 전용 경로와 14개 장별 PDF를 확인했습니다.
- 공식 보증서 파일명은 `25Trax crossover`이고, 쉐보레 공식 뉴스룸의 [2025년형 트랙스 크로스오버 출시 공지](https://news.chevrolet.co.kr/ko/chevrolet/newsroom.detail.html/Pages/news/kr/ko/2024/mar/0314_New_Trax.html)는 2024-03-14에 2025년형 출시를 명시합니다.
- 이 근거는 2025년형 한 건에만 사용하며 2024·2026년형으로 확대하지 않습니다.

### KGM 토레스 2023 J100

- KGM 공식 [취급 설명서](https://www.kg-mobility.com/sr/update-download/download-center/instruction-manual)의 이전 모델 목록에서 `토레스 - 취급설명서 (2022.07)`와 9개 장별 PDF를 확인했습니다.
- 공식 PDF 내부 원본명은 `J100`이며 문서 제작 시점은 2022년 6~9월입니다. KGM 공식 블로그의 [토레스 역사](https://allways.kg-mobility.com/kgm-%ED%86%A0%EB%A0%88%EC%8A%A4%EC%97%AD%EC%82%AC/)는 2022년 7월 출시를 기록하고, [KGM 인증중고차](https://certified.kg-mobility.com/listPage)는 해당 초기형 토레스를 2023년형으로 표시합니다.
- `2022.07`은 설명서 발행 시점이지 차량 연식이 아닙니다. 위 근거가 함께 확인된 2023년형 J100에만 사용합니다.

## 로컬 활성화

제조사 PDF나 제조사 API 응답은 복사하지 않습니다. 예시 JSON만 서버의 Git 제외 디렉터리에 복사합니다.

```powershell
New-Item -ItemType Directory -Force src/api/data/manuals | Out-Null
Copy-Item docs/examples/adapter-manifest.pilot.json src/api/data/manuals/adapter-manifest.json
```

백엔드 실행 후 정확 매핑을 확인합니다.

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/manual-adapters/kgm/resolve `
  -ContentType application/json `
  -Body '{"model":"토레스","model_year":2023,"generation":"J100"}'
```

인접 연식이나 다른 세대는 `404 manual_mapping_not_found`가 정상입니다.

## 장별 파일 수집

정확한 승인 매핑을 차량에 연결하면 API 모드에서 해당 차량의 매뉴얼 준비 상태가 `pending`이 됩니다. 앱은 제조사 PDF를 자동으로 내려받지 않습니다. 운영자가 이용 조건을 확인한 뒤 각 장 파일을 `APS_MANUAL_SOURCE_DIR` 안에 직접 준비하고, [장별 매뉴얼 manifest 예시](examples/manual-manifest.chapter-bundle.example.json)를 `manifest.json`의 출발점으로 사용해야 합니다.

예시의 `document_key`는 `2023 토레스(J100)` 승인 매핑에만 해당합니다. 실제 작업 전 `GET /api/v1/vehicles/{vehicle_id}/manual-ingestion` 응답의 키와 정확히 같은지 확인합니다. 작업이 완료되면 각 검색 결과는 전체 문서의 대표 URL 대신 근거가 나온 장의 제목·페이지·공식 PDF URL을 반환합니다.

## 미완료 범위

- 쉐보레 페이지는 차량 연식을 선택값으로 제공하지 않으므로 다른 차종·연식은 별도 공식 근거가 필요합니다.
- KGM의 설명서 발행월을 차량 연식으로 자동 변환하지 않습니다.
- 제조사 페이지를 주기적으로 수집하지 않으며 PDF와 원 API 응답을 저장소에 커밋하지 않습니다.
- 이 저장소의 장별 manifest는 로컬 파일 배치 형식만 설명하며, 원문 다운로드·복제 권한을 부여하지 않습니다.
- 실제 서비스에 배치하기 전 운영자가 제조사 이용 조건과 링크 상태를 다시 확인해야 합니다.
