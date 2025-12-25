from __future__ import annotations

import re
from typing import Iterable, List, Optional, Sequence, Tuple

VALID_CHOICES: Tuple[str, ...] = tuple("ABCDE")
_OPTION_PATTERN = re.compile(r"^\s*([A-Z])\s*[\.\:：．、]\s*(.*)$")
_PROMPT_PATTERN = re.compile(
    r"^\s*(?P<qtype>[\u4e00-\u9fa5A-Za-z]+题)?\s*(?P<num>\d+)?[\.\:：、]?\s*(?P<stem>.*)$"
)


def normalize_answers(raw: str) -> List[str]:
    text = (raw or "").strip().upper().replace(" ", "")
    if not text:
        return []
    if all(ch.isdigit() for ch in text):
        letters = [
            chr(ord("A") + int(ch) - 1)
            for ch in text
            if ch.isdigit() and 1 <= int(ch) <= len(VALID_CHOICES)
        ]
    else:
        letters = [ch for ch in text if ch in VALID_CHOICES]
    seen = set()
    ordered = []
    for ch in letters:
        if ch not in seen:
            seen.add(ch)
            ordered.append(ch)
    return sorted(ordered)


def answers_match(user_letters: Sequence[str], expected: str) -> bool:
    expected_letters = normalize_answers(expected)
    return sorted(user_letters) == expected_letters


def parse_options_text(options_text: str) -> tuple[str, list[tuple[str, str]]]:
    if not options_text:
        return "", []
    # 支持逗号或换行分隔
    raw_parts = re.split(r"[，,]|\n", options_text)
    parts = [p.strip() for p in raw_parts if p and p.strip()]
    qtype = ""
    options: list[tuple[str, str]] = []
    for part in parts:
        match = _OPTION_PATTERN.match(part)
        if match:
            letter = match.group(1)
            text = match.group(2).strip()
            options.append((letter, text))
        elif not qtype and part.endswith("题"):
            qtype = part
    return qtype, options


def parse_prompt(prompt: str) -> tuple[Optional[str], Optional[int], str]:
    if not prompt:
        return None, None, ""
    match = _PROMPT_PATTERN.match(prompt)
    if not match:
        return None, None, prompt.strip()
    stem = match.group("stem").strip()
    qtype = match.group("qtype") or None
    num_text = match.group("num")
    number = int(num_text) if num_text and num_text.isdigit() else None
    return qtype, number, stem


def letters_to_string(letters: Iterable[str]) -> str:
    ordered = sorted(letters)
    return "".join(ordered)
