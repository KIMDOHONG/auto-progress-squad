# 매뉴얼 생성 답변 모델 후보와 CPU 파일럿

- 측정일: 2026-08-30
- 관련 이슈: #18
- 실행 장치: Intel Core i5-1135G7, 4코어·8스레드, RAM 15.68GB, Windows 11
- 평가 데이터: `tests/fixtures/manual-generation-evaluation.v1.json`

## 판단

`OpenVINO/Qwen2.5-1.5B-Instruct-int4-ov`의 고정 리비전 `748d8cc119574c982192d9473e77bcf68273dd5a`을 로컬 CPU 파일럿으로 선택합니다.

- OpenVINO 공식 변환본이며 OpenVINO IR과 INT4 대칭 압축을 이미 적용했습니다.
- 원 모델과 변환 모델은 Apache-2.0이고 모델 카드에 한국어가 지원 언어로 명시되어 있습니다.
- 원 모델은 지시 이행과 JSON 구조화 출력 개선을 명시하며, 현재 서버의 구조화 claim 계약과 맞습니다.
- 로컬 파일은 892.64MB로, 같은 계열 7B INT4 약 4.48GB나 1.5B FP16 약 3.11GB보다 현재 16GB 노트북의 파일럿에 적합합니다.

이 판단은 모델 가중치의 일반적인 정확도나 실제 차량 정비 안전성을 승인하는 결정이 아닙니다. 서버는 계속 모델 출력을 신뢰하지 않고 인용·수치·어휘 근거를 검증합니다.

## 로컬 준비

모델은 Git 저장소 밖의 전용 캐시에만 받습니다. 아래 경로는 예시이며 저장소에 모델 파일을 복사하지 않습니다.

```powershell
cd src/api
uv sync --locked --extra test --extra generation-evaluation

$modelCache = "C:\Users\dohon\.cache\auto-progress-squad\models\qwen2.5-1.5b-instruct-int4-ov-748d8cc"
uv run hf download OpenVINO/Qwen2.5-1.5B-Instruct-int4-ov `
  --revision 748d8cc119574c982192d9473e77bcf68273dd5a `
  --local-dir $modelCache
```

측정한 `openvino_model.bin` SHA-256은 다음과 같습니다.

```text
c06a0c7346e6cad8dea0cdf3f0e11f4f5d3dbc49fa79366b867d17cba7a1c73d
```

## 재현 명령

```powershell
$modelCache = "C:\Users\dohon\.cache\auto-progress-squad\models\qwen2.5-1.5b-instruct-int4-ov-748d8cc"
uv run python -m app.manual_generation_evaluation `
  ../../tests/fixtures/manual-generation-evaluation.v1.json `
  --model-path $modelCache `
  --repeats 3
```

평가기는 첫 호출에 모델 지연 로드를 포함하고, 이후 호출의 평균·p50·p95와 프로세스 RSS 최고점을 출력합니다. 각 답변은 실제 API와 같은 서버 검증기를 통과해야 성공하며, `[1]` 인용과 사례별 필수 정보도 별도로 확인합니다.

## 측정 결과

| 항목 | 결과 |
| --- | ---: |
| 합성 한국어 근거 문항 | 8개 |
| 문항별 반복 | 3회 |
| 전체 생성·검증 | 24/24 통과 |
| 생성 수락률 | 1.0000 |
| 인용 정확도 | 1.0000 |
| 필수 정보 정확도 | 1.0000 |
| 첫 호출(모델 로드 포함) | 17,369.76ms |
| 웜 평균 | 2,797.22ms |
| 웜 p50 | 2,753.58ms |
| 웜 p95 | 3,196.82ms |
| 프로세스 RSS 기준선 | 30.99MB |
| 프로세스 RSS 최고점 | 2,097.12MB |
| 프로세스 RSS 증가량 | 2,066.13MB |

초기 탐색에서 질문에만 `12V`, `빨간`, `집에서` 같은 근거 밖 조건을 넣었을 때 생성 답변은 서버의 숫자 또는 어휘 근거 검증에서 차단됐습니다. 이 탐색 결과는 고정 평가 세트의 품질 지표에 섞지 않으며, 위조 인용·지원되지 않는 숫자·근거 이탈의 결정적 회귀 검증은 `test_manual_grounded_answer.py`에서 담당합니다.

## 해석과 미완료 범위

- 현재 결과는 제조사 원문을 복제하지 않은 작은 합성 문장 8개에 대한 기능·성능 측정입니다.
- 24회가 모두 같은 결과였어도 실제 차량 설명서의 긴 문맥, 여러 출처, 표, 페이지 오류와 다양한 한국어 질문을 대표하지 않습니다.
- 로컬 승인 디렉터리에 제조사 원문 파일이 없으므로 승인 실제 문서 E2E는 아직 수행하지 않았습니다.
- 첫 호출 약 17초는 사용자 요청 경로에서 그대로 기다리기에는 길어 서버 시작 후 명시적인 예열이나 비동기 준비 상태가 필요합니다.
- 실제 문서 평가와 운영 정책이 끝날 때까지 기본값은 `source-list`이며, 파일럿 모델을 자동 다운로드하거나 GitHub Pages에서 실행하지 않습니다.

