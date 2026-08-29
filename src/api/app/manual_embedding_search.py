from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Callable, Mapping, Sequence
from typing import Protocol


class SentenceEmbeddingModel(Protocol):
    def encode(
        self,
        sentences: list[str],
        *,
        normalize_embeddings: bool,
        convert_to_numpy: bool,
        show_progress_bar: bool,
    ) -> object: ...


class ManualEmbeddingSearchError(Exception):
    pass


def _vectors(value: object) -> list[list[float]]:
    raw = value.tolist() if hasattr(value, "tolist") else value
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("embedding model returned an unsupported value")
    vectors: list[list[float]] = []
    for vector in raw:
        if not isinstance(vector, Sequence) or isinstance(vector, (str, bytes)):
            raise ValueError("embedding model returned an unsupported vector")
        vectors.append([float(item) for item in vector])
    if not vectors or not vectors[0]:
        raise ValueError("embedding model returned no usable vectors")
    dimension = len(vectors[0])
    if any(len(vector) != dimension for vector in vectors):
        raise ValueError("embedding model returned inconsistent vector dimensions")
    return vectors


def _default_model_factory(
    model_name: str, revision: str, model_file: str
) -> SentenceEmbeddingModel:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise ManualEmbeddingSearchError(
            "embedding dependencies are not installed"
        ) from error
    try:
        return SentenceTransformer(
            model_name,
            revision=revision,
            backend="openvino",
            device="cpu",
            model_kwargs={"file_name": model_file},
        )
    except Exception as error:
        raise ManualEmbeddingSearchError("embedding model could not be loaded") from error


class EmbeddingManualSearcher:
    def __init__(
        self,
        *,
        model_name: str,
        revision: str,
        model_file: str,
        min_score: float,
        model_factory: Callable[[], SentenceEmbeddingModel] | None = None,
        max_cached_documents: int = 4,
    ) -> None:
        if not 0 <= min_score <= 1:
            raise ValueError("min_score must be between 0 and 1")
        if max_cached_documents < 1:
            raise ValueError("max_cached_documents must be at least 1")
        self.model_name = model_name
        self.revision = revision
        self.model_file = model_file
        self.min_score = min_score
        self._model_factory = model_factory or (
            lambda: _default_model_factory(model_name, revision, model_file)
        )
        self._max_cached_documents = max_cached_documents
        self._model: SentenceEmbeddingModel | None = None
        self._document_cache: dict[str, tuple[str, list[list[float]]]] = {}
        self._lock = threading.RLock()

    def _get_model(self) -> SentenceEmbeddingModel:
        if self._model is None:
            try:
                self._model = self._model_factory()
            except ManualEmbeddingSearchError:
                raise
            except Exception as error:
                raise ManualEmbeddingSearchError(
                    "embedding model could not be loaded"
                ) from error
        return self._model

    @staticmethod
    def _fingerprint(rows: list[dict[str, object]]) -> str:
        serialized = json.dumps(rows, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _encode(
        self, model: SentenceEmbeddingModel, sentences: list[str]
    ) -> list[list[float]]:
        try:
            return _vectors(
                model.encode(
                    sentences,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
            )
        except ManualEmbeddingSearchError:
            raise
        except Exception as error:
            raise ManualEmbeddingSearchError(
                "embedding model inference failed"
            ) from error

    def search(
        self,
        rows: Sequence[Mapping[str, object]],
        *,
        document_key: str,
        question: str,
        limit: int,
    ) -> list[dict[str, object]]:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        records = [dict(row) for row in rows]
        if not records:
            return []
        fingerprint = self._fingerprint(records)

        with self._lock:
            model = self._get_model()
            cached = self._document_cache.get(document_key)
            if cached is None or cached[0] != fingerprint:
                document_vectors = self._encode(
                    model, ["passage: " + str(row["content"]) for row in records]
                )
                if len(document_vectors) != len(records):
                    raise ManualEmbeddingSearchError(
                        "embedding model returned the wrong document vector count"
                    )
                self._document_cache[document_key] = (fingerprint, document_vectors)
                while len(self._document_cache) > self._max_cached_documents:
                    self._document_cache.pop(next(iter(self._document_cache)))
            else:
                document_vectors = cached[1]

            query_vectors = self._encode(model, ["query: " + question])
            if len(query_vectors) != 1:
                raise ManualEmbeddingSearchError(
                    "embedding model returned the wrong query vector count"
                )
            query_vector = query_vectors[0]

        if len(query_vector) != len(document_vectors[0]):
            raise ManualEmbeddingSearchError(
                "query and document embedding dimensions do not match"
            )
        scores = [
            sum(left * right for left, right in zip(query_vector, document_vector))
            for document_vector in document_vectors
        ]
        ranked_indexes = sorted(
            range(len(scores)), key=lambda index: scores[index], reverse=True
        )
        results: list[dict[str, object]] = []
        for index in ranked_indexes:
            if scores[index] < self.min_score:
                continue
            row = records[index]
            content = str(row["content"])
            results.append(
                {
                    "document_name": row["document_name"],
                    "source_url": row["source_url"],
                    "page": row["page"],
                    "section": row["section"],
                    "excerpt": content[:500],
                }
            )
            if len(results) >= limit:
                break
        return results
