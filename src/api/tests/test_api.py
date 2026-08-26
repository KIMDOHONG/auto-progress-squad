import sqlite3

from fastapi.testclient import TestClient


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


def test_manual_search_fails_closed_until_rag_is_configured(client: TestClient) -> None:
    response = client.post(
        "/api/v1/manual/search",
        json={"vehicle_id": "sample-bmw3", "question": "타이어 공기압은?"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "manual_rag_not_configured"
    assert response.json()["error"]["retryable"] is False


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
    assert "/api/v1/manual/search" in paths
    assert "/api/v1/vehicles/{vehicle_id}/recalls" in paths


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
