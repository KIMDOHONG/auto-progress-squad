from pathlib import Path

import pytest

from app.manual_search_evaluation import (
    evaluate_keyword_search,
    load_evaluation_dataset,
)
from app.manual_ingestion import rank_manual_chunks


def evaluation_path() -> Path:
    return Path(__file__).parents[3] / "tests" / "fixtures" / (
        "manual-search-evaluation.v1.json"
    )


def test_keyword_search_baseline_is_reproducible() -> None:
    result = evaluate_keyword_search(load_evaluation_dataset(evaluation_path()))

    assert result["question_count"] == 8
    assert result["limit"] == 3
    assert result["hit_rate_at_k"] == 0.75
    assert result["mean_reciprocal_rank"] == 0.75
    assert [case["relevant_page"] for case in result["cases"] if case["rank"] is None] == [
        66,
        88,
    ]


def test_evaluation_rejects_invalid_limit() -> None:
    dataset = load_evaluation_dataset(evaluation_path())

    with pytest.raises(ValueError, match="limit must be at least 1"):
        evaluate_keyword_search(dataset, limit=0)


@pytest.mark.parametrize(
    ("question", "content"),
    [
        ("스마트키 배터리 교체", "스마트 키 건전지 교체 방법"),
        ("12V 배터리 방전", "12 V 배터리 방전 시 점프 스타트 방법"),
    ],
)
def test_keyword_search_normalizes_spacing_and_battery_synonym(
    question: str,
    content: str,
) -> None:
    results = rank_manual_chunks(
        [
            {
                "document_name": "공식 취급설명서",
                "source_url": "https://ownersmanual.hyundai.com/manual/test",
                "page": 10,
                "section": None,
                "content": content,
            },
            {
                "document_name": "공식 취급설명서",
                "source_url": "https://ownersmanual.hyundai.com/manual/test",
                "page": 20,
                "section": None,
                "content": "일반 배터리 관리 안내",
            },
        ],
        question,
        1,
    )

    assert results[0]["page"] == 10
