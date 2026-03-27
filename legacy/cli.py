"""CLI helpers for legacy analysis workflows.

This interface is intentionally light-touch: it organizes commands without
changing the behavior or outputs of the underlying analysis scripts.
"""

import argparse
from pathlib import Path

from convert import convert_excels


def cmd_convert(args: argparse.Namespace) -> int:
    converted = convert_excels(args.input_dir, args.output_dir)
    if converted:
        print(f"Converted {len(converted)} file(s).")
        for path in converted:
            print(f"- {path}")
    else:
        print(f"No .xlsx files found in {args.input_dir}")
    return 0


def cmd_validate_layout(args: argparse.Namespace) -> int:
    required_paths = [
        args.data_dir / "merged_survey.csv",
        args.data_dir / "complete.csv",
        args.data_dir / "complete_tags.csv",
        args.data_dir / "complete_tags2.csv",
        args.data_dir / "excel",
        args.metadata_dir / "themes_with_descriptions.json",
        Path("analysis.py"),
        Path("convert.py"),
        Path("app.py"),
    ]

    missing = [path for path in required_paths if not path.exists()]
    if missing:
        print("Missing expected legacy paths:")
        for path in missing:
            print(f"- {path}")
        return 1

    print("Legacy layout check passed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Utilities for running and validating legacy survey tooling."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert .xlsx demographic files into .csv.",
    )
    convert_parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/excel"),
        help="Directory containing .xlsx files (default: data/excel).",
    )
    convert_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Directory where .csv files are written (default: data).",
    )
    convert_parser.set_defaults(handler=cmd_convert)

    validate_parser = subparsers.add_parser(
        "validate-layout",
        help="Check that expected legacy files/folders are present.",
    )
    validate_parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Legacy data directory (default: data).",
    )
    validate_parser.add_argument(
        "--metadata-dir",
        type=Path,
        default=Path("metadata"),
        help="Legacy metadata directory (default: metadata).",
    )
    validate_parser.set_defaults(handler=cmd_validate_layout)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
