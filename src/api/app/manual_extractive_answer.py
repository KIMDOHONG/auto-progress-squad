from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


MAX_EXTRACTIVE_CHARACTERS = 520
MAX_EXTRACTIVE_SEGMENTS = 3
MAX_EXTRACTIVE_STEP_SEGMENTS = 4

_TOKEN_PATTERN = re.compile(r"[0-9]+(?:[.,][0-9]+)*|[a-zA-Z]+|[가-힣]{2,}")
_PAGE_MARKER_PATTERN = re.compile(r"^\d+-\d+$")
_IMAGE_CODE_PATTERN = re.compile(r"^[0-9A-Za-z]+_[0-9A-Za-z_]+$")
_COMPACT_IMAGE_CODE_PATTERN = re.compile(r"^[A-Z]{2,}[0-9]{4,}$")
_NUMBERED_STEP_PATTERN = re.compile(r"^\d+[.)]\s*")
_LIST_MARKER_PATTERN = re.compile(r"^[•●▶▷-]\s*")
_SENTENCE_BOUNDARY_PATTERN = re.compile(
    r"(?<!\d\.)(?<=[.!?])\s+(?=[0-9A-Za-z가-힣'\"“‘(])"
)
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
_QUESTION_STOP_TOKENS = {
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
}
_TERM_EQUIVALENTS = {
    "배터리": ("건전지",),
    "건전지": ("배터리",),
}
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
    "사용 제한",
    "사용하기",
    "설정하기",
)


@dataclass(frozen=True, slots=True)
class ExtractiveManualAnswer:
    answer: str
    citations: tuple[int, ...]


def _compact(value: str) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]+", "", value.lower())


def _query_terms(question: str) -> list[str]:
    terms: list[str] = []
    for raw_token in _TOKEN_PATTERN.findall(question.lower()):
        token = raw_token
        if re.fullmatch(r"[가-힣]+", token):
            for suffix in _KOREAN_SUFFIXES:
                if token.endswith(suffix) and len(token) > len(suffix) + 1:
                    token = token[: -len(suffix)]
                    break
        if token in _QUESTION_STOP_TOKENS or len(token) < 2:
            continue
        if token not in terms:
            terms.append(token)
    return terms


def _drop_layout_line(line: str) -> bool:
    compact = line.replace(" ", "")
    if not compact:
        return True
    if _PAGE_MARKER_PATTERN.fullmatch(compact) or compact.isdigit():
        return True
    if _IMAGE_CODE_PATTERN.fullmatch(compact) or _COMPACT_IMAGE_CODE_PATTERN.fullmatch(compact):
        return True
    if compact in {"주의", "경고", "참고", "편의장치", "비상시응급조치", "정기점검"}:
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


def _segment_score(segment: str, terms: Sequence[str]) -> int:
    if len(segment) < 16 or not segment.endswith((".", "!", "?")):
        return 0
    compact = _compact(segment)
    score = 0
    for term in terms:
        variants = (term, *_TERM_EQUIVALENTS.get(term, ()))
        if any(_compact(variant) in compact for variant in variants):
            score += max(len(term), 2)
    if score and _NUMBERED_STEP_PATTERN.match(segment):
        score += 2
    return score


def build_extractive_manual_answer(
    question: str, sources: Sequence[Mapping[str, object]]
) -> ExtractiveManualAnswer:
    if not sources:
        raise ValueError("at least one manual source is required")
    terms = _query_terms(question)
    if not terms:
        raise ValueError("question has no searchable terms")

    source_segments = _segments(str(sources[0]["excerpt"]))
    scored = [
        (score, index, segment)
        for index, segment in enumerate(source_segments)
        if (score := _segment_score(segment, terms)) > 0
    ]
    if not scored:
        raise ValueError("top source has no extractive answer segment")

    selected_indexes: set[int] = set()
    total_characters = 0

    numbered_matches = [
        index
        for _, index, _ in scored
        if _NUMBERED_STEP_PATTERN.match(source_segments[index])
    ]
    segment_limit = (
        MAX_EXTRACTIVE_STEP_SEGMENTS if numbered_matches else MAX_EXTRACTIVE_SEGMENTS
    )
    if numbered_matches:
        first_numbered_match = min(numbered_matches)
        numbered_sequence = [
            index
            for index, segment in enumerate(source_segments)
            if index >= first_numbered_match and _NUMBERED_STEP_PATTERN.match(segment)
        ][:3]
        for next_index in numbered_sequence:
            next_segment = source_segments[next_index]
            projected = total_characters + len(next_segment) + (1 if selected_indexes else 0)
            if projected > MAX_EXTRACTIVE_CHARACTERS:
                break
            selected_indexes.add(next_index)
            total_characters = projected

    for _, index, segment in sorted(scored, key=lambda item: (-item[0], item[1])):
        if index in selected_indexes:
            continue
        projected = total_characters + len(segment) + (1 if selected_indexes else 0)
        if projected > MAX_EXTRACTIVE_CHARACTERS:
            continue
        selected_indexes.add(index)
        total_characters = projected
        if len(selected_indexes) >= segment_limit:
            break

    selected = [source_segments[index] for index in sorted(selected_indexes)]
    separator = "\n" if numbered_matches else " "
    return ExtractiveManualAnswer(
        answer=separator.join(selected) + " [1]",
        citations=(1,),
    )
