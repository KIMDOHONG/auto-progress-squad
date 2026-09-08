from __future__ import annotations

import pytest

from app.manual_extractive_answer import build_extractive_manual_answer


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
