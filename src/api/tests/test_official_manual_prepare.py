from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.official_manual_prepare import (
    FetchedResource,
    OfficialManualPreparationError,
    prepare_vehicle_manual,
)
from tests.test_api import vehicle_payload, verified_manual_payload


def _create(client, payload: dict[str, object]) -> None:
    response = client.post("/api/v1/vehicles", json=payload)
    assert response.status_code == 201, response.text


def _resource(url: str, content: str | bytes, content_type: str = "") -> FetchedResource:
    return FetchedResource(
        final_url=url,
        content=content.encode("utf-8") if isinstance(content, str) else content,
        content_type=content_type,
    )


def test_prepares_official_pdf_and_indexes_it(client, tmp_path: Path, monkeypatch) -> None:
    payload = verified_manual_payload("pdf-hmc")
    payload["manual_project_code"] = "FE"
    _create(client, payload)
    pdf_path = tmp_path / "manual.pdf"
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with pdf_path.open("wb") as stream:
        writer.write(stream)
    pdf_bytes = pdf_path.read_bytes()

    def fetch(url: str, limit: int) -> FetchedResource:
        assert limit > 0
        if "/owners-manuals?" in url:
            return _resource(
                url,
                json.dumps({"omManual": {"pdfManual": "https://ownersmanual.hyundai.com/full_pdf/FE/2024/ko_KR"}}),
                "application/json",
            )
        return _resource(url, pdf_bytes, "application/pdf")

    monkeypatch.setattr(
        "app.official_manual_prepare.ingest_vehicle_manual",
        lambda *_args, **_kwargs: type("Result", (), {"status": "ready", "failure_code": None, "chunk_count": 7})(),
    )
    source_root = tmp_path / "manuals"
    result = prepare_vehicle_manual(
        client.app.state.settings.database_path, source_root, "pdf-hmc", fetch=fetch
    )

    assert result.source_kind == "pdf"
    assert result.source_count == 1
    assert result.chunk_count == 7
    manifest = json.loads((source_root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["documents"][0]["document_key"] == "hmc:FE:2024"
    assert manifest["documents"][0]["file"] == "hmc/FE/2024/owners-manual.pdf"
    assert (source_root / "hmc/FE/2024/owners-manual.pdf").read_bytes() == pdf_bytes


def test_prepares_webhelp_topics_when_pdf_is_missing(client, tmp_path: Path) -> None:
    payload = verified_manual_payload("webhelp-kia")
    payload.update(
        {
            "manufacturer": "기아",
            "model": "EV6",
            "model_year": 2026,
            "manual_site_id": "kia",
            "manual_model_name": "EV6",
            "manual_project_code": "CV1",
            "manual_model_year": 2026,
            "manual_image_url": "https://ownersmanual.kia.com/api/v2/kia/files/1/ev6.png",
        }
    )
    _create(client, payload)
    toc_url = "https://ownersmanual.kia.com/full_webhelp/CV1/2026/ko_KR/toc.html"
    topic_url = "https://ownersmanual.kia.com/full_webhelp/CV1/2026/ko_KR/topics/chapter1_1.html"
    nested_topic_url = (
        "https://ownersmanual.kia.com/full_webhelp/CV1/2026/ko_KR/topics/chapter1_1_1.html"
    )
    stale_topic_url = (
        "https://ownersmanual.kia.com/full_webhelp/CV1/2026/ko_KR/topics/chapter1_1_404.html"
    )

    def fetch(url: str, _limit: int) -> FetchedResource:
        if "/owners-manuals?" in url:
            return _resource(url, json.dumps({"omManual": {"webhelpToc": toc_url}}))
        if url == toc_url:
            return _resource(url, '<a href="./topics/chapter1_1.html"><h2>충전</h2></a>')
        if url == topic_url:
            return _resource(
                url,
                '<nav><a href="chapter9_9.html">전역 메뉴</a></nav>'
                '<div class="topic-contents main-page"><h2>전기 자동차 충전</h2>'
                '<div class="containd-section"><a href="chapter1_1_1.html">충전 연결 방법</a>'
                '<a href="chapter1_1_404.html">삭제된 세부 항목</a>'
                "<p>관련 세부 항목을 선택하십시오.</p></div></div>",
            )
        if url == nested_topic_url:
            return _resource(
                url,
                '<div class="topic-contents"><h2>충전 연결 방법</h2>'
                '<p>충전 커넥터를 연결하십시오.</p>'
                '<a href="chapter1_1.html">전기 자동차 충전</a></div>',
            )
        if url == stale_topic_url:
            raise OfficialManualPreparationError(
                "official_manual_fetch_failed", "삭제된 공식 세부 페이지"
            )
        raise AssertionError(url)

    source_root = tmp_path / "manuals"
    result = prepare_vehicle_manual(
        client.app.state.settings.database_path, source_root, "webhelp-kia", fetch=fetch
    )

    assert result.source_kind == "webhelp"
    assert result.source_count == 2
    assert result.chunk_count >= 1
    manifest = json.loads((source_root / "manifest.json").read_text(encoding="utf-8"))
    chapters = manifest["documents"][0]["chapters"]
    assert [chapter["source_url"] for chapter in chapters] == [topic_url, nested_topic_url]
    assert chapters[0]["title"] == "전기 자동차 충전"
    assert chapters[1]["title"] == "충전 연결 방법"
    text = (source_root / chapters[1]["file"]).read_text(encoding="utf-8")
    assert "충전 커넥터를 연결하십시오." in text

    search = client.post(
        "/api/v1/manual/search",
        json={"vehicle_id": "webhelp-kia", "question": "충전 커넥터 연결"},
    )
    assert search.status_code == 200
    assert search.json()["sources"][0]["source_url"] == nested_topic_url
    assert search.json()["sources"][0]["section"] == "충전 연결 방법"


def test_rejects_manual_redirect_to_another_host(client, tmp_path: Path) -> None:
    payload = verified_manual_payload("redirected")
    payload["manual_project_code"] = "FE"
    _create(client, payload)

    def fetch(url: str, _limit: int) -> FetchedResource:
        if "/owners-manuals?" in url:
            return _resource(
                url,
                json.dumps({"omManual": {"pdfManual": "https://ownersmanual.hyundai.com/full_pdf/FE/2024/ko_KR"}}),
            )
        return _resource("https://example.com/manual.pdf", b"%PDF-1.4")

    with pytest.raises(OfficialManualPreparationError) as caught:
        prepare_vehicle_manual(
            client.app.state.settings.database_path,
            tmp_path / "manuals",
            "redirected",
            fetch=fetch,
        )
    assert caught.value.code == "official_manual_url_not_allowed"


def test_rejects_unconnected_manufacturer(client, tmp_path: Path) -> None:
    payload = vehicle_payload("manual-bmw", "330i")
    payload.update(
        {
            "manufacturer": "BMW",
            "powertrain": "gasoline",
            "battery_capacity_kwh": None,
            "fuel_grade": "premium",
        }
    )
    _create(client, payload)
    with pytest.raises(OfficialManualPreparationError) as caught:
        prepare_vehicle_manual(
            client.app.state.settings.database_path,
            tmp_path / "manuals",
            "manual-bmw",
            fetch=lambda *_args: pytest.fail("network must not be called"),
        )
    assert caught.value.code == "verified_hkg_manual_required"
