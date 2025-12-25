from __future__ import annotations

from pathlib import Path
import os
import re
from typing import Optional

import pandas as pd


def _normalize_cell(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)) or pd.isna(value):
        return ""
    return str(value).strip()


def convert_format2_to_format1(
    input_xlsx_path: str,
    output_xlsx_path: str | None = None,
    sheet_name: str | int | None = 0,
) -> str:
    """Convert the raw bank (格式2) into a normalized Excel file."""
    input_path = Path(input_xlsx_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if output_xlsx_path is None:
        base, ext = os.path.splitext(str(input_path))
        output_xlsx_path = f"{base}_格式1{ext or '.xlsx'}"

    df_raw = pd.read_excel(input_path, header=None, dtype=str, sheet_name=sheet_name)

    def is_header_row(row) -> bool:
        vals = [_normalize_cell(x) for x in row.tolist()]
        return any(v in ("标题", "题目") for v in vals)

    header_idx = None
    for i in range(len(df_raw)):
        if is_header_row(df_raw.iloc[i]):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("未找到表头行（包含“标题/题目”）。")

    header_vals = [_normalize_cell(x) for x in df_raw.iloc[header_idx].tolist()]
    df = df_raw.iloc[header_idx + 1 :].copy()
    df.columns = range(df.shape[1])

    def find_idx_exact(text: str) -> int | None:
        for j, v in enumerate(header_vals):
            if v == text:
                return j
        return None

    title_idx = find_idx_exact("标题") or find_idx_exact("题目")
    if title_idx is None:
        title_idx = 0

    opt_idx = {
        "A": find_idx_exact("选项A"),
        "B": find_idx_exact("选项B"),
        "C": find_idx_exact("选项C"),
        "D": find_idx_exact("选项D"),
    }

    used = {title_idx} | {i for i in opt_idx.values() if i is not None}

    def norm_cell_upper(x) -> str:
        return _normalize_cell(x).upper()

    ans_pattern = re.compile(r"^[A-D]+$")

    best_ans_idx = None
    best_score = float("-inf")

    for j in range(df.shape[1]):
        if j in used:
            continue
        col = df.iloc[:, j].map(norm_cell_upper)
        non_empty = col[col != ""]
        if len(non_empty) == 0:
            continue
        match_rate = non_empty.map(lambda s: bool(ans_pattern.match(re.sub(r"[^A-D]", "", s)))).mean()
        avg_len = non_empty.map(len).mean()
        score = match_rate - 0.02 * max(0, avg_len - 4)
        if score > best_score:
            best_score = score
            best_ans_idx = j

    if best_ans_idx is None:
        non_empty_counts = [
            (j, df.iloc[:, j].notna().sum()) for j in range(df.shape[1]) if j not in used
        ]
        if not non_empty_counts:
            raise ValueError("未找到答案列候选列。")
        best_ans_idx = max(non_empty_counts, key=lambda t: (t[1], t[0]))[0]

    rows: list[dict[str, str]] = []
    for k in range(len(df)):
        title = _normalize_cell(df.iat[k, title_idx])
        if not title:
            continue

        def get_opt(letter: str) -> str:
            idx = opt_idx.get(letter)
            if idx is None:
                return ""
            return _normalize_cell(df.iat[k, idx])

        ans_raw = norm_cell_upper(df.iat[k, best_ans_idx])
        answer = re.sub(r"[^A-D]", "", ans_raw)
        qtype = "单选题" if len(answer) <= 1 else "多选题"
        stem = f"{qtype}  {len(rows) + 1}. {title}"

        option_parts = []
        for letter in ("A", "B", "C", "D"):
            value = get_opt(letter)
            if value:
                option_parts.append(f"{letter}.{value}")
        options = ", ".join([qtype, *option_parts]) if option_parts else qtype

        rows.append({"题目": stem, "选项": options, "答案": answer})

    out_df = pd.DataFrame(rows, columns=["题目", "选项", "答案"])
    out_df.to_excel(output_xlsx_path, index=False)
    return output_xlsx_path


_RE_NUM = re.compile(r'^\s*"?\s*(\d+)\s*[：:\.、]?\s*')
_RE_TRAIL_QTYPE = re.compile(r'（[^（）]*?(单选题|多选题)[^（）]*?）\s*$', re.S)
_RE_QTYPE_INNER = re.compile(r'（([^（）]*)）\s*$', re.S)
_RE_OPT_LINE = re.compile(r'^\s*([A-D])\s*[\.\．、]\s*(.+?)\s*$')
_RE_OPT_INLINE = re.compile(
    r'([A-D])\s*[\.\．、]\s*'
    r'(.+?)'
    r'(?=(?:\s*[A-D]\s*[\.\．、]\s*)|$)',
    re.S,
)


def _clean_text(text) -> str:
    if text is None:
        return ""
    value = str(text).strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        value = value[1:-1]
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r'[ \t]+', ' ', value)
    return value.strip()


def _strip_trailing_qtype(text: str) -> str:
    return _RE_TRAIL_QTYPE.sub('', text).strip()


def _extract_qtype(text: str, answer: str) -> str:
    match = _RE_QTYPE_INNER.search(text)
    if match:
        inner = match.group(1)
        if "多选题" in inner:
            return "多选题"
        if "单选题" in inner:
            return "单选题"
    return "多选题" if len(answer) > 1 else "单选题"


def _extract_number_and_stem(text: str, fallback_index: int) -> tuple[int, str]:
    number = fallback_index
    match = _RE_NUM.match(text)
    if match:
        number = int(match.group(1))
        text = text[match.end():].lstrip()
    opt_match = re.search(r'(?:\n|\s)([A-D])\s*[\.\．、]\s*', text)
    if opt_match:
        stem = text[:opt_match.start()].strip()
    else:
        stem = text.strip()
    stem = re.sub(r'\s*\n\s*', ' ', stem).strip()
    return number, stem


def _parse_options_block(text: str) -> dict[str, str]:
    options = {letter: "" for letter in "ABCD"}
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for line in lines:
        match = _RE_OPT_LINE.match(line)
        if match:
            options[match.group(1)] = match.group(2).strip()
    if all(value == "" for value in options.values()):
        for match in _RE_OPT_INLINE.finditer(text):
            letter = match.group(1)
            value = re.sub(r'\s+', ' ', match.group(2)).strip()
            options[letter] = value
    return options


def convert_embedded_question_format(
    input_xlsx_path: str,
    output_xlsx_path: str | None = None,
    sheet_name: str | int | None = 0,
) -> str:
    """Handle source Excel where question text includes options and metadata in single cell."""

    input_path = Path(input_xlsx_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if output_xlsx_path is None:
        base, ext = os.path.splitext(str(input_path))
        output_xlsx_path = f"{base}_格式1{ext or '.xlsx'}"

    df = pd.read_excel(input_path, sheet_name=sheet_name, dtype=str)
    df.columns = [str(col).strip() for col in df.columns]

    question_col = "题目" if "题目" in df.columns else df.columns[0]
    answer_col: Optional[str]
    if "答案" in df.columns:
        answer_col = "答案"
    elif len(df.columns) > 1:
        answer_col = df.columns[1]
    else:
        answer_col = None

    rows: list[dict[str, str]] = []
    fallback_index = 0
    for _, record in df.iterrows():
        question_cell = record.get(question_col, "")
        answer_cell = record.get(answer_col, "") if answer_col else ""
        cleaned_question = _clean_text(question_cell)
        if not cleaned_question:
            continue

        fallback_index += 1
        answer = re.sub(r'[^A-D]', '', _clean_text(answer_cell).upper())
        qtype = _extract_qtype(cleaned_question, answer)
        question_wo_qtype = _strip_trailing_qtype(cleaned_question)
        number, stem = _extract_number_and_stem(question_wo_qtype, fallback_index)
        options = _parse_options_block(question_wo_qtype)

        option_parts = [qtype]
        for letter in "ABCD":
            value = options[letter]
            if value:
                option_parts.append(f"{letter}.{value}")
        options_text = ", ".join(option_parts)

        rows.append(
            {
                "题目": f"{qtype}  {number}. {stem}",
                "选项": options_text,
                "答案": answer,
            }
        )

    out_df = pd.DataFrame(rows, columns=["题目", "选项", "答案"])
    out_df.to_excel(output_xlsx_path, index=False)
    return output_xlsx_path
