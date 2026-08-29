from pathlib import Path

import pytest

from app.manual_embedding_evaluation import evaluate_embedding_search
from app.manual_search_evaluation import load_evaluation_dataset


class FakeEmbeddingModel:
    def __init__(self, page_vectors: dict[str, list[float]]) -> None:
        self.page_vectors = page_vectors

    def encode(
        self,
        sentences: list[str],
        *,
        normalize_embeddings: bool,
        convert_to_numpy: bool,
        show_progress_bar: bool,
    ) -> list[list[float]]:
        del normalize_embeddings, convert_to_numpy, show_progress_bar
        return [self.page_vectors.get(sentence, [1.0, 0.0]) for sentence in sentences]

    def get_sentence_embedding_dimension(self) -> int:
        return len(next(iter(self.page_vectors.values())))


class InvalidEmbeddingModel:
    def __init__(self, *, document_vectors: list[list[float]]) -> None:
        self.document_vectors = document_vectors

    def encode(
        self,
        sentences: list[str],
        *,
        normalize_embeddings: bool,
        convert_to_numpy: bool,
        show_progress_bar: bool,
    ) -> list[list[float]]:
        del normalize_embeddings, convert_to_numpy, show_progress_bar
        if len(sentences) == 1:
            return [[1.0, 0.0]]
        return self.document_vectors

    def get_sentence_embedding_dimension(self) -> int:
        return 2


def evaluation_path() -> Path:
    return Path(__file__).parents[3] / "tests" / "fixtures" / (
        "manual-search-evaluation.v1.json"
    )


def test_embedding_evaluation_reports_retrieval_metrics() -> None:
    dataset = load_evaluation_dataset(evaluation_path())
    vectors: dict[str, list[float]] = {}
    for index, chunk in enumerate(dataset.chunks):
        vector = [0.0] * len(dataset.chunks)
        vector[index] = 1.0
        vectors[str(chunk["content"])] = vector
    for index, item in enumerate(dataset.questions):
        vectors[item.question] = vectors[str(dataset.chunks[index]["content"])]
    model = FakeEmbeddingModel(vectors)

    result = evaluate_embedding_search(
        dataset,
        model,
        model_name="fake",
        backend="test",
        device="cpu",
        repeats=1,
    )

    assert result["question_count"] == 8
    assert result["embedding_dimension"] == 8
    assert result["hit_rate_at_k"] == 1.0
    assert result["mean_reciprocal_rank"] == 1.0
    assert all(case["rank"] == 1 for case in result["cases"])
    assert len(result["cases"]) == 8
    assert result["timing_ms"]["query_mean"] >= 0


@pytest.mark.parametrize(("limit", "repeats"), ((0, 1), (3, 0)))
def test_embedding_evaluation_rejects_invalid_counts(limit: int, repeats: int) -> None:
    dataset = load_evaluation_dataset(evaluation_path())

    with pytest.raises(ValueError):
        evaluate_embedding_search(
            dataset,
            FakeEmbeddingModel({}),
            model_name="fake",
            backend="test",
            device="cpu",
            limit=limit,
            repeats=repeats,
        )


@pytest.mark.parametrize(
    ("document_vectors", "message"),
    (
        ([[1.0, 0.0]], "wrong document vector count"),
        ([[1.0, 0.0, 0.0]] * 8, "dimensions do not match"),
    ),
)
def test_embedding_evaluation_rejects_invalid_model_output(
    document_vectors: list[list[float]], message: str
) -> None:
    dataset = load_evaluation_dataset(evaluation_path())

    with pytest.raises(ValueError, match=message):
        evaluate_embedding_search(
            dataset,
            InvalidEmbeddingModel(document_vectors=document_vectors),
            model_name="invalid",
            backend="test",
            device="cpu",
            repeats=1,
        )
