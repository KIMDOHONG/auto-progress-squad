from pathlib import Path

import pytest

from app.manual_search_evaluation import (
    evaluate_keyword_search,
    load_evaluation_dataset,
)


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
