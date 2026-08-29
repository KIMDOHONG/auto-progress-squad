from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app import manual_ingestion
from app.manual_ingestion import run_pending_ingestion
from tests.test_api import vehicle_payload, verified_manual_payload


def write_manifest(
    source_root: Path,
    *,
    document_key: str = "hmc:NE1:2024",
    relative_file: str = "hmc_ne1_2024.txt",
    include_text: bool = True,
) -> None:
    source_root.mkdir(parents=True, exist_ok=True)
    if include_text:
        (source_root / relative_file).write_text(
            "타이어 공기압은 운전석 도어 라벨의 권장값을 확인하십시오.\n\n"
            "장거리 주행 전에는 냉간 상태에서 공기압을 점검하십시오.",
            encoding="utf-8",
        )
    (source_root / "manifest.json").write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "document_key": document_key,
                        "document_name": "아이오닉 5 2024 취급설명서",
                        "source_url": "https://ownersmanual.hyundai.com/manual/ioniq5-2024",
                        "file": relative_file,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_worker_marks_document_ready_and_search_returns_sources(
    client: TestClient, tmp_path: Path
) -> None:
    assert client.post("/api/v1/vehicles", json=verified_manual_payload()).status_code == 201
    source_root = tmp_path / "manuals"
    write_manifest(source_root)

    results = run_pending_ingestion(
        client.app.state.settings.database_path, source_root
    )

    assert len(results) == 1
    assert results[0].status == "ready"
    assert results[0].chunk_count == 1
    status_response = client.get(
        "/api/v1/vehicles/verified-ioniq5/manual-ingestion"
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "ready"
    assert status_response.json()["can_search"] is True

    search_response = client.post(
        "/api/v1/manual/search",
        json={"vehicle_id": "verified-ioniq5", "question": "타이어 공기압은?"},
    )
    assert search_response.status_code == 200
    payload = search_response.json()
    assert payload["answer"].startswith("공식 취급설명서에서")
    assert payload["search_engine"] == "keyword-frequency-v1"
    assert payload["sources"] == [
        {
            "document_name": "아이오닉 5 2024 취급설명서",
            "source_url": "https://ownersmanual.hyundai.com/manual/ioniq5-2024",
            "page": 1,
            "section": None,
            "excerpt": (
                "타이어 공기압은 운전석 도어 라벨의 권장값을 확인하십시오.\n\n"
                "장거리 주행 전에는 냉간 상태에서 공기압을 점검하십시오."
            ),
        }
    ]
    assert payload["generated_at"]

    no_match = client.post(
        "/api/v1/manual/search",
        json={"vehicle_id": "verified-ioniq5", "question": "견인 고리 위치"},
    )
    assert no_match.status_code == 200
    assert no_match.json()["sources"] == []
    assert "찾지 못했습니다" in no_match.json()["answer"]


def test_worker_failure_is_visible_and_retry_returns_to_pending(
    client: TestClient, tmp_path: Path
) -> None:
    assert client.post("/api/v1/vehicles", json=verified_manual_payload()).status_code == 201
    source_root = tmp_path / "manuals"
    source_root.mkdir()
    (source_root / "manifest.json").write_text(
        json.dumps({"documents": []}), encoding="utf-8"
    )

    results = run_pending_ingestion(
        client.app.state.settings.database_path, source_root
    )

    assert results[0].status == "failed"
    assert results[0].failure_code == "manifest_entry_missing"
    failed = client.get(
        "/api/v1/vehicles/verified-ioniq5/manual-ingestion"
    ).json()
    assert failed["status"] == "failed"
    assert failed["failure_code"] == "manifest_entry_missing"
    assert failed["attempt_count"] == 1

    retried = client.post(
        "/api/v1/vehicles/verified-ioniq5/manual-ingestion/retry"
    )
    assert retried.status_code == 202
    assert retried.json()["status"] == "pending"


def test_worker_rejects_manifest_file_outside_approved_root(
    client: TestClient, tmp_path: Path
) -> None:
    assert client.post("/api/v1/vehicles", json=verified_manual_payload()).status_code == 201
    source_root = tmp_path / "manuals"
    source_root.mkdir()
    (tmp_path / "outside.txt").write_text("외부 파일", encoding="utf-8")
    write_manifest(source_root, relative_file="../outside.txt", include_text=False)

    result = run_pending_ingestion(
        client.app.state.settings.database_path, source_root
    )[0]

    assert result.status == "failed"
    assert result.failure_code == "manual_source_outside_root"


def test_same_verified_document_is_indexed_once_for_multiple_vehicles(
    client: TestClient, tmp_path: Path
) -> None:
    first = verified_manual_payload("first-ioniq5")
    second = verified_manual_payload("second-ioniq5")
    assert client.post("/api/v1/vehicles", json=first).status_code == 201
    assert client.post("/api/v1/vehicles", json=second).status_code == 201
    source_root = tmp_path / "manuals"
    write_manifest(source_root)

    results = run_pending_ingestion(
        client.app.state.settings.database_path, source_root
    )

    assert len(results) == 1
    for vehicle_id in ("first-ioniq5", "second-ioniq5"):
        status_payload = client.get(
            f"/api/v1/vehicles/{vehicle_id}/manual-ingestion"
        ).json()
        assert status_payload["status"] == "ready"
        search = client.post(
            "/api/v1/manual/search",
            json={"vehicle_id": vehicle_id, "question": "공기압 점검"},
        )
        assert search.status_code == 200
        assert search.json()["sources"]


def test_identical_document_hash_reuses_existing_chunks_without_extraction(
    client: TestClient, tmp_path: Path, monkeypatch
) -> None:
    assert client.post(
        "/api/v1/vehicles", json=verified_manual_payload("first-ioniq5")
    ).status_code == 201
    source_root = tmp_path / "manuals"
    write_manifest(source_root)
    assert run_pending_ingestion(
        client.app.state.settings.database_path, source_root
    )[0].status == "ready"

    assert client.post(
        "/api/v1/vehicles", json=verified_manual_payload("second-ioniq5")
    ).status_code == 201

    def fail_if_extracted(_source_file: Path):
        raise AssertionError("동일 해시 문서를 다시 추출했습니다.")

    monkeypatch.setattr(manual_ingestion, "_extract_chunks", fail_if_extracted)
    result = run_pending_ingestion(
        client.app.state.settings.database_path, source_root
    )[0]

    assert result.status == "ready"
    assert result.chunk_count == 1
    assert client.get(
        "/api/v1/vehicles/second-ioniq5/manual-ingestion"
    ).json()["can_search"] is True


def test_changed_document_hash_atomically_replaces_shared_search_content(
    client: TestClient, tmp_path: Path
) -> None:
    assert client.post(
        "/api/v1/vehicles", json=verified_manual_payload("first-ioniq5")
    ).status_code == 201
    source_root = tmp_path / "manuals"
    write_manifest(source_root)
    database_path = client.app.state.settings.database_path
    run_pending_ingestion(database_path, source_root)

    with sqlite3.connect(database_path) as connection:
        previous_hash = connection.execute(
            "SELECT content_sha256 FROM manual_documents WHERE document_key = ?",
            ("hmc:NE1:2024",),
        ).fetchone()[0]

    assert client.post(
        "/api/v1/vehicles", json=verified_manual_payload("second-ioniq5")
    ).status_code == 201
    (source_root / "hmc_ne1_2024.txt").write_text(
        "비상 견인 고리는 트렁크 공구함에서 확인하십시오.", encoding="utf-8"
    )
    result = run_pending_ingestion(database_path, source_root)[0]

    assert result.status == "ready"
    for vehicle_id in ("first-ioniq5", "second-ioniq5"):
        search = client.post(
            "/api/v1/manual/search",
            json={"vehicle_id": vehicle_id, "question": "비상 견인 고리"},
        )
        assert search.status_code == 200
        assert "트렁크 공구함" in search.json()["sources"][0]["excerpt"]
        old_search = client.post(
            "/api/v1/manual/search",
            json={"vehicle_id": vehicle_id, "question": "타이어 공기압"},
        )
        assert old_search.json()["sources"] == []
    with sqlite3.connect(database_path) as connection:
        current_hash = connection.execute(
            "SELECT content_sha256 FROM manual_documents WHERE document_key = ?",
            ("hmc:NE1:2024",),
        ).fetchone()[0]
        assert current_hash != previous_hash
        assert connection.execute(
            "SELECT COUNT(*) FROM manual_chunks WHERE document_key = ?",
            ("hmc:NE1:2024",),
        ).fetchone()[0] == 1


def test_shared_document_is_deleted_only_after_last_vehicle_reference(
    client: TestClient, tmp_path: Path
) -> None:
    for vehicle_id in ("first-ioniq5", "second-ioniq5"):
        assert client.post(
            "/api/v1/vehicles", json=verified_manual_payload(vehicle_id)
        ).status_code == 201
    assert client.post(
        "/api/v1/vehicles", json=vehicle_payload("remaining-unverified")
    ).status_code == 201
    source_root = tmp_path / "manuals"
    write_manifest(source_root)
    database_path = client.app.state.settings.database_path
    run_pending_ingestion(database_path, source_root)

    assert client.delete("/api/v1/vehicles/first-ioniq5").status_code == 204
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM manual_documents WHERE document_key = ?",
            ("hmc:NE1:2024",),
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM manual_chunks WHERE document_key = ?",
            ("hmc:NE1:2024",),
        ).fetchone()[0] == 1

    assert client.delete("/api/v1/vehicles/second-ioniq5").status_code == 204
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM manual_documents WHERE document_key = ?",
            ("hmc:NE1:2024",),
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM manual_chunks WHERE document_key = ?",
            ("hmc:NE1:2024",),
        ).fetchone()[0] == 0


def test_textless_pdf_fails_instead_of_marking_document_ready(
    client: TestClient, tmp_path: Path
) -> None:
    assert client.post("/api/v1/vehicles", json=verified_manual_payload()).status_code == 201
    source_root = tmp_path / "manuals"
    source_root.mkdir()
    pdf_path = source_root / "empty.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with pdf_path.open("wb") as output:
        writer.write(output)
    write_manifest(source_root, relative_file="empty.pdf", include_text=False)

    result = run_pending_ingestion(
        client.app.state.settings.database_path, source_root
    )[0]

    assert result.status == "failed"
    assert result.failure_code == "manual_text_empty"
