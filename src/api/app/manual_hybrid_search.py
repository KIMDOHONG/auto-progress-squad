from __future__ import annotations

from collections.abc import Mapping, Sequence


def _source_key(source: Mapping[str, object]) -> tuple[str, object, object]:
    return (
        str(source["source_url"]),
        source.get("page"),
        source.get("section"),
    )


def merge_manual_search_results(
    keyword_results: Sequence[Mapping[str, object]],
    embedding_results: Sequence[Mapping[str, object]],
    *,
    limit: int,
) -> list[dict[str, object]]:
    """Merge lexical and semantic rankings while preferring grounded intent matches."""
    if limit < 1:
        raise ValueError("limit must be at least 1")

    records: dict[tuple[str, object, object], dict[str, object]] = {}
    scores: dict[tuple[str, object, object], float] = {}
    keyword_ranks: dict[tuple[str, object, object], int] = {}
    embedding_ranks: dict[tuple[str, object, object], int] = {}

    for rank, source in enumerate(keyword_results, start=1):
        key = _source_key(source)
        records.setdefault(key, dict(source))
        keyword_ranks.setdefault(key, rank)
        scores[key] = scores.get(key, 0.0) + 2.0 / (60 + rank)

    for rank, source in enumerate(embedding_results, start=1):
        key = _source_key(source)
        records.setdefault(key, dict(source))
        embedding_ranks.setdefault(key, rank)
        scores[key] = scores.get(key, 0.0) + 1.0 / (60 + rank)

    ranked_keys = sorted(
        records,
        key=lambda key: (
            -scores[key],
            keyword_ranks.get(key, 10_000),
            embedding_ranks.get(key, 10_000),
        ),
    )
    return [records[key] for key in ranked_keys[:limit]]
