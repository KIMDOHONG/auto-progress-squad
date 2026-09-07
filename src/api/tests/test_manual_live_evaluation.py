from pathlib import Path

import pytest

from app.database import create_vehicle, initialize_database, replace_manual_document
from app.manual_live_evaluation import (
    LiveEvaluationDataset,
    LiveEvaluationDocument,
    LiveEvaluationQuestion,
    evaluate_live_manual_search,
    load_live_evaluation_dataset,
)
from app.schemas import VehicleCreate
from tests.test_api import verified_manual_payload


def dataset_path() -> Path:
    return Path(__file__).parents[3] / "tests" / "fixtures" / (
        "manual-live-evaluation.hkg.v1.json"
    )


def indexed_dataset(database_path: Path, *, source_host: str) -> LiveEvaluationDataset:
    initialize_database(database_path)
    payload = verified_manual_payload()
    payload["id"] = "live-evaluation-ioniq5"
    create_vehicle(database_path, VehicleCreate(**payload).model_dump())
    replace_manual_document(
        database_path,
        vehicle_id="live-evaluation-ioniq5",
        document_key="hmc:NE1:2024",
        document_name="아이오닉 5 2024 취급설명서",
        source_url=f"https://{source_host}/manual/ioniq5",
        content_sha256="a" * 64,
        page_count=2,
        chunks=[
            {
                "page": 1,
                "section": None,
                "content": "타이어 공기압은 운전석 도어 라벨에서 확인합니다.",
                "source_url": f"https://{source_host}/manual/ioniq5",
            },
            {
                "page": 2,
                "section": None,
                "content": "충전 도어를 연 다음 커넥터를 연결합니다.",
                "source_url": f"https://{source_host}/manual/ioniq5",
            },
        ],
    )
    return LiveEvaluationDataset(
        name="test-live-index",
        measured_at="2026-09-06",
        documents=(
            LiveEvaluationDocument(
                vehicle_id="live-evaluation-ioniq5",
                document_key="hmc:NE1:2024",
                questions=(
                    LiveEvaluationQuestion(
                        question="타이어 공기압 확인",
                        relevant_pages=(1,),
                    ),
                ),
            ),
        ),
    )


def test_live_dataset_loads_without_copying_manual_text() -> None:
    dataset = load_live_evaluation_dataset(dataset_path())

    assert dataset.name == "hkg-actual-owner-manual-baseline-v1"
    assert len(dataset.documents) == 2
    assert sum(len(document.questions) for document in dataset.documents) == 6


def test_live_evaluation_uses_ready_index_and_checks_source_isolation(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "live.db"
    dataset = indexed_dataset(
        database_path, source_host="ownersmanual.hyundai.com"
    )

    result = evaluate_live_manual_search(database_path, dataset)

    assert result["hit_rate_at_k"] == 1.0
    assert result["mean_reciprocal_rank"] == 1.0
    assert result["source_isolation_pass"] is True
    assert result["cases"][0]["retrieved_pages"] == [1]


def test_live_evaluation_reports_cross_manufacturer_source(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "cross-source.db"
    dataset = indexed_dataset(
        database_path, source_host="ownersmanual.genesis.com"
    )

    result = evaluate_live_manual_search(database_path, dataset)

    assert result["source_isolation_pass"] is False
    assert result["cases"][0]["source_isolation_pass"] is False


def test_live_evaluation_requires_registered_ready_document(tmp_path: Path) -> None:
    database_path = tmp_path / "missing.db"
    initialize_database(database_path)
    dataset = LiveEvaluationDataset(
        name="missing",
        measured_at="2026-09-06",
        documents=(
            LiveEvaluationDocument(
                vehicle_id="missing-vehicle",
                document_key="hmc:FE:2021",
                questions=(
                    LiveEvaluationQuestion("수소 충전구", (136,)),
                ),
            ),
        ),
    )

    with pytest.raises(ValueError, match="evaluation vehicle is not registered"):
        evaluate_live_manual_search(database_path, dataset)
