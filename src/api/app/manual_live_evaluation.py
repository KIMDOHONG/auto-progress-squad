from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from .config import Settings
from .database import VehicleNotFoundError, get_manual_ingestion_row
from .manual_ingestion import search_manual_document


OFFICIAL_MANUAL_HOSTS = {
    "hmc": "ownersmanual.hyundai.com",
    "kia": "ownersmanual.kia.com",
    "genesis": "ownersmanual.genesis.com",
}


@dataclass(frozen=True, slots=True)
class LiveEvaluationQuestion:
    question: str
    relevant_pages: tuple[int, ...] = ()
    relevant_source_urls: tuple[str, ...] = ()
    relevant_sections: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LiveEvaluationDocument:
    vehicle_id: str
    document_key: str
    questions: tuple[LiveEvaluationQuestion, ...]


@dataclass(frozen=True, slots=True)
class LiveEvaluationDataset:
    name: str
    measured_at: str
    documents: tuple[LiveEvaluationDocument, ...]


def load_live_evaluation_dataset(path: Path) -> LiveEvaluationDataset:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported live evaluation dataset schema")

    documents: list[LiveEvaluationDocument] = []
    for raw_document in payload.get("documents", ()):
        document_key = str(raw_document["document_key"])
        site_id = document_key.partition(":")[0]
        if site_id not in OFFICIAL_MANUAL_HOSTS:
            raise ValueError("live evaluation supports official HKG manuals only")
        questions = tuple(
            LiveEvaluationQuestion(
                question=str(item["question"]).strip(),
                relevant_pages=tuple(
                    int(page) for page in item.get("relevant_pages", ())
                ),
                relevant_source_urls=tuple(
                    str(url).strip()
                    for url in item.get("relevant_source_urls", ())
                    if str(url).strip()
                ),
                relevant_sections=tuple(
                    str(section).strip()
                    for section in item.get("relevant_sections", ())
                    if str(section).strip()
                ),
            )
            for item in raw_document.get("questions", ())
        )
        if not questions or any(
            not item.question
            or not (
                item.relevant_pages
                or item.relevant_source_urls
                or item.relevant_sections
            )
            for item in questions
        ):
            raise ValueError("each live evaluation document requires valid questions")
        documents.append(
            LiveEvaluationDocument(
                vehicle_id=str(raw_document["vehicle_id"]),
                document_key=document_key,
                questions=questions,
            )
        )

    if not documents:
        raise ValueError("live evaluation dataset requires documents")
    return LiveEvaluationDataset(
        name=str(payload.get("name", path.stem)),
        measured_at=str(payload.get("measured_at", "")),
        documents=tuple(documents),
    )


def evaluate_live_manual_search(
    database_path: Path,
    dataset: LiveEvaluationDataset,
    *,
    limit: int = 3,
) -> dict[str, object]:
    if limit < 1:
        raise ValueError("limit must be at least 1")

    hits = 0
    reciprocal_rank_sum = 0.0
    isolation_pass = True
    cases: list[dict[str, object]] = []

    for document in dataset.documents:
        try:
            job = get_manual_ingestion_row(database_path, document.vehicle_id)
        except VehicleNotFoundError as error:
            raise ValueError(
                f"evaluation vehicle is not registered: {document.vehicle_id}"
            ) from error
        if job is None:
            raise ValueError(
                f"manual ingestion is not configured: {document.vehicle_id}"
            )
        if job["document_key"] != document.document_key:
            raise ValueError(
                f"manual document mismatch for vehicle: {document.vehicle_id}"
            )
        if job["status"] != "ready":
            raise ValueError(
                f"manual document is not ready: {document.vehicle_id}"
            )

        site_id = document.document_key.partition(":")[0]
        expected_host = OFFICIAL_MANUAL_HOSTS[site_id]
        for item in document.questions:
            results = search_manual_document(
                database_path,
                document.document_key,
                item.question,
                limit,
            )
            retrieved_pages = [int(result["page"]) for result in results]
            retrieved_source_urls = [str(result["source_url"]) for result in results]
            retrieved_sections = [
                str(result["section"] or "") for result in results
            ]
            rank = next(
                (
                    index
                    for index, result in enumerate(results, start=1)
                    if (
                        not item.relevant_pages
                        or int(result["page"]) in item.relevant_pages
                    )
                    and (
                        not item.relevant_source_urls
                        or str(result["source_url"]) in item.relevant_source_urls
                    )
                    and (
                        not item.relevant_sections
                        or str(result["section"] or "") in item.relevant_sections
                    )
                ),
                None,
            )
            source_hosts = [
                (urlsplit(str(result["source_url"])).hostname or "").lower()
                for result in results
            ]
            case_isolation_pass = bool(source_hosts) and all(
                host == expected_host for host in source_hosts
            )
            isolation_pass = isolation_pass and case_isolation_pass
            if rank is not None:
                hits += 1
                reciprocal_rank_sum += 1 / rank
            cases.append(
                {
                    "vehicle_id": document.vehicle_id,
                    "document_key": document.document_key,
                    "question": item.question,
                    "relevant_pages": list(item.relevant_pages),
                    "relevant_source_urls": list(item.relevant_source_urls),
                    "relevant_sections": list(item.relevant_sections),
                    "retrieved_pages": retrieved_pages,
                    "retrieved_source_urls": retrieved_source_urls,
                    "retrieved_sections": retrieved_sections,
                    "rank": rank,
                    "expected_source_host": expected_host,
                    "retrieved_source_hosts": source_hosts,
                    "source_isolation_pass": case_isolation_pass,
                }
            )

    question_count = len(cases)
    return {
        "dataset": dataset.name,
        "measured_at": dataset.measured_at,
        "search": "keyword-intent-v3",
        "document_count": len(dataset.documents),
        "question_count": question_count,
        "limit": limit,
        "hit_rate_at_k": round(hits / question_count, 4),
        "mean_reciprocal_rank": round(reciprocal_rank_sum / question_count, 4),
        "source_isolation_pass": isolation_pass,
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate search against locally indexed official HKG manuals."
    )
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--database-path", type=Path)
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    database_path = args.database_path or Settings.from_env().database_path
    result = evaluate_live_manual_search(
        database_path,
        load_live_evaluation_dataset(args.dataset),
        limit=args.limit,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
