# NHS Survey Dashboard (Django)

This project has been migrated from Streamlit to Django.

## Quick Start

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

Open `http://127.0.0.1:8000/` and upload your survey CSV.

## Current Features

- CSV upload + replacement/clear workflow
- Overview tab with demographic filtering and response distribution
- Themes tab with demographic and tag filters plus theme table
- Quotation Bank with demographic/theme/tag filters and context drill-down

## Notes

- The original Streamlit code is still present in `app.py` for reference.
- Uploaded CSV files are stored temporarily in your system temp directory (`/tmp/nhs_survey_dash_uploads`).
