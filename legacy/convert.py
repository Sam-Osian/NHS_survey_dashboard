"""Convert Excel files in a folder to CSV files."""

import argparse
from pathlib import Path

import pandas as pd


def convert_excels(input_dir: Path, output_dir: Path) -> list[Path]:
    """Convert all .xlsx files from input_dir into CSV files in output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)

    converted: list[Path] = []
    for excel_file in sorted(input_dir.glob("*.xlsx")):
        df = pd.read_excel(excel_file)
        csv_file = output_dir / f"{excel_file.stem}.csv"
        df.to_csv(csv_file, index=False)
        converted.append(csv_file)

    return converted


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert .xlsx files to .csv files.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/excel"),
        help="Directory containing .xlsx files (default: data/excel).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Directory where .csv files are written (default: data).",
    )
    args = parser.parse_args()

    converted = convert_excels(args.input_dir, args.output_dir)
    if converted:
        print(f"Converted {len(converted)} files:")
        for path in converted:
            print(f"- {path}")
    else:
        print(f"No .xlsx files found in {args.input_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

