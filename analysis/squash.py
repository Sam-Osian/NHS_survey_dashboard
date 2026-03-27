from __future__ import annotations

from functools import reduce
from pathlib import Path

import pandas as pd

from .paths import squashed_path, year_artifact_dir, year_input_dir
from .verify import REQUIRED_EXCEL_FILES


def squash_year(year: int, force: bool) -> tuple[bool, list[str]]:
    input_dir = year_input_dir(year)
    excel_dir = input_dir / "excel"

    if not excel_dir.exists():
        return False, [f"Missing Excel input directory: {excel_dir}"]

    frames: list[pd.DataFrame] = []
    for filename in REQUIRED_EXCEL_FILES:
        file_path = excel_dir / filename
        if not file_path.exists():
            return False, [f"Missing required input file: {file_path}"]

        try:
            source_df = pd.read_excel(file_path)
        except Exception as exc:
            return False, [f"Could not read {file_path}: {exc}"]

        if source_df.shape[1] < 2:
            return False, [
                f"Input file must contain at least two columns (group + comment): {file_path}"
            ]

        group_name = Path(filename).stem
        trimmed = source_df.iloc[:, :2].copy()
        trimmed.columns = [group_name, "Comment"]
        frames.append(trimmed)

    merged = reduce(
        lambda left, right: pd.merge(left, right, on="Comment", how="outer"),
        frames,
    )
    merged = merged.fillna("N/A")

    out_dir = year_artifact_dir(year)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = squashed_path(year)

    if out_path.exists() and not force:
        return False, [
            f"Squashed file already exists: {out_path}",
            "Re-run with --force to overwrite.",
        ]

    merged.to_csv(out_path, index=False, encoding="utf-8")
    return True, [
        f"Squashed input files for {year}.",
        f"Rows: {len(merged)}, Columns: {len(merged.columns)}",
        f"Output: {out_path}",
    ]
