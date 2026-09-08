from app.manual_hybrid_search import merge_manual_search_results


def source(page: int) -> dict[str, object]:
    return {
        "document_name": "테스트 설명서",
        "source_url": "https://example.com/manual",
        "page": page,
        "section": None,
        "excerpt": f"{page}쪽 내용",
    }


def test_hybrid_merge_rewards_agreement_and_keeps_keyword_first() -> None:
    result = merge_manual_search_results(
        [source(1), source(2), source(3)],
        [source(2), source(4), source(1)],
        limit=3,
    )

    assert [item["page"] for item in result] == [1, 2, 3]


def test_hybrid_merge_rejects_invalid_limit() -> None:
    try:
        merge_manual_search_results([], [], limit=0)
    except ValueError as error:
        assert str(error) == "limit must be at least 1"
    else:
        raise AssertionError("invalid limit was accepted")
