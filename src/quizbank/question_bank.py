from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import pandas as pd
import random

from .utils import parse_options_text, parse_prompt


@dataclass(frozen=True)
class QuestionSelection:
    index: int
    prompt: str
    options: str
    answer: str
    correct_count: int
    remaining_count: int


class QuestionBank:
    """Wrapper around the Excel question bank with helper utilities."""

    def __init__(
        self,
        excel_path: str | Path,
        *,
        correct_column: str = "正确次数",
        max_correct: int = 5,
    ) -> None:
        self.path = Path(excel_path)
        if not self.path.exists():
            raise FileNotFoundError(f"Question bank not found: {self.path}")
        self.correct_column = correct_column
        self.max_correct = max_correct
        self._data = self._load()

    def _load(self) -> pd.DataFrame:
        df = pd.read_excel(self.path)
        if self.correct_column not in df.columns:
            df[self.correct_column] = 0
        df[self.correct_column] = df[self.correct_column].fillna(0).astype(int)
        return df

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    def remaining_questions(self) -> pd.DataFrame:
        return self._data[self._data[self.correct_column] < self.max_correct]

    def select_question(self, rng: Optional[random.Random] = None) -> Optional[QuestionSelection]:
        rng = rng or random.Random()
        remaining = self.remaining_questions()
        if remaining.empty:
            return None
        weights = 1 / (remaining[self.correct_column] + 1)
        weights = weights / weights.sum()
        chosen_index = rng.choices(remaining.index.tolist(), weights=weights.tolist(), k=1)[0]
        row = self._data.loc[chosen_index]
        prompt = row.get("题目", "")
        options = row.get("选项", "")
        answer = str(row.get("答案", "")).strip()
        correct_count = int(row[self.correct_column])
        remaining_count = len(remaining)
        return QuestionSelection(
            index=chosen_index,
            prompt=prompt,
            options=options,
            answer=answer,
            correct_count=correct_count,
            remaining_count=remaining_count,
        )

    def record_correct(self, selection: QuestionSelection, *, increment: int = 1) -> None:
        idx = selection.index
        self._data.at[idx, self.correct_column] = int(self._data.at[idx, self.correct_column]) + increment

    def save(self) -> None:
        self._data.to_excel(self.path, index=False)

    def reload(self) -> None:
        self._data = self._load()

    @staticmethod
    def describe(selection: QuestionSelection) -> dict[str, object]:
        prompt_type, prompt_number, prompt_stem = parse_prompt(selection.prompt)
        options_type, options_list = parse_options_text(selection.options)
        qtype = prompt_type or options_type or ""
        return {
            "type": qtype,
            "number": prompt_number,
            "stem": prompt_stem,
            "options": options_list,
        }
