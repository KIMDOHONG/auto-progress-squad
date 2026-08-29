from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .manual_grounded_answer import (
    GroundedManualAnswer,
    ManualAnswerGenerationError,
    ManualAnswerValidationError,
    OpenVINOGroundedAnswerGenerator,
)


DEFAULT_MODEL_ID = "OpenVINO/Qwen2.5-1.5B-Instruct-int4-ov"
DEFAULT_REVISION = "748d8cc119574c982192d9473e77bcf68273dd5a"


@dataclass(frozen=True, slots=True)
class GenerationEvaluationCase:
    case_id: str
    question: str
    sources: tuple[dict[str, object], ...]
    expected_citations: tuple[int, ...]
    required_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GenerationEvaluationDataset:
    name: str
    notice: str
    cases: tuple[GenerationEvaluationCase, ...]


class GroundedAnswerGenerator(Protocol):
    def generate(
        self, question: str, sources: Sequence[dict[str, object]]
    ) -> GroundedManualAnswer: ...


def _required_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def load_generation_evaluation_dataset(path: Path) -> GenerationEvaluationDataset:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("unsupported generation evaluation dataset schema")
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("generation evaluation dataset requires cases")

    cases: list[GenerationEvaluationCase] = []
    seen_ids: set[str] = set()
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            raise ValueError("generation evaluation case must be an object")
        case_id = _required_string(raw_case.get("id"), "case id")
        if case_id in seen_ids:
            raise ValueError("generation evaluation case ids must be unique")
        seen_ids.add(case_id)
        question = _required_string(raw_case.get("question"), "question")
        raw_sources = raw_case.get("sources")
        if not isinstance(raw_sources, list) or not raw_sources:
            raise ValueError("generation evaluation case requires sources")
        sources: list[dict[str, object]] = []
        for raw_source in raw_sources:
            if not isinstance(raw_source, dict):
                raise ValueError("generation evaluation source must be an object")
            source = {
                "document_name": _required_string(
                    raw_source.get("document_name"), "document_name"
                ),
                "source_url": _required_string(
                    raw_source.get("source_url"), "source_url"
                ),
                "page": raw_source.get("page"),
                "section": raw_source.get("section"),
                "excerpt": _required_string(raw_source.get("excerpt"), "excerpt"),
            }
            if not isinstance(source["page"], int) or source["page"] < 1:
                raise ValueError("generation evaluation source page must be positive")
            if source["section"] is not None and not isinstance(
                source["section"], str
            ):
                raise ValueError("generation evaluation source section is invalid")
            sources.append(source)

        raw_citations = raw_case.get("expected_citations")
        if not isinstance(raw_citations, list) or not raw_citations or not all(
            isinstance(citation, int) and 1 <= citation <= len(sources)
            for citation in raw_citations
        ):
            raise ValueError("expected citations must reference provided sources")
        raw_terms = raw_case.get("required_terms")
        if not isinstance(raw_terms, list) or not raw_terms:
            raise ValueError("generation evaluation case requires terms")
        required_terms = tuple(
            _required_string(term, "required term") for term in raw_terms
        )
        cases.append(
            GenerationEvaluationCase(
                case_id=case_id,
                question=question,
                sources=tuple(sources),
                expected_citations=tuple(raw_citations),
                required_terms=required_terms,
            )
        )
    return GenerationEvaluationDataset(
        name=_required_string(payload.get("name"), "dataset name"),
        notice=_required_string(payload.get("notice"), "dataset notice"),
        cases=tuple(cases),
    )


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def evaluate_grounded_generation(
    dataset: GenerationEvaluationDataset,
    generator: GroundedAnswerGenerator,
    *,
    model_id: str,
    revision: str,
    device: str,
    repeats: int = 1,
) -> dict[str, object]:
    if repeats < 1:
        raise ValueError("repeats must be at least 1")

    latencies_ms: list[float] = []
    cases: list[dict[str, object]] = []
    successful_runs = 0
    citation_matches = 0
    required_term_matches = 0
    total_runs = len(dataset.cases) * repeats
    for item in dataset.cases:
        run_results: list[dict[str, object]] = []
        for _ in range(repeats):
            started = time.perf_counter()
            try:
                answer = generator.generate(item.question, item.sources)
            except (ManualAnswerGenerationError, ManualAnswerValidationError) as error:
                elapsed_ms = (time.perf_counter() - started) * 1_000
                latencies_ms.append(elapsed_ms)
                run_results.append(
                    {
                        "status": "rejected",
                        "error": type(error).__name__,
                        "reason": str(error),
                        "latency_ms": round(elapsed_ms, 4),
                    }
                )
                continue
            elapsed_ms = (time.perf_counter() - started) * 1_000
            latencies_ms.append(elapsed_ms)
            citations_match = answer.citations == item.expected_citations
            terms_match = all(term in answer.answer for term in item.required_terms)
            successful_runs += 1
            citation_matches += int(citations_match)
            required_term_matches += int(terms_match)
            run_results.append(
                {
                    "status": "accepted",
                    "answer": answer.answer,
                    "citations": list(answer.citations),
                    "citations_match": citations_match,
                    "required_terms_match": terms_match,
                    "latency_ms": round(elapsed_ms, 4),
                }
            )
        cases.append(
            {
                "id": item.case_id,
                "question": item.question,
                "expected_citations": list(item.expected_citations),
                "required_terms": list(item.required_terms),
                "runs": run_results,
                "passed": all(
                    run.get("status") == "accepted"
                    and run.get("citations_match") is True
                    and run.get("required_terms_match") is True
                    for run in run_results
                ),
            }
        )

    warm_latencies = latencies_ms[1:] or latencies_ms
    return {
        "dataset": dataset.name,
        "dataset_notice": dataset.notice,
        "model": model_id,
        "revision": revision,
        "device": device,
        "case_count": len(dataset.cases),
        "repeats": repeats,
        "generation_accept_rate": round(successful_runs / total_runs, 4),
        "citation_accuracy": round(citation_matches / total_runs, 4),
        "required_term_accuracy": round(required_term_matches / total_runs, 4),
        "case_pass_rate": round(
            sum(case["passed"] is True for case in cases) / len(cases), 4
        ),
        "timing_ms": {
            "first_call_cold": round(latencies_ms[0], 4),
            "warm_mean": round(statistics.fmean(warm_latencies), 4),
            "warm_p50": round(statistics.median(warm_latencies), 4),
            "warm_p95": round(_percentile(warm_latencies, 0.95), 4),
        },
        "cases": cases,
    }


class PeakRSSSampler:
    def __init__(self, process: object, interval_seconds: float = 0.05) -> None:
        self.process = process
        self.interval_seconds = interval_seconds
        self.baseline_bytes = int(process.memory_info().rss)  # type: ignore[attr-defined]
        self.peak_bytes = self.baseline_bytes
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            rss = int(self.process.memory_info().rss)  # type: ignore[attr-defined]
            self.peak_bytes = max(self.peak_bytes, rss)

    def __enter__(self) -> "PeakRSSSampler":
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.peak_bytes = max(
            self.peak_bytes,
            int(self.process.memory_info().rss),  # type: ignore[attr-defined]
        )
        self._stop.set()
        self._thread.join()


def _model_size_bytes(path: Path) -> int:
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while block := file.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate a local OpenVINO grounded manual answer model."
    )
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--revision", default=DEFAULT_REVISION)
    parser.add_argument("--device", default="CPU")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--max-new-tokens", type=int, default=128)
    parser.add_argument("--min-token-overlap", type=float, default=0.55)
    args = parser.parse_args()

    try:
        import psutil
    except ImportError as error:
        raise SystemExit(
            "evaluation dependencies are missing; run "
            "`uv sync --extra generation-evaluation`"
        ) from error
    model_path = args.model_path.resolve()
    if not model_path.is_dir() or not (model_path / "openvino_model.bin").is_file():
        raise SystemExit("model path does not contain an OpenVINO LLM")

    process = psutil.Process()
    generator = OpenVINOGroundedAnswerGenerator(
        model_path=model_path,
        device=args.device,
        max_new_tokens=args.max_new_tokens,
        min_token_overlap=args.min_token_overlap,
    )
    with PeakRSSSampler(process) as memory:
        result = evaluate_grounded_generation(
            load_generation_evaluation_dataset(args.dataset),
            generator,
            model_id=args.model_id,
            revision=args.revision,
            device=args.device,
            repeats=args.repeats,
        )
    model_bin = model_path / "openvino_model.bin"
    result["model_artifact"] = {
        "directory_name": model_path.name,
        "size_mb": round(_model_size_bytes(model_path) / (1024 * 1024), 2),
        "openvino_model_bin_sha256": _sha256(model_bin),
    }
    result["memory_mb"] = {
        "process_rss_baseline": round(memory.baseline_bytes / (1024 * 1024), 2),
        "process_rss_peak": round(memory.peak_bytes / (1024 * 1024), 2),
        "process_rss_increase": round(
            (memory.peak_bytes - memory.baseline_bytes) / (1024 * 1024), 2
        ),
        "system_total": round(psutil.virtual_memory().total / (1024 * 1024), 2),
    }
    result["runtime"] = {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_processors": os.cpu_count(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

