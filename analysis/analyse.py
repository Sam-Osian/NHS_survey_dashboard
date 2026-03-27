from __future__ import annotations

import shutil

import pandas as pd

from .paths import canonical_output_path, squashed_path, year_artifact_dir
from .pipeline_legacy import run_legacy_pipeline
from .verify import verify_inputs, verify_outputs_against_baseline


def analyse_year(year: int, force: bool) -> tuple[bool, list[str]]:
    errors = verify_inputs(year)
    if errors:
        return False, errors

    merged_path = squashed_path(year)
    if not merged_path.exists():
        return False, [
            f"Missing squashed artifact for year {year}: {merged_path}",
            "Run `analysis squash --year <year>` before `analysis analyse`.",
        ]

    try:
        merged_df = pd.read_csv(merged_path)
    except Exception as exc:
        return False, [f"Failed to read squashed file {merged_path}: {exc}"]

    artifact_dir = year_artifact_dir(year)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    complete_path = artifact_dir / "complete.csv"
    complete_tags2_path = artifact_dir / "complete_tags2.csv"
    themes_path = artifact_dir / "themes_with_descriptions.json"

    if (complete_path.exists() or complete_tags2_path.exists()) and not force:
        return False, [
            f"Analysis artifacts already exist for {year} in {artifact_dir}",
            "Re-run with --force to overwrite.",
        ]

    try:
        complete_df, complete_tags2_df, raw_themes_json = run_legacy_pipeline(merged_df)
    except Exception as exc:
        return False, [f"Legacy pipeline execution failed: {exc}"]

    complete_df.to_csv(complete_path, index=False)
    complete_tags2_df.to_csv(complete_tags2_path, index=False)
    themes_path.write_text(raw_themes_json, encoding="utf-8")

    canonical_path = canonical_output_path(year)
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(complete_tags2_path, canonical_path)

    messages = [
        f"Wrote analysis artifacts to {artifact_dir}",
        f"Wrote canonical output to {canonical_path}",
    ]

    if year == 2024:
        baseline_errors = verify_outputs_against_baseline(2024)
        if baseline_errors:
            return False, baseline_errors
        messages.append("2024 canonical output matches frozen baseline.")

    return True, messages
