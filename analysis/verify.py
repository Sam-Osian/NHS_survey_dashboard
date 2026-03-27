from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from .paths import baseline_manifest_path, squashed_path, year_input_dir, year_output_dir

REQUIRED_MERGED_COLUMNS = [
    "occupation_group",
    "Comment",
    "lgbtq",
    "disability",
    "age",
    "service_line",
    "division",
    "gender",
    "payband",
    "staff_group",
    "bme",
]

REQUIRED_INPUT_FILES = [
    "metadata/themes_with_descriptions.json",
]

REQUIRED_EXCEL_FILES = [
    "age.xlsx",
    "bme.xlsx",
    "disability.xlsx",
    "division.xlsx",
    "gender.xlsx",
    "lgbtq.xlsx",
    "occupation_group.xlsx",
    "payband.xlsx",
    "service_line.xlsx",
    "staff_group.xlsx",
]


def sha256sum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_manifest(path: Path) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        hash_value, file_name = line.split("  ", 1)
        pairs[file_name] = hash_value
    return pairs


def verify_inputs(year: int) -> list[str]:
    errors: list[str] = []
    in_dir = year_input_dir(year)

    if not in_dir.exists():
        return [f"Missing input directory: {in_dir}"]

    if year == 2024:
        canonical_input = in_dir / "comments_2024.csv"
        if not canonical_input.exists():
            errors.append(f"Missing frozen 2024 canonical input file: {canonical_input}")

    for rel_path in REQUIRED_INPUT_FILES:
        path = in_dir / rel_path
        if not path.exists():
            errors.append(f"Missing required input file: {path}")

    excel_dir = in_dir / "excel"
    if not excel_dir.exists():
        errors.append(f"Missing required input folder: {excel_dir}")
    else:
        for name in REQUIRED_EXCEL_FILES:
            file_path = excel_dir / name
            if not file_path.exists():
                errors.append(f"Missing required Excel input: {file_path}")

    # Validate each expected demographic sheet shape.
    for name in REQUIRED_EXCEL_FILES:
        file_path = excel_dir / name
        if not file_path.exists():
            continue
        try:
            df = pd.read_excel(file_path, nrows=5)
        except Exception as exc:
            errors.append(f"Could not parse Excel input ({file_path}): {exc}")
            continue
        if df.shape[1] < 2:
            errors.append(
                f"Excel input must have at least 2 columns (group + comment): {file_path}"
            )

    # Validate squashed artifact schema if it has already been generated.
    merged_path = squashed_path(year)
    if merged_path.exists():
        try:
            merged_df = pd.read_csv(merged_path, nrows=10)
        except Exception as exc:
            errors.append(f"Could not parse merged survey CSV ({merged_path}): {exc}")
        else:
            missing_cols = [
                col for col in REQUIRED_MERGED_COLUMNS if col not in merged_df.columns
            ]
            if missing_cols:
                errors.append(
                    "Merged survey schema missing required columns: "
                    + ", ".join(missing_cols)
                )

    return errors


def verify_outputs_against_baseline(year: int) -> list[str]:
    errors: list[str] = []

    manifest_path = baseline_manifest_path(year)
    if not manifest_path.exists():
        return [
            f"Missing baseline manifest for year {year}: {manifest_path}. "
            "Create one before enforcing output integrity."
        ]

    out_dir = year_output_dir(year)
    if not out_dir.exists():
        return [f"Missing output directory: {out_dir}"]

    expected = _read_manifest(manifest_path)

    for rel_name, expected_hash in expected.items():
        output_file = out_dir / rel_name
        if not output_file.exists():
            errors.append(f"Missing output file: {output_file}")
            continue

        actual_hash = sha256sum(output_file)
        if actual_hash != expected_hash:
            errors.append(
                f"Output hash mismatch for {output_file}: "
                f"expected {expected_hash}, got {actual_hash}"
            )

    current_files = {
        path.name
        for path in out_dir.iterdir()
        if path.is_file()
    }
    unexpected = sorted(current_files - set(expected.keys()))
    if unexpected:
        errors.append(
            "Unexpected output files present for baseline-controlled year "
            f"{year}: {', '.join(unexpected)}"
        )

    return errors


def verify_year(year: int, check_outputs: bool) -> list[str]:
    errors = verify_inputs(year)
    if check_outputs:
        errors.extend(verify_outputs_against_baseline(year))
    return errors
