from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.manual_generation_evaluation import (
    PeakRSSSampler,
    evaluate_grounded_generation,
    load_generation_evaluation_dataset,
)
from app.manual_grounded_answer import (
    GroundedManualAnswer,
    ManualAnswerValidationError,
)


def evaluation_path() -> Path:
    return Path(__file__).parents[3] / "tests" / "fixtures" / (
        "manual-generation-evaluation.v1.json"
    )


class SourceCopyGenerator:
    def generate(
        self, _question: str, sources: tuple[dict[str, object], ...]
    ) -> GroundedManualAnswer:
        return GroundedManualAnswer(
            answer=f"{sources[0]['excerpt']} [1]", citations=(1,)
        )


class RejectingGenerator(SourceCopyGenerator):
    def generate(
        self, question: str, sources: tuple[dict[str, object], ...]
    ) -> GroundedManualAnswer:
        if "냉각수" in question:
            raise ManualAnswerValidationError("test rejection")
        return super().generate(question, sources)


def test_generation_evaluation_reports_quality_and_latency_metrics() -> None:
    result = evaluate_grounded_generation(
        load_generation_evaluation_dataset(evaluation_path()),
        SourceCopyGenerator(),
        model_id="fake-grounded-model",
        revision="test",
        device="CPU",
        repeats=2,
    )

    assert result["case_count"] == 8
    assert result["generation_accept_rate"] == 1.0
    assert result["citation_accuracy"] == 1.0
    assert result["required_term_accuracy"] == 1.0
    assert result["case_pass_rate"] == 1.0
    assert result["timing_ms"]["first_call_cold"] >= 0
    assert all(case["passed"] for case in result["cases"])


def test_generation_evaluation_preserves_rejection_reason() -> None:
    result = evaluate_grounded_generation(
        load_generation_evaluation_dataset(evaluation_path()),
        RejectingGenerator(),
        model_id="rejecting-model",
        revision="test",
        device="CPU",
    )

    rejected = next(case for case in result["cases"] if case["id"] == "coolant-level")
    assert rejected["passed"] is False
    assert rejected["runs"][0]["status"] == "rejected"
    assert rejected["runs"][0]["reason"] == "test rejection"
    assert result["generation_accept_rate"] == 0.875
    assert result["case_pass_rate"] == 0.875


def test_generation_evaluation_rejects_invalid_repeat_count() -> None:
    with pytest.raises(ValueError, match="repeats"):
        evaluate_grounded_generation(
            load_generation_evaluation_dataset(evaluation_path()),
            SourceCopyGenerator(),
            model_id="fake",
            revision="test",
            device="CPU",
            repeats=0,
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda payload: payload.update(schema_version=2), "schema"),
        (
            lambda payload: payload["cases"][1].update(
                id=payload["cases"][0]["id"]
            ),
            "unique",
        ),
        (
            lambda payload: payload["cases"][0].update(expected_citations=[2]),
            "provided sources",
        ),
    ],
)
def test_generation_evaluation_dataset_rejects_invalid_payload(
    tmp_path: Path, mutation, message: str
) -> None:
    payload = json.loads(evaluation_path().read_text(encoding="utf-8"))
    mutation(payload)
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_generation_evaluation_dataset(path)


class FakeMemoryInfo:
    def __init__(self, rss: int) -> None:
        self.rss = rss


class FakeProcess:
    def __init__(self) -> None:
        self.values = iter((100, 200, 150))
        self.last = 100

    def memory_info(self) -> FakeMemoryInfo:
        self.last = next(self.values, self.last)
        return FakeMemoryInfo(self.last)


def test_peak_rss_sampler_keeps_highest_observation() -> None:
    process = FakeProcess()
    with PeakRSSSampler(process, interval_seconds=0.001) as sampler:
        import time

        time.sleep(0.01)

    assert sampler.baseline_bytes == 100
    assert sampler.peak_bytes == 200

