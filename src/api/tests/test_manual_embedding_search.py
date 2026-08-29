from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.manual_embedding_search import EmbeddingManualSearcher
from app.manual_ingestion import run_pending_ingestion
from tests.test_api import verified_manual_payload
from tests.test_manual_ingestion import write_manifest


class FakeSemanticModel:
    def __init__(self) -> None:
        self.encoded_batches: list[list[str]] = []

    def encode(
        self,
        sentences: list[str],
        *,
        normalize_embeddings: bool,
        convert_to_numpy: bool,
        show_progress_bar: bool,
    ) -> list[list[float]]:
        del normalize_embeddings, convert_to_numpy, show_progress_bar
        self.encoded_batches.append(sentences)
        vectors: list[list[float]] = []
        for sentence in sentences:
            if "운전석 도어 라벨" in sentence or "바람 압력" in sentence:
                vectors.append([1.0, 0.0])
            elif "견인 고리" in sentence:
                vectors.append([0.0, 1.0])
            else:
                vectors.append([-1.0, 0.0])
        return vectors


def searcher_with(model: FakeSemanticModel) -> EmbeddingManualSearcher:
    return EmbeddingManualSearcher(
        model_name="fake",
        revision="test",
        model_file="fake.xml",
        min_score=0.82,
        model_factory=lambda: model,
    )


def test_embedding_search_finds_semantic_match_and_reuses_document_vectors() -> None:
    model = FakeSemanticModel()
    searcher = searcher_with(model)
    rows = [
        {
            "document_name": "테스트 설명서",
            "source_url": "https://example.com/manual",
            "page": 1,
            "section": None,
            "content": "권장값은 운전석 도어 라벨에서 확인하십시오.",
        },
        {
            "document_name": "테스트 설명서",
            "source_url": "https://example.com/manual",
            "page": 2,
            "section": None,
            "content": "견인 고리는 트렁크 공구함에 있습니다.",
        },
    ]

    first = searcher.search(
        rows, document_key="test:manual:2025", question="타이어 바람 압력", limit=1
    )
    second = searcher.search(
        rows, document_key="test:manual:2025", question="타이어 바람 압력", limit=1
    )
    unrelated = searcher.search(
        rows, document_key="test:manual:2025", question="오늘 날씨", limit=1
    )

    assert first[0]["page"] == 1
    assert second == first
    assert unrelated == []
    assert [len(batch) for batch in model.encoded_batches] == [2, 1, 1, 1]


def test_embedding_search_reindexes_changed_document() -> None:
    model = FakeSemanticModel()
    searcher = searcher_with(model)
    rows = [
        {
            "document_name": "테스트 설명서",
            "source_url": "https://example.com/manual",
            "page": 1,
            "section": None,
            "content": "권장값은 운전석 도어 라벨에서 확인하십시오.",
        }
    ]
    searcher.search(rows, document_key="test:manual:2025", question="바람 압력", limit=1)
    rows[0]["content"] = "견인 고리는 트렁크 공구함에 있습니다."

    result = searcher.search(
        rows, document_key="test:manual:2025", question="견인 고리", limit=1
    )

    assert result[0]["page"] == 1
    assert [len(batch) for batch in model.encoded_batches] == [1, 1, 1, 1]


def embedding_client(tmp_path: Path) -> TestClient:
    settings = Settings(
        database_path=tmp_path / "embedding.db",
        cors_origins=("https://kimdohong.github.io",),
        manual_source_dir=tmp_path / "manuals",
        manual_search_mode="embedding",
    )
    return TestClient(create_app(settings))


def prepare_ready_manual(client: TestClient, tmp_path: Path) -> None:
    assert client.post(
        "/api/v1/vehicles", json=verified_manual_payload()
    ).status_code == 201
    write_manifest(tmp_path / "manuals")
    assert run_pending_ingestion(
        client.app.state.settings.database_path, tmp_path / "manuals"
    )[0].status == "ready"


def test_embedding_mode_is_used_by_manual_search_api(tmp_path: Path) -> None:
    model = FakeSemanticModel()
    with embedding_client(tmp_path) as client:
        client.app.state.manual_embedding_search = searcher_with(model)
        prepare_ready_manual(client, tmp_path)

        response = client.post(
            "/api/v1/manual/search",
            json={"vehicle_id": "verified-ioniq5", "question": "타이어 바람 압력"},
        )

    assert response.status_code == 200
    assert response.json()["search_engine"] == "openvino-embedding-v1"
    assert response.json()["sources"][0]["page"] == 1


def test_embedding_model_load_failure_is_explicit(tmp_path: Path) -> None:
    def fail_model_load():
        raise RuntimeError("test model load failure")

    with embedding_client(tmp_path) as client:
        client.app.state.manual_embedding_search = EmbeddingManualSearcher(
            model_name="fake",
            revision="test",
            model_file="fake.xml",
            min_score=0.82,
            model_factory=fail_model_load,
        )
        prepare_ready_manual(client, tmp_path)

        response = client.post(
            "/api/v1/manual/search",
            json={"vehicle_id": "verified-ioniq5", "question": "타이어 바람 압력"},
        )

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "manual_embedding_unavailable",
        "message": "매뉴얼 의미 검색 모델을 사용할 수 없습니다. 서버 설정과 모델 상태를 확인해 주세요.",
        "retryable": True,
        "details": None,
    }
