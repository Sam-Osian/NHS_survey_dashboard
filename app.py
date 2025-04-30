import streamlit as st
import pandas as pd
import altair as alt

# Page config
st.set_page_config(page_title="Staff Survey Dashboard", layout="wide")

# Sidebar: Data upload
st.sidebar.title("Data Upload")
uploaded_file = st.sidebar.file_uploader("Upload survey CSV", type=["csv"])
if not uploaded_file:
    st.warning("Please upload a CSV file to continue.")
    st.stop()

# Load data with proper typing
def load_data(file):
    df = pd.read_csv(file)
    # Drop index column if present
    if 'Unnamed: 0' in df.columns:
        df = df.drop(columns=['Unnamed: 0'])
    # Ensure 'Comment' column is string to avoid float indexing errors
    if 'Comment' in df.columns:
        df['Comment'] = df['Comment'].fillna('').astype(str)
    return df

# Read and prepare data
df = load_data(uploaded_file)
# Rename columns for display consistency
rename_map = {
    'occupation_group': 'Occupation group',
    'lgbtq': 'Sexuality',
    'disability': 'Disability',
    'age': 'Age group',
    'service_line': 'Service line',
    'division': 'Division',  # keep title case
    'gender': 'Gender',
    'payband': 'Pay band',
    'staff_group': 'Staff group',
    'bme': 'Ethnicity'
}
df = df.rename(columns=rename_map)

total_responses = len(df)

# Define columns after rename
demographic_cols = [
    'Occupation group', 'Sexuality', 'Disability', 'Age group', 'Service line',
    'Division', 'Gender', 'Pay band', 'Staff group', 'Ethnicity'
]
tags = ['suggestion', 'urgent', 'positive', 'negative']
all_cols = df.columns.tolist()
# Identify theme columns dynamically (exclude demographics, comments, and tags)
theme_cols = [c for c in all_cols if c not in demographic_cols + ['Comment'] + tags]

# Validation: check for missing expected columns
expected_cols = demographic_cols + ['Comment'] + tags
missing_cols = [c for c in expected_cols if c not in df.columns]
if missing_cols:
    st.error(f"Missing expected columns: {', '.join(missing_cols)}. Please check your CSV file and try again.")
    st.stop()

# App title
st.title("Staff Survey Open-Box Comments Dashboard")

# Create tabs
overview_tab, themes_tab, quotes_tab = st.tabs(["Overview", "Themes", "Quotation Bank"])

# --- Overview Tab ---
with overview_tab:
    st.header("Survey Completion by Staff Group")

    # Select dimension
    sel_group = st.selectbox("Select staff group dimension", demographic_cols)
    # Multi-select filter
    options = sorted(df[sel_group].dropna().unique().tolist())
    sel_vals = st.multiselect(
        f"Select {sel_group}", options=["All"] + options,
        default=["All"], key='overview_vals'
    )
    if "All" in sel_vals and len(sel_vals) > 1:
        sel_vals = [v for v in sel_vals if v != "All"]
    if not sel_vals:
        sel_vals = ["All"]
    filtered = df.copy() if "All" in sel_vals else df[df[sel_group].isin(sel_vals)]

    # Response counts
    count_filtered = len(filtered)
    st.write(
        f"Showing {count_filtered} out of {total_responses} responses"
        if count_filtered != total_responses else
        f"Showing {total_responses} responses"
    )

    # Compute counts and percentages
    counts = filtered[sel_group].value_counts().sort_index()
    counts_df = counts.rename_axis(sel_group).reset_index(name='Count')
    counts_df['Percent'] = counts_df['Count'] / total_responses

    # Bar chart with percentage tooltip
    chart = alt.Chart(counts_df).mark_bar().encode(
        x=alt.X(f'{sel_group}:N', title=sel_group),
        y=alt.Y('Count:Q', title='Count'),
        tooltip=[alt.Tooltip('Percent:Q', format='.1%', title='Percentage')]
    )
    st.altair_chart(chart, use_container_width=True)

    # Table mirroring chart
    display_df = counts_df.copy()
    display_df['Percent'] = display_df['Percent'].map("{:.1%}".format)
    st.dataframe(display_df)

# --- Themes Tab ---
with themes_tab:
    st.header("Theme Tabulation")
    grp_dim = st.selectbox("Staff group dimension", ["All"] + demographic_cols, key='theme_dim')
    if grp_dim == "All":
        filtered = df.copy()
    else:
        options = sorted(df[grp_dim].dropna().unique().tolist())
        sel_vals = st.multiselect(f"Select {grp_dim}", options=["All"] + options, default=["All"], key='theme_vals')
        if "All" in sel_vals and len(sel_vals) > 1:
            sel_vals = [v for v in sel_vals if v != "All"]
        if not sel_vals:
            sel_vals = ["All"]
        filtered = df.copy() if "All" in sel_vals else df[df[grp_dim].isin(sel_vals)]

    # Response counts
    count_filtered = len(filtered)
    st.write(
        f"Showing {count_filtered} out of {total_responses} responses"
        if count_filtered != total_responses else
        f"Showing {total_responses} responses"
    )

    # AI disclaimer with icon
    st.markdown("ℹ️ *These themes were identified and assigned using AI. AI isn’t perfect and may make mistakes.*")

    # Count themes
    theme_counts = []
    for theme in theme_cols:
        ct = filtered[theme].astype(str).str.lower().isin(['yes','true','1']).sum()
        pct = ct / count_filtered if count_filtered else 0
        theme_counts.append({'Theme': theme, 'Count': ct, 'Percent': f"{pct:.1%}"})
    theme_df = pd.DataFrame(theme_counts).sort_values('Count', ascending=False)
    st.dataframe(theme_df)

# --- Quotation Bank Tab ---
with quotes_tab:
    st.header("Quotation Bank")
    q_dim = st.selectbox("Staff group dimension", ["All"] + demographic_cols, key='quote_dim')
    if q_dim == "All":
        q_filtered = df.copy()
    else:
        options = sorted(df[q_dim].dropna().unique().tolist())
        q_sel = st.multiselect(f"Select {q_dim}", options=["All"] + options, default=["All"], key='quote_vals')
        if "All" in q_sel and len(q_sel) > 1:
            q_sel = [v for v in q_sel if v != "All"]
        if not q_sel:
            q_sel = ["All"]
        q_filtered = df.copy() if "All" in q_sel else df[df[q_dim].isin(q_sel)]

    sel_theme = st.selectbox("Theme", options=["All"] + theme_cols, key='quote_theme')
    if sel_theme != "All":
        q_filtered = q_filtered[q_filtered[sel_theme].astype(str).str.lower().isin(['yes','true','1'])]

    sel_tags = st.multiselect("Tags", options=["All"] + tags, default=["All"], key='quote_tags')
    if "All" in sel_tags and len(sel_tags) > 1:
        sel_tags = [v for v in sel_tags if v != "All"]
    if not sel_tags:
        sel_tags = ["All"]
    if "All" not in sel_tags:
        tag_mask = pd.Series(False, index=q_filtered.index)
        for tag in sel_tags:
            tag_mask |= q_filtered[tag].astype(str).str.lower().isin(['yes','true','1'])
        q_filtered = q_filtered[tag_mask]

    # Response counts
    count_filtered = len(q_filtered)
    st.write(
        f"Showing {count_filtered} out of {total_responses} responses"
        if count_filtered != total_responses else
        f"Showing {total_responses} responses"
    )

    # AI disclaimer with icon
    st.markdown("ℹ️ *Themes and tags were identified and assigned using AI. AI isn’t perfect and may make mistakes.*")

    # Display comments
    cols = []
    if q_dim != "All": cols.append(q_dim)
    cols.append('Comment')
    if sel_theme != "All": cols.append(sel_theme)
    if "All" not in sel_tags: cols += sel_tags
    st.dataframe(q_filtered[cols])

    # Context viewer
    if not q_filtered.empty:
        sel_idx = st.selectbox(
            "Select a response to see context:",
            options=[None] + q_filtered.index.tolist(),
            format_func=lambda x: f"{x}: {q_filtered.loc[x,'Comment'][:50]}..." if x is not None else "None"
        )
        if sel_idx is not None and st.button("See context"):
            context_cols = demographic_cols + theme_cols + tags + ['Comment']
            st.write("**Context for selected response:**")
            st.dataframe(q_filtered.loc[[sel_idx], context_cols])
