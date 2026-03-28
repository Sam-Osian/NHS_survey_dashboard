from pathlib import Path

import pandas as pd
from django.http import JsonResponse
from django.shortcuts import render

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
VALID_TABS = {"overview", "themes"}
DATASET_PATH = Path(__file__).resolve().parent.parent / "data" / "outputs" / "2024" / "comments_2024.csv"


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
    active_tab = request.GET.get("tab", "overview")
    if active_tab not in VALID_TABS:
        active_tab = "overview"

    context: dict = {
        "active_tab": active_tab,
        "data_loaded": False,
        "dataset_filename": DATASET_PATH.name,
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

    if not DATASET_PATH.exists():
        context["data_error"] = f"Dataset not found at {DATASET_PATH}."
        return render(request, "dashboard/home.html", context)

    try:
        df, missing_cols = _load_data(DATASET_PATH)
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
    context["active_theme_count"] = sum(
        1 for col in theme_cols if int(_truthy_mask(df[col]).sum()) > 0
    )

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
    max_theme_count = theme_rows[0]["count"] if theme_rows else 1
    for row in theme_rows:
        row["bar_pct"] = round((row["count"] / max_theme_count) * 100, 1) if max_theme_count else 0
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


# ── JSON API views (used by client-side live filters) ──────────────────────

def _build_overview_data(df, group_col, total_responses):
    counts = df[group_col].dropna().astype(str).value_counts().sort_index()
    rows = []
    chart = []
    for label, count in counts.items():
        c = int(count)
        pct = (c / total_responses) if total_responses else 0
        rows.append({"label": label, "count": c, "percent": f"{pct:.1%}"})
        chart.append({"name": label, "value": c, "percent": round(pct * 100, 2)})
    return {"chart_data": chart, "table_rows": rows, "count": len(df)}


def _build_themes_data(df, theme_cols, total):
    rows = []
    for col in theme_cols:
        count = int(_truthy_mask(df[col]).sum()) if col in df.columns else 0
        pct = (count / total) if total else 0
        rows.append({"theme": col, "count": count, "percent": f"{pct:.1%}"})
    rows.sort(key=lambda r: r["count"], reverse=True)
    max_c = rows[0]["count"] if rows else 1
    for r in rows:
        r["bar_pct"] = round((r["count"] / max_c) * 100, 1) if max_c else 0
    chart = [{"name": r["theme"], "value": r["count"]} for r in rows[:15]]
    return {"chart_data": chart, "theme_rows": rows, "count": total}


def api_overview(request):
    if not DATASET_PATH.exists():
        return JsonResponse({"error": "Dataset not found."}, status=404)
    try:
        df, missing = _load_data(DATASET_PATH)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)
    if missing:
        return JsonResponse({"error": f"Missing columns: {', '.join(missing)}"}, status=400)

    group_col = request.GET.get("dim", DEMOGRAPHIC_COLS[0])
    if group_col not in DEMOGRAPHIC_COLS:
        group_col = DEMOGRAPHIC_COLS[0]

    total = len(df)
    data = _build_overview_data(df, group_col, total)
    data["total"] = total
    return JsonResponse(data)


def api_themes(request):
    if not DATASET_PATH.exists():
        return JsonResponse({"error": "Dataset not found."}, status=404)
    try:
        df, missing = _load_data(DATASET_PATH)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)
    if missing:
        return JsonResponse({"error": f"Missing columns: {', '.join(missing)}"}, status=400)

    all_cols = df.columns.tolist()
    theme_cols = [c for c in all_cols if c not in DEMOGRAPHIC_COLS + ["Comment"] + TAGS]
    total = len(df)

    dim = request.GET.get("dim", "All")
    if dim not in ["All"] + DEMOGRAPHIC_COLS:
        dim = "All"

    filtered = df.copy()
    if dim != "All":
        filtered = filtered[filtered[dim].notna()]

    data = _build_themes_data(filtered, theme_cols, len(filtered))
    data["total"] = total
    return JsonResponse(data)

def api_theme_quotes(request):
    if not DATASET_PATH.exists():
        return JsonResponse({"error": "Dataset not found."}, status=404)
    try:
        df, missing = _load_data(DATASET_PATH)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)
    if missing:
        return JsonResponse({"error": f"Missing columns: {', '.join(missing)}"}, status=400)

    theme = request.GET.get("theme", "All")
    dim = request.GET.get("dim", "All")
    tag = request.GET.get("tag", "All")

    all_cols = df.columns.tolist()
    theme_cols = [c for c in all_cols if c not in DEMOGRAPHIC_COLS + ["Comment"] + TAGS]

    filtered = df.copy()

    # Filter by theme only when a specific theme is selected
    if theme != "All":
        if theme not in theme_cols:
            return JsonResponse({"quotes": [], "count": 0, "truncated": False})
        filtered = filtered[_truthy_mask(filtered[theme])]

    if dim != "All" and dim in DEMOGRAPHIC_COLS and dim in filtered.columns:
        filtered = filtered[filtered[dim].notna()]

    if tag != "All" and tag in TAGS and tag in filtered.columns:
        filtered = filtered[_truthy_mask(filtered[tag])]

    total_filtered = len(filtered)
    sample = filtered.head(200)

    quotes = []
    for idx, row in sample.iterrows():
        comment = str(row.get("Comment", "")).strip()
        if not comment:
            continue
        active_tags = [t for t in TAGS if t in row and pd.notna(row[t]) and str(row[t]).strip().lower() in TRUTHY_VALUES]
        dim_value = ""
        if dim != "All" and dim in row and pd.notna(row[dim]):
            dim_value = str(row[dim]).strip()
        demographics = {
            col: str(row[col]).strip()
            for col in DEMOGRAPHIC_COLS
            if col in row and pd.notna(row[col]) and str(row[col]).strip() not in ("", "nan")
        }
        quotes.append({
            "row_id": int(idx),
            "comment": comment,
            "dim_label": dim if dim != "All" else "",
            "dim_value": dim_value,
            "tags": active_tags,
            "demographics": demographics,
        })

    return JsonResponse({"quotes": quotes, "count": total_filtered, "truncated": total_filtered > 200})
