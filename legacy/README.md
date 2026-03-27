# Legacy Analysis Folder

This folder preserves the original analytical workflow and outputs used to
construct the survey datasets.

## Invariant

- Analytical outputs in `legacy/data/` should not be edited in-place.
- Any refactoring should only affect code organization, interface, and docs.

## CLI

Run commands from inside `legacy/`:

```bash
uv run python cli.py validate-layout
uv run python cli.py convert
```

### Commands

- `validate-layout`: checks expected files/folders are present.
- `convert`: converts `data/excel/*.xlsx` into CSV files in `data/`.

## Existing Scripts

- `analysis.py`: LLM-assisted theme generation/assignment workflow.
- `convert.py`: Excel-to-CSV conversion utility.
- `app.py`: original Streamlit exploration app.

## Notes

- `analysis.py` example block references `data/all_staff.csv` and
  `data/community_care.csv`; those files are not currently present in this
  folder and may need path updates for reruns.
- The folder currently contains a nested `legacy/.git` repository. Keep it only
  if intentional.
