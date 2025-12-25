from __future__ import annotations

from pathlib import Path
import pandas as pd


def prepend_prefix(
    file_path: str | Path,
    column_name: str,
    *,
    trigger: str,
    prefix: str,
) -> Path:
    """Remove a trigger string and prepend a prefix in the target column."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"未找到文件：{path}")

    df = pd.read_excel(path)
    if column_name not in df.columns:
        raise ValueError(f"列 '{column_name}' 不存在。")

    def transform(value):
        if pd.isna(value):
            return value
        text = str(value)
        if trigger in text:
            return prefix + text.replace(trigger, "")
        return text

    df[column_name] = df[column_name].map(transform)
    df.to_excel(path, index=False)
    return path
