from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.recall_provider import (
    OFFICIAL_RECALL_SOURCE_NAME,
    OFFICIAL_RECALL_SOURCE_URL,
    RecallProviderError,
    RecallQuery,
    RecallRecord,
    RecallVehicleKey,
)


class FakeRecallProvider:
    source_name = OFFICIAL_RECALL_SOURCE_NAME
    source_url = OFFICIAL_RECALL_SOURCE_URL

    def __init__(self, records: Sequence[RecallRecord] = ()) -> None:
        self.records = records
        self.queries: list[RecallQuery] = []

    def list_recalls(self, query: RecallQuery) -> Sequence[RecallRecord]:
        self.queries.append(query)
        return self.records


class FailingRecallProvider(FakeRecallProvider):
    def list_recalls(self, query: RecallQuery) -> Sequence[RecallRecord]:
        self.queries.append(query)
        raise RecallProviderError("test provider timeout")


def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "recalls.db",
        cors_origins=("https://kimdohong.github.io",),
        manual_source_dir=tmp_path / "manuals",
    )


def vehicle_payload() -> dict[str, object]:
    return {
        "id": "stinger-2021",
        "nickname": "스팅어",
        "manufacturer": "기아",
        "model": "스팅어",
        "model_year": 2021,
        "powertrain": "gasoline",
        "fuel_grade": "premium",
        "manual_site_id": "kia",
        "manual_model_name": "스팅어",
        "manual_project_code": "CK",
        "manual_model_year": 2021,
        "manual_image_url": "https://ownersmanual.kia.com/images/ck.png",
        "manual_verified_at": "2026-09-01T00:00:00Z",
    }


def stinger_key(
    *,
    manufacturer: str = "기아",
    model: str = "스팅어",
    model_year: int = 2021,
    generation: str | None = None,
    project_code: str | None = "CK",
) -> RecallVehicleKey:
    return RecallVehicleKey(
        manufacturer=manufacturer,
        model=model,
        model_year=model_year,
        generation=generation,
        project_code=project_code,
    )


def test_recall_lookup_returns_official_records_and_query_scope(tmp_path: Path) -> None:
    provider = FakeRecallProvider(
        (
            RecallRecord(
                recall_id="KOR-2026-001",
                title="평가용 리콜 제목",
                published_at="2026-08-01",
                source_url="https://www.car.go.kr/ri/recall/detail.do?id=KOR-2026-001",
                vehicle_key=stinger_key(
                    manufacturer="KIA Corporation", model="스 팅어", project_code="ck"
                ),
            ),
        )
    )
    with TestClient(create_app(settings(tmp_path), recall_provider=provider)) as client:
        assert client.post("/api/v1/vehicles", json=vehicle_payload()).status_code == 201
        response = client.get("/api/v1/vehicles/stinger-2021/recalls")

    assert response.status_code == 200
    assert response.json() == {
        "vehicle_id": "stinger-2021",
        "status": "matched",
        "query": {
            "manufacturer": "기아",
            "model": "스팅어",
            "model_year": 2021,
            "generation": None,
            "project_code": "CK",
            "lookup_key": "kia|스팅어|2021|-|ck",
        },
        "items": [
            {
                "recall_id": "KOR-2026-001",
                "title": "평가용 리콜 제목",
                "published_at": "2026-08-01",
                "source_url": (
                    "https://www.car.go.kr/ri/recall/detail.do?id=KOR-2026-001"
                ),
            }
        ],
        "source_name": OFFICIAL_RECALL_SOURCE_NAME,
        "source_url": OFFICIAL_RECALL_SOURCE_URL,
        "retrieved_at": response.json()["retrieved_at"],
    }
    assert provider.queries == [
        RecallQuery(
            vehicle_id="stinger-2021",
            manufacturer="기아",
            model="스팅어",
            model_year=2021,
            generation=None,
            project_code="CK",
        )
    ]


def test_recall_lookup_distinguishes_no_results_from_failure(tmp_path: Path) -> None:
    provider = FakeRecallProvider()
    with TestClient(create_app(settings(tmp_path), recall_provider=provider)) as client:
        assert client.post("/api/v1/vehicles", json=vehicle_payload()).status_code == 201
        response = client.get("/api/v1/vehicles/stinger-2021/recalls")

    assert response.status_code == 200
    assert response.json()["status"] == "no_results"
    assert response.json()["items"] == []
    assert response.json()["source_name"] == OFFICIAL_RECALL_SOURCE_NAME


def test_recall_lookup_returns_404_for_unknown_vehicle_when_provider_exists(
    tmp_path: Path,
) -> None:
    with TestClient(
        create_app(settings(tmp_path), recall_provider=FakeRecallProvider())
    ) as client:
        response = client.get("/api/v1/vehicles/missing/recalls")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "vehicle_not_found"


def test_recall_lookup_fails_closed_when_official_provider_fails(tmp_path: Path) -> None:
    with TestClient(
        create_app(settings(tmp_path), recall_provider=FailingRecallProvider())
    ) as client:
        assert client.post("/api/v1/vehicles", json=vehicle_payload()).status_code == 201
        response = client.get("/api/v1/vehicles/stinger-2021/recalls")

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "recall_source_unavailable",
        "message": "공식 리콜 정보를 조회할 수 없습니다. 잠시 후 다시 시도해 주세요.",
        "retryable": True,
        "details": None,
    }


def test_recall_lookup_rejects_non_official_record_url(tmp_path: Path) -> None:
    provider = FakeRecallProvider(
        (
            RecallRecord(
                recall_id="untrusted",
                title="비공식 결과",
                source_url="https://example.com/recall/untrusted",
                vehicle_key=stinger_key(),
            ),
        )
    )
    with TestClient(create_app(settings(tmp_path), recall_provider=provider)) as client:
        assert client.post("/api/v1/vehicles", json=vehicle_payload()).status_code == 201
        response = client.get("/api/v1/vehicles/stinger-2021/recalls")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "recall_source_unavailable"


def test_recall_lookup_does_not_substitute_other_year_generation_or_project(
    tmp_path: Path,
) -> None:
    provider = FakeRecallProvider(
        (
            RecallRecord(
                recall_id="other-year",
                title="다른 연식",
                source_url="https://www.car.go.kr/ri/recall/detail.do?id=other-year",
                vehicle_key=stinger_key(model_year=2022),
            ),
            RecallRecord(
                recall_id="other-generation",
                title="다른 세대",
                source_url=(
                    "https://www.car.go.kr/ri/recall/detail.do?id=other-generation"
                ),
                vehicle_key=stinger_key(generation="CK PE"),
            ),
            RecallRecord(
                recall_id="other-project",
                title="다른 프로젝트 코드",
                source_url=(
                    "https://www.car.go.kr/ri/recall/detail.do?id=other-project"
                ),
                vehicle_key=stinger_key(project_code="CK2"),
            ),
        )
    )
    with TestClient(create_app(settings(tmp_path), recall_provider=provider)) as client:
        assert client.post("/api/v1/vehicles", json=vehicle_payload()).status_code == 201
        response = client.get("/api/v1/vehicles/stinger-2021/recalls")

    assert response.status_code == 200
    assert response.json()["status"] == "no_results"
    assert response.json()["items"] == []


def test_recall_vehicle_key_only_normalizes_format_and_known_manufacturer_aliases() -> None:
    assert stinger_key(
        manufacturer="기아자동차",
        model="스팅어  ",
        project_code="ＣＫ",
    ) == stinger_key(manufacturer="KIA", model="스-팅어", project_code="ck")
    assert stinger_key(model="스팅어 마이스터") != stinger_key(model="스팅어")
    assert stinger_key(model_year=2022) != stinger_key(model_year=2021)
    assert stinger_key(generation="CK PE") != stinger_key(generation=None)
