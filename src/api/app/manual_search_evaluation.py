from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from .manual_ingestion import rank_manual_chunks


@dataclass(frozen=True, slots=True)
class EvaluationQuestion:
    question: str
    relevant_page: int


@dataclass(frozen=True, slots=True)
class EvaluationDataset:
    name: str
    chunks: tuple[dict[str, object], ...]
    questions: tuple[EvaluationQuestion, ...]


def load_evaluation_dataset(path: Path) -> EvaluationDataset:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported evaluation dataset schema")

    chunks = tuple(payload.get("chunks", ()))
    questions = tuple(
        EvaluationQuestion(
            question=str(item["question"]),
            relevant_page=int(item["relevant_page"]),
        )
        for item in payload.get("questions", ())
    )
    if not chunks or not questions:
        raise ValueError("evaluation dataset requires chunks and questions")

    pages = {int(chunk["page"]) for chunk in chunks}
    if any(question.relevant_page not in pages for question in questions):
        raise ValueError("evaluation question references an unknown page")

    return EvaluationDataset(
        name=str(payload.get("name", path.stem)),
        chunks=chunks,
        questions=questions,
    )


def evaluate_keyword_search(
    dataset: EvaluationDataset, *, limit: int = 3
) -> dict[str, object]:
    if limit < 1:
        raise ValueError("limit must be at least 1")

    hits = 0
    reciprocal_rank_sum = 0.0
    cases: list[dict[str, object]] = []
    for item in dataset.questions:
        results = rank_manual_chunks(dataset.chunks, item.question, limit)
        retrieved_pages = [int(result["page"]) for result in results]
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
        "search": "keyword-frequency-v1",
        "question_count": question_count,
        "limit": limit,
        "hit_rate_at_k": round(hits / question_count, 4),
        "mean_reciprocal_rank": round(reciprocal_rank_sum / question_count, 4),
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the current manual keyword search baseline."
    )
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    result = evaluate_keyword_search(
        load_evaluation_dataset(args.dataset), limit=args.limit
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
