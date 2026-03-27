from __future__ import annotations

import argparse

from .analyse import analyse_year
from .squash import squash_year
from .verify import verify_year


def _year_type(value: str) -> int:
    year = int(value)
    if year < 2000 or year > 2100:
        raise argparse.ArgumentTypeError("year must be between 2000 and 2100")
    return year


def cmd_verify(args: argparse.Namespace) -> int:
    check_outputs = args.with_outputs or args.year == 2024

    errors = verify_year(year=args.year, check_outputs=check_outputs)
    if errors:
        print(f"Verify failed for year {args.year}:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Verify passed for year {args.year}.")
    return 0


def cmd_analyse(args: argparse.Namespace) -> int:
    ok, messages = analyse_year(year=args.year, force=args.force)
    if not ok:
        print(f"Analyse failed for year {args.year}:")
        for message in messages:
            print(f"- {message}")
        return 1

    print(f"Analyse completed for year {args.year}:")
    for message in messages:
        print(f"- {message}")
    return 0


def cmd_squash(args: argparse.Namespace) -> int:
    ok, messages = squash_year(year=args.year, force=args.force)
    if not ok:
        print(f"Squash failed for year {args.year}:")
        for message in messages:
            print(f"- {message}")
        return 1

    print(f"Squash completed for year {args.year}:")
    for message in messages:
        print(f"- {message}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="staff-survey",
        description="NHS staff survey analysis CLI.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify a year's input contract and baseline output integrity.",
    )
    verify_parser.add_argument("--year", required=True, type=_year_type)
    verify_parser.add_argument(
        "--with-outputs",
        action="store_true",
        help="Also verify outputs against the baseline manifest.",
    )
    verify_parser.set_defaults(handler=cmd_verify)

    squash_parser = subparsers.add_parser(
        "squash",
        help="Merge yearly demographic inputs into a single squashed dataset.",
    )
    squash_parser.add_argument("--year", required=True, type=_year_type)
    squash_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing squashed artifact if present.",
    )
    squash_parser.set_defaults(handler=cmd_squash)

    analyse_parser = subparsers.add_parser(
        "analyse",
        help="Run analysis for a named year.",
    )
    analyse_parser.add_argument("--year", required=True, type=_year_type)
    analyse_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite year outputs when materialising 2024 frozen outputs.",
    )
    analyse_parser.set_defaults(handler=cmd_analyse)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
