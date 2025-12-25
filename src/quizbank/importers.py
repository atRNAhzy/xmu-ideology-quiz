from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pandas as pd

try:
    from docx import Document
except ImportError as exc:
    Document = None  # type: ignore[assignment]


def _ensure_docx_available() -> None:
    if Document is None:
        raise ImportError("python-docx 未安装，无法处理 Word 文档。")


def extract_from_docx(word_file: str | Path) -> pd.DataFrame:
    _ensure_docx_available()
    doc = Document(word_file)

    questions: list[str] = []
    answers: list[str] = []
    current_question_lines: list[str] = []

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        if text.startswith("正确答案"):
            questions.append("\n".join(current_question_lines).strip())
            answer = text.split("：", 1)[1] if "：" in text else text.split(":", 1)[-1]
            answers.append(answer.strip())
            current_question_lines = []
        else:
            current_question_lines.append(text)

    df = pd.DataFrame({"题目": questions, "答案": answers})
    return df


def extract_from_marked_text(text_file: str | Path, *, encoding: str = "utf-8") -> pd.DataFrame:
    with open(text_file, "r", encoding=encoding) as handle:
        content = handle.read()

    pattern = r"(\d+\.\s*.*?)(?=\d+\.|\Z)"
    matches = re.findall(pattern, content, flags=re.DOTALL)

    rows: list[dict[str, str]] = []
    for block in matches:
        lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
        if not lines:
            continue
        title = lines[0]
        options = ", ".join(lines[1:-1]) if len(lines) > 2 else ""
        answer = lines[-1] if len(lines) > 1 else ""
        rows.append({"题目": title, "选项": options, "答案": answer})

    return pd.DataFrame(rows)


def save_to_excel(df: pd.DataFrame, output_path: str | Path) -> Path:
    output = Path(output_path)
    df.to_excel(output, index=False)
    return output
