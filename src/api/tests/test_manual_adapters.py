import pytest

from app.manual_adapters import (
    BmwDriverGuideAdapter,
    ManualAdapterError,
    ManualLookupRequest,
    get_manual_adapter,
    mask_vin,
)


def test_manual_adapter_capabilities_are_public_and_fail_closed(client) -> None:
    response = client.get("/api/v1/manual-adapters")

    assert response.status_code == 200
    items = {item["id"]: item for item in response.json()["items"]}
    assert set(items) == {"bmw", "chevrolet", "kgm"}
    assert items["bmw"] == {
        "id": "bmw",
        "manufacturer": "BMW",
        "official_url": (
            "https://www.bmw.co.kr/ko/topics/owners/online-manual/"
            "bmw-driver-guide.html"
        ),
        "identification_mode": "vin",
        "integration_mode": "server-only",
        "lookup_status": "permission-required",
        "stores_raw_identifier": False,
        "image_policy": "none",
        "failure_code": "bmw_driver_guide_permission_required",
    }
    assert items["chevrolet"]["lookup_status"] == "planned"
    assert items["kgm"]["lookup_status"] == "planned"


def test_bmw_lookup_requires_vin_without_guessing() -> None:
    adapter = BmwDriverGuideAdapter()

    with pytest.raises(ManualAdapterError) as error:
        adapter.resolve(ManualLookupRequest(manufacturer_id="bmw"))

    assert error.value.code == "vin_required"


def test_bmw_lookup_does_not_leak_or_send_raw_vin_while_disabled() -> None:
    vin = "WBA00000000000000"  # synthetic test identifier, not a real vehicle VIN
    request = ManualLookupRequest(manufacturer_id="bmw", vin=vin)

    assert vin not in repr(request)
    assert request.masked_identifier == "WBA**********0000"
    assert mask_vin(vin.lower()) == "WBA**********0000"

    with pytest.raises(ManualAdapterError) as error:
        get_manual_adapter("bmw").resolve(request)

    assert error.value.code == "bmw_driver_guide_permission_required"
    assert vin not in str(error.value)


@pytest.mark.parametrize(
    "vin",
    ["WBA123", "WBA6N1109MFK7959I", "WBA6N1109MFK7959-"],
)
def test_bmw_vin_validation_is_explicit_and_does_not_echo_input(vin: str) -> None:
    with pytest.raises(ManualAdapterError) as error:
        BmwDriverGuideAdapter().resolve(
            ManualLookupRequest(manufacturer_id="bmw", vin=vin)
        )

    assert error.value.code == "invalid_vin"
    assert vin not in str(error.value)
