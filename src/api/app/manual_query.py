from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


ManualQueryIntent = Literal[
    "general",
    "open",
    "close",
    "drive-away",
    "departure-schedule",
    "charging-power",
    "charging-lock",
    "tire-pressure-location",
    "jump-start",
]

_TOKEN_PATTERN = re.compile(r"[0-9]+(?:[.,][0-9]+)*|[a-zA-Z]+|[가-힣]{2,}")
_CHARGING_POWER_PATTERN = re.compile(r"\d+(?:[.,]\d+)?\s*k\s*w(?!h)", re.IGNORECASE)
_KOREAN_SUFFIXES = (
    "에서는",
    "으로는",
    "에게서",
    "까지는",
    "부터는",
    "에서",
    "으로",
    "에게",
    "까지",
    "부터",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "의",
    "에",
)
_STOP_TOKENS = {
    "관련",
    "내용",
    "방법",
    "뭐야",
    "무엇",
    "설명",
    "설명해줘",
    "어디",
    "어디서",
    "알려줘",
    "확인",
    "하나요",
    "해주세요",
    "어떻게",
    "해야해",
    "해야하지",
    "하는데",
    "하려고",
    "꽂으려고",
    "걸었는데",
    "정도",
    "받을",
    "있어",
    "있을",
}
_TERM_EQUIVALENTS = {
    "배터리": ("건전지",),
    "건전지": ("배터리",),
    "천천히": ("완속", "휴대용"),
    "완속": ("천천히",),
    "아이": ("어린이",),
    "아이들": ("어린이",),
    "어린이": ("아이",),
    "뒷문": ("뒷도어", "뒷좌석도어"),
    "뒷도어": ("뒷문", "뒷좌석도어"),
}
_OPEN_PATTERNS = (
    "여는방법",
    "열림버튼",
    "여십시오",
    "열어",
    "열고",
    "열립니다",
)
_CLOSE_PATTERNS = (
    "닫는방법",
    "닫으십시오",
    "닫고",
    "닫아",
    "닫힙니다",
    "잠그십시오",
)
_DRIVE_PATTERNS = (
    "차량시동및출발",
    "출발하는경우",
    "주행을시작",
    "주행시작",
    "d주행",
    "d단",
    "가속페달을천천히",
    "브레이크페달에서발을떼",
)
_DIRECT_CHARGING_POWER_PATTERNS = (
    "최대충전출력",
    "충전출력",
    "최대수전출력",
)
_SCHEDULE_PATTERNS = (
    "다음출발시간",
    "출발시간을선택",
    "출발일정",
    "예약충전",
    "예약공조",
)
_CHARGING_LOCK_PATTERNS = (
    "충전커넥터잠금모드",
    "충전커넥터잠금모드설정",
    "상시잠금",
    "충전중잠금",
    "충전커넥터를잠금",
)
_CHARGING_LOCK_SETTING_PATTERNS = (
    "ev설정",
    "상세기능을선택",
    "사용안함",
    "항상자동으로잠깁니다",
)
_TIRE_PRESSURE_LOCATION_PATTERNS = (
    "타이어표준공기압라벨",
    "타이어공기압라벨",
    "운전석b필라",
    "운전석옆센터필러",
    "공기압제원",
    "운전석도어프레임",
    "운전석도어라벨",
    "부착된라벨",
)
_JUMP_START_PATTERNS = (
    "점프스타트",
    "비상시동",
    "보조배터리",
    "점프케이블",
)


@dataclass(frozen=True, slots=True)
class ManualQuestionProfile:
    question: str
    terms: tuple[str, ...]
    intent: ManualQueryIntent
    expects_numeric_power: bool = False
    unit_was_kwh: bool = False


def compact_manual_text(value: str) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]+", "", value.lower())


def _contains_any(compact: str, patterns: tuple[str, ...]) -> bool:
    return any(compact_manual_text(pattern) in compact for pattern in patterns)


def _normalize_token(raw_token: str) -> str:
    token = raw_token.lower()
    if re.fullmatch(r"[가-힣]+", token):
        for suffix in _KOREAN_SUFFIXES:
            if token.endswith(suffix) and len(token) > len(suffix) + 1:
                return token[: -len(suffix)]
    return token


def analyze_manual_question(question: str) -> ManualQuestionProfile:
    lowered = question.lower()
    compact = compact_manual_text(question)
    terms: list[str] = []
    for raw_token in _TOKEN_PATTERN.findall(lowered):
        token = _normalize_token(raw_token)
        if token in _STOP_TOKENS or len(token) < 2:
            continue
        if token not in terms:
            terms.append(token)

    asks_open = _contains_any(compact, ("열어", "열기", "여는", "열림"))
    asks_close = _contains_any(compact, ("닫아", "닫기", "닫는", "잠가", "잠그"))
    asks_departure = "출발" in compact
    asks_schedule = _contains_any(compact, ("출발시간", "출발일정", "예약출발"))
    asks_charging = _contains_any(compact, ("충전", "충전기", "충전구"))
    asks_power = _contains_any(compact, ("최대출력", "충전출력", "최대몇", "몇kwh", "몇kw"))
    asks_charging_lock = "충전커넥터" in compact and _contains_any(
        compact, ("잠금", "잠그", "락")
    )
    asks_tire_pressure_location = (
        "타이어" in compact
        and "공기압" in compact
        and _contains_any(compact, ("권장", "추천", "어디", "위치", "확인"))
    )
    asks_jump_start = (
        _contains_any(compact, ("12v", "배터리", "방전"))
        and _contains_any(compact, ("점프", "시동", "방전"))
    )

    intent: ManualQueryIntent = "general"
    if asks_jump_start:
        intent = "jump-start"
    elif asks_tire_pressure_location:
        intent = "tire-pressure-location"
    elif asks_charging_lock:
        intent = "charging-lock"
    elif asks_charging and asks_power:
        intent = "charging-power"
    elif asks_open and not asks_close:
        intent = "open"
    elif asks_close and not asks_open:
        intent = "close"
    elif asks_departure and asks_schedule:
        intent = "departure-schedule"
    elif asks_departure:
        intent = "drive-away"

    if intent == "drive-away":
        terms = [term for term in terms if term not in {"시동", "걸었는데"}]
        if "출발" not in terms:
            terms.append("출발")
    if intent == "charging-power" and "kw" not in terms:
        terms.append("kw")
    if intent == "jump-start":
        for term in ("점프", "시동"):
            if term not in terms:
                terms.append(term)

    return ManualQuestionProfile(
        question=question,
        terms=tuple(terms),
        intent=intent,
        expects_numeric_power=intent == "charging-power",
        unit_was_kwh="kwh" in compact,
    )


def _term_count(lowered: str, compact: str, term: str) -> int:
    variants = (term, *_TERM_EQUIVALENTS.get(term, ()))
    return max(
        max(
            lowered.count(variant),
            compact.count(compact_manual_text(variant)),
        )
        for variant in variants
    )


def manual_text_score(
    profile: ManualQuestionProfile,
    text: str,
    *,
    section: str | None = None,
) -> int:
    lowered = text.lower()
    compact = compact_manual_text(text)
    counts = [_term_count(lowered, compact, term) for term in profile.terms]
    coverage = sum(1 for count in counts if count)
    score = coverage * 12 + sum(
        min(count, 4) * max(len(term), 2)
        for term, count in zip(profile.terms, counts)
    )

    leading = compact_manual_text(" ".join(filter(None, (section, text[:180]))))
    score += sum(
        6
        for term, count in zip(profile.terms, counts)
        if count and compact_manual_text(term) in leading
    )

    has_open = _contains_any(compact, _OPEN_PATTERNS)
    has_close = _contains_any(compact, _CLOSE_PATTERNS)
    has_drive = _contains_any(compact, _DRIVE_PATTERNS)
    has_schedule = _contains_any(compact, _SCHEDULE_PATTERNS)

    if profile.intent == "open":
        score += 90 if has_open else -45
        if has_close and not has_open:
            score -= 100
        if "연료충전구여는방법" in compact:
            score += 160
        if "비상시" in compact and "비상" not in compact_manual_text(profile.question):
            score -= 120
    elif profile.intent == "close":
        score += 90 if has_close else -45
        if has_open and not has_close:
            score -= 100
    elif profile.intent == "drive-away":
        drive_match_count = sum(
            compact_manual_text(pattern) in compact for pattern in _DRIVE_PATTERNS
        )
        score += drive_match_count * 55 if has_drive else -50
        if has_schedule and not has_drive:
            score -= 160
    elif profile.intent == "departure-schedule":
        score += 100 if has_schedule else -40
    elif profile.intent == "charging-power":
        if _CHARGING_POWER_PATTERN.search(text):
            score += 180
        else:
            score -= 90
    elif profile.intent == "charging-lock":
        score += 180 if _contains_any(compact, _CHARGING_LOCK_PATTERNS) else -80
        setting_matches = sum(
            compact_manual_text(pattern) in compact
            for pattern in _CHARGING_LOCK_SETTING_PATTERNS
        )
        score += setting_matches * 120
        if "참고하십시오" in compact and not _contains_any(
            compact, _CHARGING_LOCK_SETTING_PATTERNS
        ):
            score -= 80
    elif profile.intent == "tire-pressure-location":
        location_matches = sum(
            compact_manual_text(pattern) in compact
            for pattern in _TIRE_PRESSURE_LOCATION_PATTERNS
        )
        score += location_matches * 100 if location_matches else -80
    elif profile.intent == "jump-start":
        jump_matches = sum(
            compact_manual_text(pattern) in compact for pattern in _JUMP_START_PATTERNS
        )
        score += jump_matches * 110 if jump_matches else -120
        if "스마트키" in compact and not jump_matches:
            score -= 160

    return score


def manual_segment_score(profile: ManualQuestionProfile, segment: str) -> int:
    compact = compact_manual_text(segment)
    has_open = _contains_any(compact, _OPEN_PATTERNS)
    has_close = _contains_any(compact, _CLOSE_PATTERNS)
    has_drive = _contains_any(compact, _DRIVE_PATTERNS)
    has_schedule = _contains_any(compact, _SCHEDULE_PATTERNS)

    if profile.expects_numeric_power:
        if not _CHARGING_POWER_PATTERN.search(segment):
            return 0
        if not _contains_any(compact, _DIRECT_CHARGING_POWER_PATTERNS):
            return 0
    if profile.intent == "open" and (not has_open or (has_close and not has_open)):
        return 0
    if profile.intent == "close" and (not has_close or (has_open and not has_close)):
        return 0
    if profile.intent == "drive-away" and (not has_drive or (has_schedule and not has_drive)):
        return 0
    if profile.intent == "departure-schedule" and not has_schedule:
        return 0
    if profile.intent == "charging-lock" and not _contains_any(
        compact, _CHARGING_LOCK_PATTERNS
    ):
        return 0
    if profile.intent == "tire-pressure-location" and not _contains_any(
        compact, _TIRE_PRESSURE_LOCATION_PATTERNS
    ):
        return 0
    if profile.intent == "jump-start" and not _contains_any(
        compact, _JUMP_START_PATTERNS
    ):
        return 0

    score = manual_text_score(profile, segment)
    return max(score, 0)


def manual_no_answer_message(profile: ManualQuestionProfile) -> str:
    if profile.intent == "charging-power":
        unit_note = (
            " 충전 출력은 kW, 배터리 용량과 충전 에너지는 kWh로 구분합니다."
            if profile.unit_was_kwh
            else ""
        )
        return (
            "공식 취급설명서 검색 결과에서 요청한 최대 충전 출력 수치를 "
            f"확인하지 못했습니다.{unit_note} 공식 차량 제원을 확인해 주세요."
        )
    return (
        "공식 취급설명서 검색 결과에서 질문에 정확히 답할 수 있는 문장을 "
        "확인하지 못했습니다. 아래 원문 근거를 확인해 주세요."
    )
