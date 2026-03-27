from pathlib import Path
import tempfile
import uuid

import pandas as pd
from django.contrib import messages
from django.shortcuts import redirect, render

RENAME_MAP = {
    "occupation_group": "Occupation group",
    "lgbtq": "Sexuality",
    "disability": "Disability",
    "age": "Age group",
    "service_line": "Service line",
    "gender": "Gender",
    "payband": "Pay band",
    "staff_group": "Staff group",
    "bme": "Ethnicity",
}

DEMOGRAPHIC_COLS = [
    "Occupation group",
    "Sexuality",
    "Disability",
    "Age group",
    "Service line",
    "Gender",
    "Pay band",
    "Staff group",
    "Ethnicity",
]

TAGS = ["suggestion", "urgent", "positive", "negative"]
TRUTHY_VALUES = {"yes", "true", "1"}
VALID_TABS = {"overview", "themes", "quotes"}
UPLOAD_DIR = Path(tempfile.gettempdir()) / "nhs_survey_dash_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _remove_upload(path_value: str | None) -> None:
    if not path_value:
        return

    try:
        Path(path_value).unlink(missing_ok=True)
    except OSError:
        pass


def _save_upload(uploaded_file, session_key: str | None) -> Path:
    suffix = Path(uploaded_file.name).suffix or ".csv"
    token = session_key or uuid.uuid4().hex
    destination = UPLOAD_DIR / f"{token}_{uuid.uuid4().hex}{suffix}"

    with destination.open("wb") as output_file:
        for chunk in uploaded_file.chunks():
            output_file.write(chunk)

    return destination


def _load_data(csv_path: Path) -> tuple[pd.DataFrame, list[str]]:
    df = pd.read_csv(csv_path)

    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])

    if "Comment" in df.columns:
        df["Comment"] = df["Comment"].fillna("").astype(str)

    df = df.rename(columns=RENAME_MAP)

    if "division" in df.columns:
        df = df.drop(columns=["division"])

    expected_cols = DEMOGRAPHIC_COLS + ["Comment"] + TAGS
    missing_cols = [column for column in expected_cols if column not in df.columns]
    return df, missing_cols


def _options_for_column(df: pd.DataFrame, column_name: str) -> list[str]:
    values = df[column_name].dropna().astype(str).str.strip()
    cleaned = sorted({value for value in values if value})
    return cleaned


def _normalize_multiselect(selected_values: list[str], allowed_options: list[str]) -> list[str]:
    valid = [value for value in selected_values if value in allowed_options or value == "All"]

    if "All" in valid and len(valid) > 1:
        valid = [value for value in valid if value != "All"]

    return valid or ["All"]


def _truthy_mask(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(TRUTHY_VALUES)


def home(request):
    if request.method == "POST":
        action = request.POST.get("action", "upload")
        existing_path = request.session.get("uploaded_csv_path")

        if action == "clear":
            _remove_upload(existing_path)
            request.session.pop("uploaded_csv_path", None)
            messages.info(request, "Uploaded CSV cleared.")
            return redirect("home")

        uploaded_csv = request.FILES.get("survey_csv")
        if not uploaded_csv:
            messages.error(request, "Please choose a CSV file to upload.")
            return redirect("home")

        if not uploaded_csv.name.lower().endswith(".csv"):
            messages.error(request, "Only .csv files are supported.")
            return redirect("home")

        if request.session.session_key is None:
            request.session.save()

        saved_path = _save_upload(uploaded_csv, request.session.session_key)
        _remove_upload(existing_path)
        request.session["uploaded_csv_path"] = str(saved_path)

        messages.success(request, f"Uploaded {uploaded_csv.name}.")
        return redirect("home")

    active_tab = request.GET.get("tab", "overview")
    if active_tab not in VALID_TABS:
        active_tab = "overview"

    context: dict = {
        "active_tab": active_tab,
        "data_loaded": False,
        "uploaded_filename": None,
        "missing_cols": [],
        "data_error": None,
        "demographic_cols": DEMOGRAPHIC_COLS,
        "tags": TAGS,
        "theme_cols": [],
        "total_responses": 0,
        "overview_group": DEMOGRAPHIC_COLS[0],
        "overview_group_options": [],
        "overview_selected_vals": ["All"],
        "overview_count_filtered": 0,
        "overview_rows": [],
        "overview_chart_data": [],
        "theme_dim": "All",
        "theme_options": [],
        "theme_selected_vals": ["All"],
        "theme_tag": "All",
        "theme_count_filtered": 0,
        "theme_rows": [],
        "theme_chart_data": [],
        "quote_dim": "All",
        "quote_options": [],
        "quote_selected_vals": ["All"],
        "quote_theme": "All",
        "quote_tag": "All",
        "quote_count_filtered": 0,
        "quote_tag_chart_data": [],
        "quote_table_headers": [],
        "quote_table_rows": [],
        "quote_table_truncated": False,
        "quote_index_options": [],
        "context_idx": "",
        "quote_context_pairs": [],
    }

    csv_path_value = request.session.get("uploaded_csv_path")
    if not csv_path_value:
        return render(request, "dashboard/home.html", context)

    csv_path = Path(csv_path_value)
    if not csv_path.exists():
        request.session.pop("uploaded_csv_path", None)
        messages.warning(request, "Saved upload was not found. Please upload your CSV again.")
        return render(request, "dashboard/home.html", context)

    context["uploaded_filename"] = csv_path.name

    try:
        df, missing_cols = _load_data(csv_path)
    except Exception as exc:
        context["data_error"] = f"Could not parse CSV: {exc}"
        return render(request, "dashboard/home.html", context)

    context["data_loaded"] = True
    context["missing_cols"] = missing_cols

    if missing_cols:
        return render(request, "dashboard/home.html", context)

    total_responses = len(df)
    context["total_responses"] = total_responses

    all_columns = df.columns.tolist()
    theme_cols = [column for column in all_columns if column not in DEMOGRAPHIC_COLS + ["Comment"] + TAGS]
    context["theme_cols"] = theme_cols

    # Overview tab state
    overview_group = request.GET.get("overview_group", DEMOGRAPHIC_COLS[0])
    if overview_group not in DEMOGRAPHIC_COLS:
        overview_group = DEMOGRAPHIC_COLS[0]

    overview_group_options = _options_for_column(df, overview_group)
    overview_selected_vals = _normalize_multiselect(
        request.GET.getlist("overview_vals"),
        overview_group_options,
    )

    if "All" in overview_selected_vals:
        filtered_overview = df.copy()
    else:
        filtered_overview = df[df[overview_group].astype(str).isin(overview_selected_vals)]

    overview_count_filtered = len(filtered_overview)
    overview_counts = (
        filtered_overview[overview_group]
        .dropna()
        .astype(str)
        .value_counts()
        .sort_index()
    )

    max_count = int(overview_counts.max()) if not overview_counts.empty else 0
    overview_rows = []
    overview_chart_data = []
    for label, count in overview_counts.items():
        count_int = int(count)
        percent = (count_int / total_responses) if total_responses else 0
        bar_width = ((count_int / max_count) * 100) if max_count else 0
        overview_rows.append(
            {
                "label": label,
                "count": count_int,
                "percent": f"{percent:.1%}",
                "bar_width": f"{bar_width:.2f}",
            }
        )
        overview_chart_data.append(
            {
                "name": label,
                "value": count_int,
                "percent": round(percent * 100, 2),
            }
        )

    context.update(
        {
            "overview_group": overview_group,
            "overview_group_options": overview_group_options,
            "overview_selected_vals": overview_selected_vals,
            "overview_count_filtered": overview_count_filtered,
            "overview_rows": overview_rows,
            "overview_chart_data": overview_chart_data,
        }
    )

    # Themes tab state
    theme_dim = request.GET.get("theme_dim", "All")
    if theme_dim not in ["All"] + DEMOGRAPHIC_COLS:
        theme_dim = "All"

    theme_options = []
    theme_selected_vals = ["All"]
    filtered_themes = df.copy()

    if theme_dim != "All":
        theme_options = _options_for_column(df, theme_dim)
        theme_selected_vals = _normalize_multiselect(
            request.GET.getlist("theme_vals"),
            theme_options,
        )

        if "All" not in theme_selected_vals:
            filtered_themes = filtered_themes[
                filtered_themes[theme_dim].astype(str).isin(theme_selected_vals)
            ]

    theme_tag = request.GET.get("theme_tag", "All")
    if theme_tag not in ["All"] + TAGS:
        theme_tag = "All"

    if theme_tag != "All" and theme_tag in filtered_themes.columns:
        filtered_themes = filtered_themes[_truthy_mask(filtered_themes[theme_tag])]

    theme_count_filtered = len(filtered_themes)

    theme_rows = []
    for theme_column in theme_cols:
        if theme_column in filtered_themes.columns and theme_count_filtered > 0:
            count = int(_truthy_mask(filtered_themes[theme_column]).sum())
        else:
            count = 0

        percent = (count / theme_count_filtered) if theme_count_filtered else 0
        theme_rows.append(
            {
                "theme": theme_column,
                "count": count,
                "percent": f"{percent:.1%}",
            }
        )

    theme_rows.sort(key=lambda item: item["count"], reverse=True)
    theme_chart_data = [
        {"name": row["theme"], "value": row["count"]}
        for row in theme_rows[:15]
    ]

    context.update(
        {
            "theme_dim": theme_dim,
            "theme_options": theme_options,
            "theme_selected_vals": theme_selected_vals,
            "theme_tag": theme_tag,
            "theme_count_filtered": theme_count_filtered,
            "theme_rows": theme_rows,
            "theme_chart_data": theme_chart_data,
        }
    )

    # Quotes tab state
    quote_dim = request.GET.get("quote_dim", "All")
    if quote_dim not in ["All"] + DEMOGRAPHIC_COLS:
        quote_dim = "All"

    quote_options = []
    quote_selected_vals = ["All"]
    filtered_quotes = df.copy()

    if quote_dim != "All":
        quote_options = _options_for_column(df, quote_dim)
        quote_selected_vals = _normalize_multiselect(
            request.GET.getlist("quote_vals"),
            quote_options,
        )

        if "All" not in quote_selected_vals:
            filtered_quotes = filtered_quotes[
                filtered_quotes[quote_dim].astype(str).isin(quote_selected_vals)
            ]

    quote_theme = request.GET.get("quote_theme", "All")
    if quote_theme not in ["All"] + theme_cols:
        quote_theme = "All"

    if quote_theme != "All" and quote_theme in filtered_quotes.columns:
        filtered_quotes = filtered_quotes[_truthy_mask(filtered_quotes[quote_theme])]

    quote_tag = request.GET.get("quote_tag", "All")
    if quote_tag not in ["All"] + TAGS:
        quote_tag = "All"

    if quote_tag != "All" and quote_tag in filtered_quotes.columns:
        filtered_quotes = filtered_quotes[_truthy_mask(filtered_quotes[quote_tag])]

    quote_count_filtered = len(filtered_quotes)
    quote_tag_chart_data = []
    for tag in TAGS:
        if tag in filtered_quotes.columns and quote_count_filtered > 0:
            tag_count = int(_truthy_mask(filtered_quotes[tag]).sum())
        else:
            tag_count = 0
        quote_tag_chart_data.append({"name": tag, "value": tag_count})

    quote_display_cols = []
    if quote_dim != "All" and quote_dim in filtered_quotes.columns:
        quote_display_cols.append(quote_dim)
    if "Comment" in filtered_quotes.columns:
        quote_display_cols.append("Comment")
    if quote_theme != "All" and quote_theme in filtered_quotes.columns:
        quote_display_cols.append(quote_theme)
    if quote_tag != "All" and quote_tag in filtered_quotes.columns:
        quote_display_cols.append(quote_tag)

    quote_table_headers = []
    quote_table_rows = []
    quote_table_truncated = False

    if quote_display_cols and not filtered_quotes.empty:
        display_df = filtered_quotes[quote_display_cols].copy()
        display_df.insert(0, "Row index", display_df.index.astype(str))

        quote_table_headers = display_df.columns.tolist()

        table_df = display_df.head(250)
        quote_table_rows = [
            ["" if pd.isna(value) else str(value) for value in row]
            for row in table_df.itertuples(index=False, name=None)
        ]
        quote_table_truncated = len(display_df) > len(table_df)

    quote_index_options = []
    if not filtered_quotes.empty and "Comment" in filtered_quotes.columns:
        for idx, comment in filtered_quotes["Comment"].head(500).items():
            clean_comment = str(comment).replace("\n", " ").strip()
            snippet = clean_comment[:80]
            if len(clean_comment) > 80:
                snippet += "..."
            quote_index_options.append({"value": str(idx), "label": f"{idx}: {snippet}"})

    context_idx = request.GET.get("context_idx", "")
    quote_context_pairs = []
    if context_idx:
        try:
            numeric_idx = int(context_idx)
        except ValueError:
            numeric_idx = None

        if numeric_idx is not None and numeric_idx in filtered_quotes.index:
            context_cols = [
                col
                for col in DEMOGRAPHIC_COLS + theme_cols + TAGS + ["Comment"]
                if col in filtered_quotes.columns
            ]
            context_row = filtered_quotes.loc[numeric_idx, context_cols]
            if isinstance(context_row, pd.DataFrame):
                context_row = context_row.iloc[0]
            quote_context_pairs = [
                {
                    "key": column,
                    "value": "" if pd.isna(value) else str(value),
                }
                for column, value in context_row.items()
            ]

    context.update(
        {
            "quote_dim": quote_dim,
            "quote_options": quote_options,
            "quote_selected_vals": quote_selected_vals,
            "quote_theme": quote_theme,
            "quote_tag": quote_tag,
            "quote_count_filtered": quote_count_filtered,
            "quote_tag_chart_data": quote_tag_chart_data,
            "quote_table_headers": quote_table_headers,
            "quote_table_rows": quote_table_rows,
            "quote_table_truncated": quote_table_truncated,
            "quote_index_options": quote_index_options,
            "context_idx": context_idx,
            "quote_context_pairs": quote_context_pairs,
        }
    )

    return render(request, "dashboard/home.html", context)
