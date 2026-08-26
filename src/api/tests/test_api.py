import sqlite3

from fastapi.testclient import TestClient


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


def test_openapi_exposes_planned_contracts(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/health" in paths
    assert "/api/v1/vehicles" in paths
    assert "/api/v1/manual/search" in paths
    assert "/api/v1/vehicles/{vehicle_id}/recalls" in paths
