from __future__ import annotations

import pytest

from app.manual_extractive_answer import build_extractive_manual_answer
from app.manual_query import analyze_manual_question, manual_text_score


def source(excerpt: str) -> dict[str, object]:
    return {
        "document_name": "공식 취급설명서",
        "source_url": "https://example.com/manual",
        "page": 10,
        "section": None,
        "excerpt": excerpt,
    }


def test_extracts_direct_answer_and_keeps_first_source_citation() -> None:
    result = build_extractive_manual_answer(
        "부스트 모드 설명해줘",
        [
            source(
                "부스트 모드\n2C_BoostMode\n"
                "부스트 모드는 급가속을 위해 최대 10초 동안 모터 장치의 "
                "최대 성능을 발휘하도록 제어합니다.\n"
                "부스트 모드를 사용하려면 주행 중 부스트 버튼을 누르십시오."
            ),
            source("전혀 관련 없는 두 번째 검색 결과입니다."),
        ],
    )

    assert result.answer == (
        "부스트 모드는 급가속을 위해 최대 10초 동안 모터 장치의 최대 성능을 "
        "발휘하도록 제어합니다. 부스트 모드를 사용하려면 주행 중 부스트 버튼을 "
        "누르십시오. [1]"
    )
    assert result.citations == (1,)


def test_repairs_common_pdf_word_wraps_and_keeps_numbered_steps() -> None:
    result = build_extractive_manual_answer(
        "스마트키 배터리 교체",
        [
            source(
                "4-12\n편의 장치\n건전지 교체 방법\n"
                "1. 드라이버를 돌려 스\n마트키를 분리하십시오.\n"
                "2. 규격에 맞는 건전지를 구입하여 조\n립하십시오.\n"
                "3. 조립은 분해의 역순으로 하십시오."
            )
        ],
    )

    assert "스마트키를 분리하십시오." in result.answer
    assert "조립하십시오." in result.answer
    assert "3. 조립은 분해의 역순으로 하십시오." in result.answer
    assert "편의 장치" not in result.answer


def test_rejects_missing_sources_or_unsearchable_question() -> None:
    with pytest.raises(ValueError, match="at least one"):
        build_extractive_manual_answer("타이어", [])
    with pytest.raises(ValueError, match="searchable"):
        build_extractive_manual_answer("어디서?", [source("타이어 공기압")])


def test_uses_source_with_matching_action_and_cites_that_source() -> None:
    result = build_extractive_manual_answer(
        "충전구 어떻게 열어야 해?",
        [
            source("충전구 커버를 눌러 확실하게 닫으십시오."),
            source("1. 차량 시동을 끄십시오.\n2. 충전구 열림 버튼을 누르십시오."),
        ],
    )

    assert "열림 버튼" in result.answer
    assert "닫으십시오" not in result.answer
    assert result.answer.endswith("[2]")
    assert result.citations == (2,)


def test_rejects_charger_rating_as_vehicle_maximum_charging_power() -> None:
    with pytest.raises(ValueError, match="no extractive answer"):
        build_extractive_manual_answer(
            "급속 충전 최대 출력이 몇 kWh야?",
            [source("350 kW급 충전기를 사용하면 약 19분이 소요됩니다.")],
        )


def test_extracts_explicit_maximum_charging_power() -> None:
    result = build_extractive_manual_answer(
        "급속 충전 최대 출력이 몇 kW야?",
        [source("이 차량의 최대 충전 출력은 240 kW입니다.")],
    )

    assert result.answer == "이 차량의 최대 충전 출력은 240 kW입니다. [1]"


def test_extracts_long_range_battery_capacity_from_official_spec_table() -> None:
    result = build_extractive_manual_answer(
        "EV6 롱레인지 배터리 용량은 몇 kWh인가요?",
        [
            source(
                "배터리 용량 및 출력\nA−A+\n구분\n기본형\n항속형\n2WD\n2WD\n4WD\nGT\n"
                "배터리 용량(kWh)\n63\n84\n모터 최고 출력(kW)\n125\n168"
            )
        ],
    )

    assert result.answer == (
        "공식 제원표 기준 항속형(롱레인지) 배터리 용량은 84 kWh입니다. [1]"
    )


def test_drops_webhelp_text_size_control_from_answer() -> None:
    result = build_extractive_manual_answer(
        "권장 타이어 공기압 라벨은 어디 있나요?",
        [
            source(
                "타이어 공기압 라벨\nA−A+\n타이어 공기압 라벨\n"
                "권장 타이어 공기압은 운전석 옆 센터 필러의 라벨에 표기되어 있습니다."
            )
        ],
    )

    assert "A−A+" not in result.answer
    assert "운전석 옆 센터 필러" in result.answer


def test_fast_charge_question_prefers_procedure_chapter_over_general_settings() -> None:
    profile = analyze_manual_question("급속 충전은 어떻게 하나요?")
    procedure = manual_text_score(
        profile,
        "급속 충전 방법입니다. 충전 커넥터를 급속 충전 인렛에 연결하십시오.",
        section="급속 충전 방법",
    )
    settings = manual_text_score(
        profile,
        "EV 설정에서 급속 충전 목표 배터리양을 변경할 수 있습니다.",
        section="EV 설정",
    )

    assert profile.intent == "fast-charge"
    assert procedure > settings


def test_flood_question_prefers_flood_response_over_fire_response() -> None:
    profile = analyze_manual_question("전기차가 침수됐을 때 어떻게 해야 하나요?")
    flooded = manual_text_score(
        profile,
        "침수된 전기차에 접근하지 말고 안전한 장소로 대피하십시오.",
        section="전기차가 침수된 경우",
    )
    fire = manual_text_score(
        profile,
        "전기차에 화재가 발생한 경우 소방서에 연락하십시오.",
        section="전기차에 화재가 발생한 경우",
    )

    assert profile.intent == "flooded-ev"
    assert flooded > fire


@pytest.mark.parametrize(
    "question",
    [
        "스포츠모드 어떻게 바꿔?",
        "스포츠 모드",
        "SPORT 모드로 바꾸는 방법",
    ],
)
def test_drive_mode_question_extracts_operation_instead_of_table_or_ev_mode(
    question: str,
) -> None:
    result = build_extractive_manual_answer(
        question,
        [
            source(
                "드라이브 모드별 기본 설정\nECO\nNORMAL\nSPORT\n"
                "SPORT 모드는 에너지 효율이 낮아질 수 있습니다."
            ),
            source(
                "드라이브 모드 조작\n작동 방법\n"
                "스티어링 휠에 위치한 드라이브 모드 버튼을 눌러 변경하십시오.\n"
                "SPORT 모드는 스포티한 주행을 제공합니다."
            ),
            source("인포테인먼트 홈 화면에서 EV 메뉴를 선택하면 EV 모드로 진입합니다."),
        ],
    )

    assert "드라이브 모드 버튼을 눌러 변경" in result.answer
    assert "EV 메뉴" not in result.answer
    assert result.citations == (2,)


def test_drift_mode_operation_question_extracts_paddle_instruction() -> None:
    result = build_extractive_manual_answer(
        "드리프트 모드 들어가는 방법",
        [
            source(
                "드리프트 모드 (사양 적용 시)\n작동 방법\n"
                "양쪽 패들 시프트 레버를 동시에 약 3초 이상 당기십시오.\n"
                "드리프트 모드에 진입하면 클러스터에 표시등이 표시됩니다."
            )
        ],
    )

    assert result.answer == (
        "양쪽 패들 시프트 레버를 동시에 약 3초 이상 당기십시오. [1]"
    )
    assert result.citations == (1,)
