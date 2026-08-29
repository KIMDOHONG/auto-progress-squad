from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient


def mapping(
    *,
    manufacturer_id: str = "kgm",
    model: str = "테스트 SUV",
    model_year: int = 2025,
    generation: str = "T1",
    official_url: str | None = None,
    chapter_url: str | None = None,
) -> dict[str, object]:
    host = (
        "www.chevrolet.co.kr"
        if manufacturer_id == "chevrolet"
        else "www.kg-mobility.com"
    )
    return {
        "manufacturer_id": manufacturer_id,
        "model": model,
        "model_year": model_year,
        "generation": generation,
        "manual_title": f"{model} - 취급설명서 (2025.01)",
        "official_url": official_url or f"https://{host}/owner-manuals/test",
        "source_checked_at": "2026-08-28",
        "chapters": [
            {
                "title": "안전 주의사항",
                "url": chapter_url or f"https://{host}/manuals/test/safety.pdf",
            },
            {
                "title": "시동 및 주행",
                "url": f"https://{host}/manuals/test/driving.pdf",
            },
        ],
    }


def write_catalog(source_root: Path, mappings: list[dict[str, object]]) -> None:
    source_root.mkdir(parents=True, exist_ok=True)
    (source_root / "adapter-manifest.json").write_text(
        json.dumps({"mappings": mappings}, ensure_ascii=False),
        encoding="utf-8",
    )


def test_catalog_lookup_returns_only_exact_approved_mapping(
    client: TestClient,
) -> None:
    write_catalog(client.app.state.settings.manual_source_dir, [mapping()])

    response = client.post(
        "/api/v1/manual-adapters/kgm/resolve",
        json={"model": "테스트 SUV", "model_year": 2025, "generation": "T1"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "manufacturer_id": "kgm",
        "model": "테스트 SUV",
        "model_year": 2025,
        "generation": "T1",
        "manual_title": "테스트 SUV - 취급설명서 (2025.01)",
        "official_url": "https://www.kg-mobility.com/owner-manuals/test",
        "source_checked_at": "2026-08-28",
        "chapters": [
            {
                "title": "안전 주의사항",
                "url": "https://www.kg-mobility.com/manuals/test/safety.pdf",
            },
            {
                "title": "시동 및 주행",
                "url": "https://www.kg-mobility.com/manuals/test/driving.pdf",
            },
        ],
    }


def test_catalog_lookup_does_not_fall_back_to_another_model_year(
    client: TestClient,
) -> None:
    write_catalog(client.app.state.settings.manual_source_dir, [mapping(model_year=2024)])

    response = client.post(
        "/api/v1/manual-adapters/kgm/resolve",
        json={"model": "테스트 SUV", "model_year": 2025, "generation": "T1"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "manual_mapping_not_found"


def test_catalog_lookup_requires_generation_when_same_year_has_multiple(
    client: TestClient,
) -> None:
    write_catalog(
        client.app.state.settings.manual_source_dir,
        [mapping(generation="T1"), mapping(generation="T2")],
    )

    ambiguous = client.post(
        "/api/v1/manual-adapters/kgm/resolve",
        json={"model": "테스트 SUV", "model_year": 2025},
    )
    exact = client.post(
        "/api/v1/manual-adapters/kgm/resolve",
        json={"model": "테스트 SUV", "model_year": 2025, "generation": "T2"},
    )

    assert ambiguous.status_code == 409
    assert ambiguous.json()["error"]["code"] == "manual_generation_required"
    assert ambiguous.json()["error"]["details"] == [
        {
            "generation": "T1",
            "manual_title": "테스트 SUV - 취급설명서 (2025.01)",
            "source_checked_at": "2026-08-28",
        },
        {
            "generation": "T2",
            "manual_title": "테스트 SUV - 취급설명서 (2025.01)",
            "source_checked_at": "2026-08-28",
        },
    ]
    assert "official_url" not in ambiguous.json()["error"]["details"][0]
    assert exact.status_code == 200
    assert exact.json()["generation"] == "T2"


def test_catalog_lookup_fails_closed_without_approved_manifest(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/manual-adapters/chevrolet/resolve",
        json={"model": "테스트 CUV", "model_year": 2025},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "manual_adapter_catalog_not_found"


def test_catalog_rejects_non_manufacturer_chapter_domain(
    client: TestClient,
) -> None:
    write_catalog(
        client.app.state.settings.manual_source_dir,
        [mapping(chapter_url="https://example.com/copied-manual.pdf")],
    )

    response = client.post(
        "/api/v1/manual-adapters/kgm/resolve",
        json={"model": "테스트 SUV", "model_year": 2025, "generation": "T1"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "manual_adapter_source_not_allowed"


def test_catalog_rejects_invalid_source_check_date(
    client: TestClient,
) -> None:
    invalid_mapping = mapping()
    invalid_mapping["source_checked_at"] = "2026-08"
    write_catalog(client.app.state.settings.manual_source_dir, [invalid_mapping])

    response = client.post(
        "/api/v1/manual-adapters/kgm/resolve",
        json={"model": "테스트 SUV", "model_year": 2025, "generation": "T1"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "manual_adapter_catalog_invalid"


def test_catalog_endpoint_rejects_bmw_and_unknown_adapter(
    client: TestClient,
) -> None:
    write_catalog(client.app.state.settings.manual_source_dir, [mapping()])

    for adapter_id in ("bmw", "unknown"):
        response = client.post(
            f"/api/v1/manual-adapters/{adapter_id}/resolve",
            json={"model": "테스트 SUV", "model_year": 2025},
        )
        assert response.status_code == 404
        assert (
            response.json()["error"]["code"]
            == "manual_adapter_catalog_not_supported"
        )


def test_exact_catalog_mapping_attaches_to_vehicle_without_guessing_image(
    client: TestClient,
) -> None:
    write_catalog(client.app.state.settings.manual_source_dir, [mapping()])
    created = client.post(
        "/api/v1/vehicles",
        json={
            "id": "kgm-test",
            "nickname": "테스트 차량",
            "manufacturer": "KGM",
            "model": "테스트 SUV",
            "model_year": 2025,
            "powertrain": "gasoline",
            "fuel_grade": "regular",
        },
    )
    assert created.status_code == 201

    response = client.post(
        "/api/v1/vehicles/kgm-test/manual-adapters/kgm",
        json={"generation": "T1"},
    )

    assert response.status_code == 200
    profile = response.json()
    assert profile["manual_site_id"] == "kgm"
    assert profile["manual_model_name"] == "테스트 SUV"
    assert profile["manual_generation"] == "T1"
    assert profile["manual_model_year"] == 2025
    assert profile["manual_title"] == "테스트 SUV - 취급설명서 (2025.01)"
    assert profile["manual_source_url"] == (
        "https://www.kg-mobility.com/owner-manuals/test"
    )
    assert profile["manual_image_url"] is None
    ingestion = client.get(
        "/api/v1/vehicles/kgm-test/manual-ingestion"
    ).json()
    assert ingestion["status"] == "pending"
    assert ingestion["document_key"] == (
        "kgm:catalog:%ED%85%8C%EC%8A%A4%ED%8A%B8%20suv:2025:t1"
    )
    assert ingestion["source_url"] == (
        "https://www.kg-mobility.com/owner-manuals/test"
    )


def test_catalog_attachment_returns_generation_choices_before_exact_selection(
    client: TestClient,
) -> None:
    write_catalog(
        client.app.state.settings.manual_source_dir,
        [mapping(generation="T2"), mapping(generation="T1")],
    )
    assert client.post(
        "/api/v1/vehicles",
        json={
            "id": "kgm-multiple-generations",
            "nickname": "세대 선택 차량",
            "manufacturer": "KGM",
            "model": "테스트 SUV",
            "model_year": 2025,
            "powertrain": "gasoline",
            "fuel_grade": "regular",
        },
    ).status_code == 201

    ambiguous = client.post(
        "/api/v1/vehicles/kgm-multiple-generations/manual-adapters/kgm",
        json={"generation": None},
    )
    exact = client.post(
        "/api/v1/vehicles/kgm-multiple-generations/manual-adapters/kgm",
        json={"generation": "T2"},
    )

    assert ambiguous.status_code == 409
    assert [
        item["generation"] for item in ambiguous.json()["error"]["details"]
    ] == ["T1", "T2"]
    assert exact.status_code == 200
    assert exact.json()["manual_generation"] == "T2"


def test_catalog_attachment_rejects_manufacturer_mismatch(
    client: TestClient,
) -> None:
    write_catalog(client.app.state.settings.manual_source_dir, [mapping()])
    assert client.post(
        "/api/v1/vehicles",
        json={
            "id": "wrong-brand",
            "nickname": "다른 제조사",
            "manufacturer": "쉐보레",
            "model": "테스트 SUV",
            "model_year": 2025,
            "powertrain": "gasoline",
            "fuel_grade": "regular",
        },
    ).status_code == 201

    response = client.post(
        "/api/v1/vehicles/wrong-brand/manual-adapters/kgm",
        json={"generation": "T1"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == (
        "manual_adapter_manufacturer_mismatch"
    )


def test_pilot_catalog_example_resolves_only_reviewed_model_years(
    client: TestClient,
) -> None:
    repository_root = Path(__file__).parents[3]
    example_path = (
        repository_root / "docs" / "examples" / "adapter-manifest.pilot.json"
    )
    payload = json.loads(example_path.read_text(encoding="utf-8"))
    write_catalog(client.app.state.settings.manual_source_dir, payload["mappings"])

    reviewed = (
        (
            "chevrolet",
            "트랙스 크로스오버",
            2025,
            "TRAX CROSSOVER (2023년 국내 출시 세대)",
            14,
        ),
        ("kgm", "토레스", 2023, "J100", 9),
    )
    for adapter_id, model, model_year, generation, chapter_count in reviewed:
        exact = client.post(
            f"/api/v1/manual-adapters/{adapter_id}/resolve",
            json={
                "model": model,
                "model_year": model_year,
                "generation": generation,
            },
        )
        adjacent_year = client.post(
            f"/api/v1/manual-adapters/{adapter_id}/resolve",
            json={
                "model": model,
                "model_year": model_year - 1,
                "generation": generation,
            },
        )

        assert exact.status_code == 200
        assert exact.json()["source_checked_at"] == "2026-08-29"
        assert len(exact.json()["chapters"]) == chapter_count
        assert adjacent_year.status_code == 404
        assert adjacent_year.json()["error"]["code"] == "manual_mapping_not_found"
