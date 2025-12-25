"""Utility package for managing quiz question banks."""

from .question_bank import QuestionBank, QuestionSelection
from .cli import run_cli
from .converters import convert_format2_to_format1, convert_embedded_question_format
from .importers import extract_from_docx, extract_from_marked_text
from .cleaners import prepend_prefix


def run_gui() -> None:
    from .gui import run_gui as _run_gui

    _run_gui()

__all__ = [
    "QuestionBank",
    "QuestionSelection",
    "run_cli",
    "run_gui",
    "convert_format2_to_format1",
    "convert_embedded_question_format",
    "extract_from_docx",
    "extract_from_marked_text",
    "prepend_prefix",
]
