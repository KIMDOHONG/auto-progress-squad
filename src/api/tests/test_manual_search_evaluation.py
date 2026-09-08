from pathlib import Path

import pytest

from app.manual_search_evaluation import (
    evaluate_keyword_search,
    load_evaluation_dataset,
)
from app.manual_ingestion import rank_manual_chunks


def evaluation_path() -> Path:
    return Path(__file__).parents[3] / "tests" / "fixtures" / (
        "manual-search-evaluation.v1.json"
    )


def test_keyword_search_baseline_is_reproducible() -> None:
    result = evaluate_keyword_search(load_evaluation_dataset(evaluation_path()))

    assert result["question_count"] == 8
    assert result["limit"] == 3
    assert result["hit_rate_at_k"] == 1.0
    assert result["mean_reciprocal_rank"] == 1.0
    assert all(case["rank"] == 1 for case in result["cases"])


def test_evaluation_rejects_invalid_limit() -> None:
    dataset = load_evaluation_dataset(evaluation_path())

    with pytest.raises(ValueError, match="limit must be at least 1"):
        evaluate_keyword_search(dataset, limit=0)


@pytest.mark.parametrize(
    ("question", "content"),
    [
        ("스마트키 배터리 교체", "스마트 키 건전지 교체 방법"),
        ("12V 배터리 방전", "12 V 배터리 방전 시 점프 스타트 방법"),
    ],
)
def test_keyword_search_normalizes_spacing_and_battery_synonym(
    question: str,
    content: str,
) -> None:
    results = rank_manual_chunks(
        [
            {
                "document_name": "공식 취급설명서",
                "source_url": "https://ownersmanual.hyundai.com/manual/test",
                "page": 10,
                "section": None,
                "content": content,
            },
            {
                "document_name": "공식 취급설명서",
                "source_url": "https://ownersmanual.hyundai.com/manual/test",
                "page": 20,
                "section": None,
                "content": "일반 배터리 관리 안내",
            },
        ],
        question,
        1,
    )

    assert results[0]["page"] == 10


@pytest.mark.parametrize(
    ("question", "expected_page"),
    [
        ("충전구 어떻게 열어야 해?", 10),
        ("충전구를 어떻게 닫아야 해?", 20),
        ("시동은 걸었는데 출발은 어떻게 해?", 30),
        ("다음 출발 시간은 어떻게 설정해?", 40),
        ("급속 충전 최대 출력이 몇 kW야?", 50),
    ],
)
def test_keyword_search_distinguishes_action_and_measurement_intent(
    question: str,
    expected_page: int,
) -> None:
    contents = [
        (10, "연료충전구 여는 방법입니다. 열림 버튼을 눌러 여십시오."),
        (20, "연료충전구 닫는 방법입니다. 커버를 눌러 닫으십시오."),
        (
            30,
            "차량 시동 및 출발하기. 브레이크 페달을 밟고 D(주행)로 "
            "변속한 후 가속 페달을 천천히 밟아 주행을 시작하십시오.",
        ),
        (40, "다음 출발 시간을 선택하고 출발 일정을 설정하십시오."),
        (50, "최대 충전 출력은 240 kW입니다."),
        (60, "급속 충전기로 충전하는 일반적인 방법입니다."),
    ]
    rows = [
        {
            "document_name": "공식 취급설명서",
            "source_url": "https://ownersmanual.hyundai.com/manual/test",
            "page": page,
            "section": None,
            "content": content,
        }
        for page, content in contents
    ]

    results = rank_manual_chunks(rows, question, 1)

    assert results[0]["page"] == expected_page


@pytest.mark.parametrize(
    "question",
    [
        "스포츠모드 어떻게 바꿔?",
        "스포츠 모드",
        "SPORT 모드로 바꾸는 방법",
    ],
)
def test_keyword_search_prefers_drive_mode_operation_over_similar_mode_text(
    question: str,
) -> None:
    rows = [
        {
            "document_name": "EV6 2026 취급설명서",
            "source_url": "https://example.com/pedal",
            "page": 10,
            "section": "기타 주의 사항",
            "content": "차량을 바꿔가며 운전할 때는 페달 위치를 확인하십시오.",
        },
        {
            "document_name": "EV6 2026 취급설명서",
            "source_url": "https://example.com/ev-mode",
            "page": 20,
            "section": "EV 모드",
            "content": "인포테인먼트 홈 화면에서 EV 메뉴를 선택하면 EV 모드로 진입합니다.",
        },
        {
            "document_name": "EV6 2026 취급설명서",
            "source_url": "https://example.com/drive-mode-table",
            "page": 30,
            "section": "드라이브 모드(DRIVE MODE)",
            "content": "드라이브 모드별 기본 설정 표에는 ECO, NORMAL, SPORT가 있습니다.",
        },
        {
            "document_name": "EV6 2026 취급설명서",
            "source_url": "https://example.com/drive-mode-operation",
            "page": 40,
            "section": "드라이브 모드(DRIVE MODE)",
            "content": (
                "드라이브 모드 조작. 스티어링 휠에 위치한 드라이브 모드 "
                "버튼을 눌러 변경하십시오. SPORT 모드는 스포티한 주행을 제공합니다."
            ),
        },
    ]

    results = rank_manual_chunks(rows, question, 3)

    assert results[0]["page"] == 40
