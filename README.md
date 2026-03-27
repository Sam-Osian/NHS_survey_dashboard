# NHS Staff Survey Analysis + Dashboard

This repository has two layers:

- **Analysis service** (`staff-survey` CLI): year-driven data validation, squashing, and analysis.
- **Django app**: dashboard interface for exploring analysed outputs.

## Repository Structure

```text
analysis/                   # Runtime analysis code + CLI
legacy/                     # Archived 2024 analysis files (reference only)
data/
  inputs/
    2024/                   # Raw yearly inputs
      excel/*.xlsx          # Demographic source files
      metadata/*.json
  artifacts/
    2024/
      merged_survey.csv     # Squashed intermediate file
      ...                   # Optional extra intermediate artifacts
  outputs/
    2024/
      comments_2024.csv     # Canonical dashboard-ready output
```

## Analysis CLI

Command name: `staff-survey`

### Stages

1. `verify` — validates year input contract (and baseline output integrity for 2024).
2. `squash` — merges yearly demographic source files into one squashed dataset.
3. `analyse` — runs analysis for the year.

`--year` is required for all stages.

### Usage

```bash
source .venv/bin/activate
staff-survey verify --year 2024
staff-survey squash --year 2024
staff-survey analyse --year 2024
```

## Stage Details

### `staff-survey verify --year <year>`

Checks:

- `data/inputs/<year>/excel/` exists with expected files
- each expected Excel file parses and has at least two columns
- `data/inputs/<year>/metadata/themes_with_descriptions.json` exists
- if `data/artifacts/<year>/merged_survey.csv` exists, verifies required merged schema columns
- for **2024**, verifies `data/outputs/2024/comments_2024.csv` hash against
  `analysis/baselines/2024_outputs.sha256`

### `staff-survey squash --year <year>`

- Reads each `data/inputs/<year>/excel/*.xlsx`
- Uses first two columns from each file (`<group_name>`, `Comment`)
- Outer-merges all on `Comment`
- Fills missing values with `N/A`
- Writes `data/artifacts/<year>/merged_survey.csv`

### `staff-survey analyse --year <year>`

- Requires squashed artifact to exist first.
- Runs the legacy LLM analytical method over `data/artifacts/<year>/merged_survey.csv`:
  - generates themes (`gpt-4.1`)
  - assigns per-theme labels (`gpt-4.1-mini`)
  - assigns meta labels (`suggestion`, `urgent`, `positive`, `negative`)
- Writes:
  - `data/artifacts/<year>/complete.csv`
  - `data/artifacts/<year>/complete_tags2.csv`
  - `data/artifacts/<year>/themes_with_descriptions.json`
  - canonical output `data/outputs/<year>/comments_<year>.csv` (copied from `complete_tags2.csv`)
- For **2024**, also verifies canonical output hash against baseline.

## 2024 Integrity Rules

- 2024 canonical output is fixed and baseline-controlled.
- Output drift is detected via SHA256 manifest checks.
- Do not hand-edit `data/outputs/2024/comments_2024.csv`.

## Setup

```bash
uv sync
source .venv/bin/activate
```

To run `analyse`, ensure `OPENAI_API_KEY` is available in environment or `api.env`.

## Django Dashboard

```bash
uv run python manage.py migrate
uv run python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Notes

- `legacy/` is intentionally retained as the archived source of the original 2024 workflow.
- Active operational tooling should now live under `analysis/`.
