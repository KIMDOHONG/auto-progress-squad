import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.database import initialize_database


def vehicle_payload(vehicle_id: str, model: str = "아이오닉 5") -> dict[str, object]:
    return {
        "id": vehicle_id,
        "nickname": model,
        "manufacturer": "현대",
        "model": model,
        "model_year": 2024,
        "powertrain": "electric",
        "battery_capacity_kwh": 84,
    }


def test_health_initializes_database(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "auto-progress-squad-api",
        "version": "0.1.0",
        "database": "ready",
    }


def test_vehicle_list_reads_sqlite(client: TestClient) -> None:
    database_path = client.app.state.settings.database_path
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO vehicle_profiles (
                id, nickname, manufacturer, model, model_year,
                powertrain, fuel_grade, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "sample-bmw3",
                "주말 차량",
                "BMW",
                "330i",
                2022,
                "gasoline",
                "premium",
                1,
            ),
        )
        connection.commit()

    response = client.get("/api/v1/vehicles")

    assert response.status_code == 200
    assert response.json()["active_vehicle_id"] == "sample-bmw3"
    assert response.json()["items"][0]["fuel_grade"] == "premium"


def verified_manual_payload(vehicle_id: str = "verified-ioniq5") -> dict[str, object]:
    payload = vehicle_payload(vehicle_id)
    payload.update(
        {
            "manual_site_id": "hmc",
            "manual_model_name": "아이오닉 5",
            "manual_project_code": "NE1",
            "manual_model_year": 2024,
            "manual_image_url": "https://ownersmanual.hyundai.com/api/v2/hmc/files/6753/H_NE1_2027.png",
            "manual_verified_at": "2026-08-27T00:00:00.000Z",
        }
    )
    return payload


def test_manual_search_is_blocked_while_document_is_pending(client: TestClient) -> None:
    assert client.post("/api/v1/vehicles", json=verified_manual_payload()).status_code == 201
    response = client.post(
        "/api/v1/manual/search",
        json={"vehicle_id": "verified-ioniq5", "question": "타이어 공기압은?"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "manual_ingestion_pending"
    assert response.json()["error"]["retryable"] is True


def test_recall_lookup_fails_closed_until_source_is_configured(client: TestClient) -> None:
    response = client.get("/api/v1/vehicles/sample-bmw3/recalls")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "recall_source_not_configured"


def test_validation_uses_common_error_shape(client: TestClient) -> None:
    response = client.post(
        "/api/v1/manual/search", json={"vehicle_id": "sample-bmw3", "question": ""}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"]


def test_pages_origin_is_allowed_by_cors(client: TestClient) -> None:
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://kimdohong.github.io",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://kimdohong.github.io"


def test_vehicle_mutation_methods_are_allowed_by_cors(client: TestClient) -> None:
    for method in ("PUT", "DELETE"):
        response = client.options(
            "/api/v1/vehicles/sample-bmw3",
            headers={
                "Origin": "https://kimdohong.github.io",
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": "content-type",
            },
        )

        assert response.status_code == 200
        assert method in response.headers["access-control-allow-methods"]


def test_openapi_exposes_planned_contracts(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/health" in paths
    assert "/api/v1/vehicles" in paths
    assert "/api/v1/vehicles/{vehicle_id}/manual-ingestion" in paths
    assert "/api/v1/vehicles/{vehicle_id}/manual-ingestion/retry" in paths
    assert "/api/v1/manual/search" in paths
    assert "/api/v1/manual-adapters" in paths
    assert "/api/v1/manual-adapters/{adapter_id}/resolve" in paths
    assert "/api/v1/vehicles/{vehicle_id}/recalls" in paths

    resolve_responses = paths[
        "/api/v1/manual-adapters/{adapter_id}/resolve"
    ]["post"]["responses"]
    assert {"404", "409", "503"}.issubset(resolve_responses)


def test_vehicle_crud_and_active_selection(client: TestClient) -> None:
    first = client.post("/api/v1/vehicles", json=vehicle_payload("ioniq5"))
    second = client.post(
        "/api/v1/vehicles",
        json={
            "id": "bmw330i",
            "nickname": "주말 차량",
            "manufacturer": "BMW",
            "model": "330i",
            "model_year": 2022,
            "powertrain": "gasoline",
            "fuel_grade": "premium",
        },
    )

    assert first.status_code == 201
    assert first.json()["is_active"] is True
    assert second.status_code == 201
    assert second.json()["is_active"] is False

    activated = client.put("/api/v1/vehicles/bmw330i/active")
    assert activated.status_code == 200
    assert activated.json()["is_active"] is True

    updated_payload = second.json()
    updated_payload["model"] = "330i M Sport"
    updated_payload.pop("id")
    updated_payload.pop("is_active")
    updated = client.put("/api/v1/vehicles/bmw330i", json=updated_payload)
    assert updated.status_code == 200
    assert updated.json()["model"] == "330i M Sport"
    assert updated.json()["is_active"] is True

    deleted = client.delete("/api/v1/vehicles/bmw330i")
    assert deleted.status_code == 204
    remaining = client.get("/api/v1/vehicles").json()
    assert remaining["active_vehicle_id"] == "ioniq5"


def test_vehicle_limit_and_last_vehicle_guards(client: TestClient) -> None:
    for index in range(3):
        response = client.post(
            "/api/v1/vehicles", json=vehicle_payload(f"vehicle-{index}", f"EV {index}")
        )
        assert response.status_code == 201

    over_limit = client.post(
        "/api/v1/vehicles", json=vehicle_payload("vehicle-3", "EV 3")
    )
    assert over_limit.status_code == 409
    assert over_limit.json()["error"]["code"] == "vehicle_limit_reached"

    assert client.delete("/api/v1/vehicles/vehicle-2").status_code == 204
    assert client.delete("/api/v1/vehicles/vehicle-1").status_code == 204
    last_delete = client.delete("/api/v1/vehicles/vehicle-0")
    assert last_delete.status_code == 409
    assert last_delete.json()["error"]["code"] == "last_vehicle_required"


def test_vehicle_mutations_report_not_found_and_invalid_energy_fields(
    client: TestClient,
) -> None:
    missing = client.put("/api/v1/vehicles/missing/active")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "vehicle_not_found"

    invalid = vehicle_payload("invalid")
    invalid["fuel_grade"] = "premium"
    response = client.post("/api/v1/vehicles", json=invalid)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_hydrogen_vehicle_profile_is_supported(client: TestClient) -> None:
    response = client.post(
        "/api/v1/vehicles",
        json={
            "id": "nexo-2021",
            "nickname": "가족 수소차",
            "manufacturer": "현대",
            "model": "넥쏘",
            "model_year": 2021,
            "powertrain": "hydrogen",
        },
    )

    assert response.status_code == 201
    assert response.json()["powertrain"] == "hydrogen"
    assert response.json()["fuel_grade"] is None
    assert response.json()["battery_capacity_kwh"] is None

    invalid = client.post(
        "/api/v1/vehicles",
        json={
            "id": "invalid-hydrogen",
            "nickname": "잘못된 수소차",
            "manufacturer": "현대",
            "model": "넥쏘",
            "model_year": 2021,
            "powertrain": "hydrogen",
            "fuel_grade": "premium",
        },
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"


def test_verified_manual_metadata_is_persisted_and_domain_checked(
    client: TestClient,
) -> None:
    payload = verified_manual_payload()

    response = client.post("/api/v1/vehicles", json=payload)

    assert response.status_code == 201
    assert response.json()["manual_project_code"] == "NE1"
    assert client.get("/api/v1/vehicles").json()["items"][0]["manual_site_id"] == "hmc"

    payload["id"] = "invalid-image-domain"
    payload["manual_image_url"] = "https://example.com/car.png"
    invalid = client.post("/api/v1/vehicles", json=payload)
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"


def test_verified_manual_queues_ingestion_and_retry_is_explicit(
    client: TestClient,
) -> None:
    assert client.post("/api/v1/vehicles", json=verified_manual_payload()).status_code == 201

    status_response = client.get(
        "/api/v1/vehicles/verified-ioniq5/manual-ingestion"
    )
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["status"] == "pending"
    assert status_payload["document_key"] == "hmc:NE1:2024"
    assert status_payload["source_url"] == (
        "https://ownersmanual.hyundai.com/manual/"
        "%EC%95%84%EC%9D%B4%EC%98%A4%EB%8B%89%205"
        "?projCode=NE1&year=2024&langCode=ko_KR&countryCode=A99"
    )
    assert status_payload["can_search"] is False
    assert status_payload["attempt_count"] == 0

    retry_response = client.post(
        "/api/v1/vehicles/verified-ioniq5/manual-ingestion/retry"
    )
    assert retry_response.status_code == 202
    assert retry_response.json()["status"] == "pending"
    assert retry_response.json()["attempt_count"] == 1


def test_unverified_vehicle_reports_unavailable_and_cannot_retry(
    client: TestClient,
) -> None:
    assert client.post("/api/v1/vehicles", json=vehicle_payload("unverified")).status_code == 201

    status_response = client.get("/api/v1/vehicles/unverified/manual-ingestion")
    assert status_response.status_code == 200
    assert status_response.json() == {
        "vehicle_id": "unverified",
        "status": "unavailable",
        "document_key": None,
        "source_url": None,
        "attempt_count": 0,
        "failure_code": None,
        "failure_message": None,
        "queued_at": None,
        "updated_at": None,
        "ready_at": None,
        "can_search": False,
    }
    retry_response = client.post(
        "/api/v1/vehicles/unverified/manual-ingestion/retry"
    )
    assert retry_response.status_code == 409
    assert retry_response.json()["error"]["code"] == "verified_manual_required"


def test_manual_identity_change_resets_job_and_vehicle_delete_cascades(
    client: TestClient,
) -> None:
    first_payload = verified_manual_payload()
    assert client.post("/api/v1/vehicles", json=first_payload).status_code == 201
    assert client.post("/api/v1/vehicles/verified-ioniq5/manual-ingestion/retry").json()["attempt_count"] == 1

    updated_payload = {key: value for key, value in first_payload.items() if key != "id"}
    updated_payload.update(
        {
            "model": "아이오닉 5 N",
            "manual_model_name": "아이오닉 5 N",
            "manual_project_code": "NE1N",
        }
    )
    updated = client.put("/api/v1/vehicles/verified-ioniq5", json=updated_payload)
    assert updated.status_code == 200
    ingestion = client.get(
        "/api/v1/vehicles/verified-ioniq5/manual-ingestion"
    ).json()
    assert ingestion["document_key"] == "hmc:NE1N:2024"
    assert ingestion["attempt_count"] == 0

    assert client.post("/api/v1/vehicles", json=vehicle_payload("second")).status_code == 201
    assert client.delete("/api/v1/vehicles/verified-ioniq5").status_code == 204
    database_path = client.app.state.settings.database_path
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM manual_ingestion_jobs WHERE vehicle_id = ?",
            ("verified-ioniq5",),
        ).fetchone()[0] == 0


def test_schema_v2_migration_preserves_profiles_and_adds_hydrogen(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.db"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE vehicle_profiles (
                id TEXT PRIMARY KEY,
                nickname TEXT NOT NULL,
                manufacturer TEXT NOT NULL,
                model TEXT NOT NULL,
                model_year INTEGER NOT NULL,
                powertrain TEXT NOT NULL CHECK (
                    powertrain IN ('electric', 'gasoline', 'diesel', 'hybrid')
                ),
                fuel_grade TEXT,
                battery_capacity_kwh REAL,
                is_active INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO vehicle_profiles (
                id, nickname, manufacturer, model, model_year, powertrain, is_active
            ) VALUES ('legacy-ev', '기존 차량', '현대', '아이오닉 5', 2024, 'electric', 1);
            """
        )

    initialize_database(database_path)

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT model FROM vehicle_profiles WHERE id = 'legacy-ev'"
        ).fetchone()[0] == "아이오닉 5"
        connection.execute(
            """
            INSERT INTO vehicle_profiles (
                id, nickname, manufacturer, model, model_year, powertrain, is_active
            ) VALUES ('nexo', '수소차', '현대', '넥쏘', 2021, 'hydrogen', 0)
            """
        )
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(vehicle_profiles)")
        }
        assert "manual_project_code" in columns
        assert "manual_image_url" in columns
        ingestion_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(manual_ingestion_jobs)")
        }
        assert {"vehicle_id", "document_key", "status", "source_url"} <= ingestion_columns
