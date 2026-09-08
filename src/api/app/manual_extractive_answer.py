from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .manual_query import (
    ManualQuestionProfile,
    analyze_manual_question,
    manual_segment_score,
)


MAX_EXTRACTIVE_CHARACTERS = 520
MAX_EXTRACTIVE_SEGMENTS = 3
MAX_EXTRACTIVE_STEP_SEGMENTS = 4

_PAGE_MARKER_PATTERN = re.compile(r"^\d+-\d+$")
_IMAGE_CODE_PATTERN = re.compile(r"^[0-9A-Za-z]+_[0-9A-Za-z_]+$")
_COMPACT_IMAGE_CODE_PATTERN = re.compile(r"^[A-Z]{2,}[0-9]{4,}$")
_NUMBERED_STEP_PATTERN = re.compile(r"^\d+[.)]\s*")
_LIST_MARKER_PATTERN = re.compile(r"^[•●▶▷-]\s*")
_SENTENCE_BOUNDARY_PATTERN = re.compile(
    r"(?<!\d\.)(?<=[.!?])\s+(?=[0-9A-Za-z가-힣'\"“‘(])"
)
_SPACE_AFTER_ENDINGS = (
    "에서",
    "에게",
    "까지",
    "부터",
    "으로",
    "하고",
    "하며",
    "하면",
    "후",
    "및",
    "와",
    "과",
    "을",
    "를",
    "은",
    "는",
    "이",
    "가",
    "의",
    "에",
    "로",
)
_HEADING_ENDINGS = (
    "감지",
    "방법",
    "모드",
    "사항",
    "사용 제한",
    "사용하기",
    "설정하기",
    "출발하기",
    "순서",
)


@dataclass(frozen=True, slots=True)
class ExtractiveManualAnswer:
    answer: str
    citations: tuple[int, ...]


def _drop_layout_line(line: str) -> bool:
    compact = line.replace(" ", "")
    if not compact:
        return True
    if _PAGE_MARKER_PATTERN.fullmatch(compact) or compact.isdigit():
        return True
    if _IMAGE_CODE_PATTERN.fullmatch(compact) or _COMPACT_IMAGE_CODE_PATTERN.fullmatch(compact):
        return True
    if "충전커넥터(차량측)" in compact and "충전플러그(충전기측)" in compact:
        return True
    if compact in {
        "A−A+",
        "A-A+",
        "주의",
        "경고",
        "참고",
        "편의장치",
        "비상시응급조치",
        "정기점검",
    }:
        return True
    return not re.search(r"[0-9A-Za-z가-힣]", compact)


def _line_joiner(previous: str, raw_previous: str) -> str:
    if raw_previous.endswith((" ", "\t")):
        return " "
    if previous.endswith((".", "!", "?", ":", ";", ",", ")", "]", "”", "’")):
        return " "
    if previous.endswith(_SPACE_AFTER_ENDINGS):
        return " "
    return ""


def _looks_like_heading(line: str) -> bool:
    if len(line) > 30 or _NUMBERED_STEP_PATTERN.match(line):
        return False
    if any(mark in line for mark in (".", "!", "?", '"', "“", "”")):
        return False
    return line.endswith(_HEADING_ENDINGS)


def _segments(excerpt: str) -> list[str]:
    paragraphs: list[str] = []
    current = ""
    previous_raw = ""
    for raw_line in excerpt.replace("\r", "").split("\n"):
        line = re.sub(r"\s+", " ", raw_line).strip()
        if _drop_layout_line(line):
            continue
        starts_item = bool(
            _NUMBERED_STEP_PATTERN.match(line) or _LIST_MARKER_PATTERN.match(line)
        )
        if current and current.endswith((".", "!", "?")):
            paragraphs.append(current.strip())
            current = ""
        if not current and _looks_like_heading(line) and not starts_item:
            if current:
                paragraphs.append(current.strip())
                current = ""
            paragraphs.append(line)
            previous_raw = raw_line
            continue
        if current and starts_item:
            paragraphs.append(current.strip())
            current = ""
        if current:
            current += _line_joiner(current, previous_raw)
        current += line
        previous_raw = raw_line
    if current:
        paragraphs.append(current.strip())

    sentences: list[str] = []
    for paragraph in paragraphs:
        sentences.extend(
            segment.strip()
            for segment in _SENTENCE_BOUNDARY_PATTERN.split(paragraph)
            if segment.strip()
        )
    return sentences


def _without_leading_section_heading(excerpt: str, section: object) -> str:
    normalized_section = re.sub(r"\s+", " ", str(section or "")).strip()
    if not normalized_section:
        return excerpt
    lines = excerpt.replace("\r", "").split("\n")
    while lines:
        first = re.sub(r"\s+", " ", lines[0]).strip()
        if not first or first == normalized_section or _drop_layout_line(first):
            lines.pop(0)
            continue
        break
    return "\n".join(lines)


def _segment_score(profile: ManualQuestionProfile, segment: str) -> int:
    if len(segment) < 16:
        return 0
    if not profile.expects_numeric_power and not segment.endswith((".", "!", "?")):
        return 0
    score = manual_segment_score(profile, segment)
    if score and _NUMBERED_STEP_PATTERN.match(segment):
        score += 2
    return score


def _numbered_value(segment: str) -> int | None:
    match = _NUMBERED_STEP_PATTERN.match(segment)
    return int(match.group(0).rstrip(".) ")) if match else None


def _battery_capacity_answer(
    question: str,
    sources: Sequence[Mapping[str, object]],
) -> ExtractiveManualAnswer | None:
    compact_question = re.sub(r"\s+", "", question.lower())
    capacity_pattern = re.compile(
        r"배터리\s*용량\s*\(\s*kwh\s*\)\s*"
        r"(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d+)?)",
        re.IGNORECASE,
    )
    for source_index, source in enumerate(sources):
        match = capacity_pattern.search(str(source["excerpt"]))
        if match is None:
            continue
        standard, long_range = match.groups()
        if "롱레인지" in compact_question or "항속형" in compact_question:
            answer = f"공식 제원표 기준 항속형(롱레인지) 배터리 용량은 {long_range} kWh입니다."
        elif "기본형" in compact_question or "스탠다드" in compact_question:
            answer = f"공식 제원표 기준 기본형 배터리 용량은 {standard} kWh입니다."
        else:
            answer = (
                "공식 제원표 기준 배터리 용량은 "
                f"기본형 {standard} kWh, 항속형(롱레인지) {long_range} kWh입니다."
            )
        citation_number = source_index + 1
        return ExtractiveManualAnswer(
            answer=f"{answer} [{citation_number}]",
            citations=(citation_number,),
        )
    return None


def build_extractive_manual_answer(
    question: str, sources: Sequence[Mapping[str, object]]
) -> ExtractiveManualAnswer:
    if not sources:
        raise ValueError("at least one manual source is required")
    profile = analyze_manual_question(question)
    if not profile.terms:
        raise ValueError("question has no searchable terms")
    if profile.intent == "battery-capacity":
        capacity_answer = _battery_capacity_answer(question, sources)
        if capacity_answer is not None:
            return capacity_answer

    all_segments = [
        _segments(
            _without_leading_section_heading(
                str(source["excerpt"]), source.get("section")
            )
        )
        for source in sources
    ]
    candidates = [
        (score, source_index, segment_index, segment)
        for source_index, source_segments in enumerate(all_segments)
        for segment_index, segment in enumerate(source_segments)
        if (score := _segment_score(profile, segment)) > 0
    ]
    if not candidates:
        raise ValueError("manual sources have no extractive answer segment")

    selected_source_index = min(source_index for _, source_index, _, _ in candidates)
    _, _, best_segment_index, _ = max(
        (item for item in candidates if item[1] == selected_source_index),
        key=lambda item: (item[0], -item[1], -item[2]),
    )
    source_segments = all_segments[selected_source_index]
    scored = [
        (score, segment_index, segment)
        for score, source_index, segment_index, segment in candidates
        if source_index == selected_source_index
    ]

    selected_indexes: set[int] = set()
    total_characters = 0

    numbered_matches = sorted(
        index
        for _, index, _ in scored
        if _NUMBERED_STEP_PATTERN.match(source_segments[index])
    )
    segment_limit = (
        2
        if profile.intent == "drive-away"
        else (
            MAX_EXTRACTIVE_STEP_SEGMENTS
            if numbered_matches
            else MAX_EXTRACTIVE_SEGMENTS
        )
    )
    if numbered_matches:
        anchor_index = (
            best_segment_index
            if best_segment_index in numbered_matches
            else numbered_matches[0]
        )
        numbered_indexes = [
            index
            for index, segment in enumerate(source_segments)
            if _NUMBERED_STEP_PATTERN.match(segment)
        ]
        anchor_position = numbered_indexes.index(anchor_index)
        start_position = anchor_position
        if anchor_position > 0:
            previous_index = numbered_indexes[anchor_position - 1]
            previous_value = _numbered_value(source_segments[previous_index])
            anchor_value = _numbered_value(source_segments[anchor_index])
            if previous_value is not None and anchor_value == previous_value + 1:
                start_position -= 1
        numbered_sequence = numbered_indexes[
            start_position : start_position + min(3, segment_limit)
        ]
        for next_index in numbered_sequence:
            next_segment = source_segments[next_index]
            projected = total_characters + len(next_segment) + (1 if selected_indexes else 0)
            if projected > MAX_EXTRACTIVE_CHARACTERS:
                break
            selected_indexes.add(next_index)
            total_characters = projected

    for _, index, segment in sorted(scored, key=lambda item: (-item[0], item[1])):
        if len(selected_indexes) >= segment_limit:
            break
        if index in selected_indexes:
            continue
        projected = total_characters + len(segment) + (1 if selected_indexes else 0)
        if projected > MAX_EXTRACTIVE_CHARACTERS:
            continue
        selected_indexes.add(index)
        total_characters = projected

    selected = [source_segments[index] for index in sorted(selected_indexes)]
    if not selected:
        raise ValueError("manual answer exceeds the extractive answer limit")
    separator = "\n" if numbered_matches else " "
    citation_number = selected_source_index + 1
    return ExtractiveManualAnswer(
        answer=separator.join(selected) + f" [{citation_number}]",
        citations=(citation_number,),
    )
