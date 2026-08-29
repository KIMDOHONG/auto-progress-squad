from __future__ import annotations

import argparse
import json
import math
import os
import platform
import statistics
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from .manual_search_evaluation import EvaluationDataset, load_evaluation_dataset


DEFAULT_MODEL = "intfloat/multilingual-e5-small"
DEFAULT_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
DEFAULT_OPENVINO_FILE = "openvino/openvino_model.xml"
DEFAULT_QUERY_PREFIX = "query: "
DEFAULT_DOCUMENT_PREFIX = "passage: "


class SentenceEmbeddingModel(Protocol):
    def encode(
        self,
        sentences: list[str],
        *,
        normalize_embeddings: bool,
        convert_to_numpy: bool,
        show_progress_bar: bool,
    ) -> object: ...

    def get_sentence_embedding_dimension(self) -> int | None: ...


def _vectors(value: object) -> list[list[float]]:
    raw = value.tolist() if hasattr(value, "tolist") else value
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise TypeError("embedding model returned an unsupported value")
    vectors: list[list[float]] = []
    for vector in raw:
        if not isinstance(vector, Sequence) or isinstance(vector, (str, bytes)):
            raise TypeError("embedding model returned an unsupported vector")
        vectors.append([float(item) for item in vector])
    if not vectors or not vectors[0]:
        raise ValueError("embedding model returned no usable vectors")
    dimension = len(vectors[0])
    if any(len(vector) != dimension for vector in vectors):
        raise ValueError("embedding model returned inconsistent vector dimensions")
    return vectors


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def evaluate_embedding_search(
    dataset: EvaluationDataset,
    model: SentenceEmbeddingModel,
    *,
    model_name: str,
    backend: str,
    device: str,
    query_prefix: str = "",
    document_prefix: str = "",
    limit: int = 3,
    repeats: int = 5,
) -> dict[str, object]:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if repeats < 1:
        raise ValueError("repeats must be at least 1")

    warmup_started = time.perf_counter()
    model.encode(
        [query_prefix + "매뉴얼 검색 준비"],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    warmup_ms = (time.perf_counter() - warmup_started) * 1_000

    index_started = time.perf_counter()
    document_vectors = _vectors(
        model.encode(
            [document_prefix + str(chunk["content"]) for chunk in dataset.chunks],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
    )
    if len(document_vectors) != len(dataset.chunks):
        raise ValueError("embedding model returned the wrong document vector count")
    document_index_ms = (time.perf_counter() - index_started) * 1_000

    hits = 0
    reciprocal_rank_sum = 0.0
    latencies_ms: list[float] = []
    cases: list[dict[str, object]] = []
    for item in dataset.questions:
        query_vector: list[float] | None = None
        for _ in range(repeats):
            query_started = time.perf_counter()
            query_vectors = _vectors(
                model.encode(
                    [query_prefix + item.question],
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
            )
            if len(query_vectors) != 1:
                raise ValueError("embedding model returned the wrong query vector count")
            query_vector = query_vectors[0]
            latencies_ms.append((time.perf_counter() - query_started) * 1_000)

        assert query_vector is not None
        if len(query_vector) != len(document_vectors[0]):
            raise ValueError("query and document embedding dimensions do not match")
        scores = [
            sum(left * right for left, right in zip(query_vector, document_vector))
            for document_vector in document_vectors
        ]
        ranked_indexes = sorted(
            range(len(scores)), key=lambda index: scores[index], reverse=True
        )[:limit]
        retrieved_pages = [int(dataset.chunks[index]["page"]) for index in ranked_indexes]
        rank = next(
            (
                index
                for index, page in enumerate(retrieved_pages, start=1)
                if page == item.relevant_page
            ),
            None,
        )
        if rank is not None:
            hits += 1
            reciprocal_rank_sum += 1 / rank
        cases.append(
            {
                "question": item.question,
                "relevant_page": item.relevant_page,
                "retrieved_pages": retrieved_pages,
                "rank": rank,
            }
        )

    question_count = len(dataset.questions)
    return {
        "dataset": dataset.name,
        "search": "dense-cosine-v1",
        "model": model_name,
        "backend": backend,
        "device": device,
        "query_prefix": query_prefix,
        "document_prefix": document_prefix,
        "embedding_dimension": model.get_sentence_embedding_dimension(),
        "question_count": question_count,
        "limit": limit,
        "repeats": repeats,
        "hit_rate_at_k": round(hits / question_count, 4),
        "mean_reciprocal_rank": round(reciprocal_rank_sum / question_count, 4),
        "timing_ms": {
            "warmup": round(warmup_ms, 4),
            "document_batch": round(document_index_ms, 4),
            "query_mean": round(statistics.fmean(latencies_ms), 4),
            "query_p50": round(statistics.median(latencies_ms), 4),
            "query_p95": round(_percentile(latencies_ms, 0.95), 4),
        },
        "runtime": {
            "platform": platform.platform(),
            "logical_processors": os.cpu_count(),
        },
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate a local sentence embedding model for manual retrieval."
    )
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--revision", default=DEFAULT_REVISION)
    parser.add_argument("--backend", default="openvino")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--file-name", default=DEFAULT_OPENVINO_FILE)
    parser.add_argument("--query-prefix", default=DEFAULT_QUERY_PREFIX)
    parser.add_argument("--document-prefix", default=DEFAULT_DOCUMENT_PREFIX)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise SystemExit(
            "embedding dependencies are missing; run `uv sync --extra embedding`"
        ) from error

    load_started = time.perf_counter()
    model = SentenceTransformer(
        args.model,
        revision=args.revision,
        backend=args.backend,
        device=args.device,
        model_kwargs={"file_name": args.file_name},
    )
    load_ms = (time.perf_counter() - load_started) * 1_000
    result = evaluate_embedding_search(
        load_evaluation_dataset(args.dataset),
        model,
        model_name=args.model,
        backend=args.backend,
        device=args.device,
        query_prefix=args.query_prefix,
        document_prefix=args.document_prefix,
        limit=args.limit,
        repeats=args.repeats,
    )
    result["revision"] = args.revision
    result["model_file"] = args.file_name
    result["timing_ms"]["load"] = round(load_ms, 4)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
