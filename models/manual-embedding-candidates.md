# 매뉴얼 임베딩 후보 비교

- 관련 이슈: #18
- 측정일: 2026-08-29
- 상태: 다음 통합 후보 선정, 서비스 검색에는 아직 미적용

## 후보와 사용 조건

| 후보 | 공식 모델 카드 | 라이선스 | 언어·차원 | 측정 파일 | 로컬 캐시 |
| --- | --- | --- | --- | --- | ---: |
| `intfloat/multilingual-e5-small` | [Hugging Face](https://huggingface.co/intfloat/multilingual-e5-small) | MIT | 94개 언어, 384차원 | OpenVINO FP32 | 465.4MB |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | [Hugging Face](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2) | Apache-2.0 | 50개 언어, 384차원 | OpenVINO INT8 | 122.8MB |

두 모델 카드 모두 한국어를 지원 언어에 포함합니다. E5는 모델 카드 권장 방식대로 질문에 `query: `, 문서에 `passage: ` 접두어를 붙였습니다. MiniLM은 접두어를 사용하지 않았습니다.

[Sentence Transformers의 OpenVINO 안내](https://sbert.net/docs/sentence_transformer/usage/efficiency.html)는 Intel CPU에서 OpenVINO와 INT8 후보를 실제 데이터로 비교하라고 권장합니다. 이 저장소도 공개 벤치마크 수치를 그대로 적용하지 않고 로컬 질문 세트에서 직접 측정합니다.

## 측정 환경

- CPU: Intel Core i5-1135G7, 4코어·8스레드
- RAM: 15.7GB
- OS: Windows 11 `10.0.26200`
- Python: 3.12.13
- Sentence Transformers: 6.0.0
- OpenVINO: 2026.3.1
- Transformers: 5.5.4
- 데이터: 합성 한국어 청크 8개·질문 8개
- 검색: 정규화 384차원 벡터의 cosine과 같은 내적, 상위 3개
- 지연시간: 모델 캐시가 준비된 상태에서 질문 8개를 각각 20회 실행

## 측정 결과

| 검색 | Hit@3 | MRR | 캐시 후 로드 | 워밍업 | 문서 8개 배치 | 질문 평균 | 질문 P95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 기존 키워드 | 0.7500 | 0.7500 | 해당 없음 | 해당 없음 | 해당 없음 | 미측정 | 미측정 |
| MiniLM-L12 INT8 | 0.8750 | 0.8125 | 8.18초 | 99.84ms | 35.20ms | 4.22ms | 5.89ms |
| multilingual-e5-small FP32 | 1.0000 | 1.0000 | 8.71초 | 24.32ms | 45.99ms | 5.09ms | 6.96ms |

MiniLM은 `앞유리 닦개 교체 방법`에서 와이퍼 청크를 상위 3개에 넣지 못했고, 브레이크 경고 질문은 정답이 2순위였습니다. E5-small은 현재 8문항의 정답을 모두 1순위로 반환했습니다.

## 결정

다음 서버 통합 실험의 기본 후보는 `intfloat/multilingual-e5-small`입니다.

- MiniLM보다 질문 평균이 약 0.87ms 느리지만 현재 평가 세트의 정확도 차이가 큽니다.
- 모델 리비전은 `614241f622f53c4eeff9890bdc4f31cfecc418b3`으로 고정합니다.
- 가중치는 Hugging Face 캐시에만 내려받으며 Git에 커밋하지 않습니다.
- 모델을 받지 않았거나 로드에 실패하면 기존 키워드 검색으로 조용히 성공 처리하지 않고, 다음 통합 단계에서 명시적 상태를 정의합니다.

저장공간이 제한된 배포 환경에서는 122.8MB MiniLM INT8을 대안으로 다시 평가할 수 있습니다. 그러나 합성 8문항 결과만으로 E5를 실제 서비스 기본값으로 확정하지 않으며, 승인된 실제 문서와 확장 질문 세트가 필요합니다.

## 재현 명령

```powershell
cd src/api
uv sync --locked --extra test --extra embedding
$env:PYTHONUTF8 = "1"

# 선택 후보: E5-small
uv run --locked --extra embedding python -m app.manual_embedding_evaluation `
  ../../tests/fixtures/manual-search-evaluation.v1.json --repeats 20

# 저장공간 절약 후보: MiniLM INT8
uv run --locked --extra embedding python -m app.manual_embedding_evaluation `
  ../../tests/fixtures/manual-search-evaluation.v1.json `
  --model sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 `
  --revision e8f8c211226b894fcb81acc59f3b34ba3efd5f42 `
  --file-name openvino/openvino_model_qint8_quantized.xml `
  --query-prefix "" --document-prefix "" --repeats 20
```
