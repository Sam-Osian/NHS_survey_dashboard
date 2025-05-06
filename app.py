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
    'gender': 'Gender',
    'payband': 'Pay band',
    'staff_group': 'Staff group',
    'bme': 'Ethnicity'
}
df = df.rename(columns=rename_map)
# Drop unwanted 'division' column if present
if 'division' in df.columns:
    df = df.drop(columns=['division'])

# Total responses count
total_responses = len(df)

# Define columns after rename
demographic_cols = [
    'Occupation group', 'Sexuality', 'Disability', 'Age group',
    'Service line', 'Gender', 'Pay band', 'Staff group', 'Ethnicity'
]
tags = ['suggestion', 'urgent', 'positive', 'negative'] # Ensure these are actual column names in your CSV for tags
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
    st.markdown("Explore who has taken part in the survey and spot any under- or over-represented groups at a glance. Use the dropdowns to slice your data by job role, age bracket, pay band, ethnicity, and more — so you can quickly check that every voice is being heard and decide where to focus further engagement.")

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
    filtered_overview = df.copy() if "All" in sel_vals else df[df[sel_group].isin(sel_vals)]

    # Response counts
    count_filtered_overview = len(filtered_overview)
    st.write(
        f"Showing {count_filtered_overview} out of {total_responses} responses"
        if count_filtered_overview != total_responses else
        f"Showing {total_responses} responses"
    )

    # Compute counts and percentages
    counts = filtered_overview[sel_group].value_counts().sort_index()
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
    st.markdown("Dive into the broad topics our AI engine has pulled from open-ended comments—everything from workplace culture to wellbeing to operational bottlenecks. Note that each comment can belong to more than one theme.")
    
    # Demographic filter
    grp_dim_themes = st.selectbox("Staff group dimension", ["All"] + demographic_cols, key='theme_dim')
    filtered_themes = df.copy() # Start with the full dataframe
    if grp_dim_themes != "All":
        options_themes = sorted(df[grp_dim_themes].dropna().unique().tolist())
        sel_vals_themes = st.multiselect(f"Select {grp_dim_themes}", options=["All"] + options_themes, default=["All"], key='theme_vals')
        if "All" in sel_vals_themes and len(sel_vals_themes) > 1:
            sel_vals_themes = [v for v in sel_vals_themes if v != "All"]
        if not sel_vals_themes:
            sel_vals_themes = ["All"]
        if "All" not in sel_vals_themes:
             filtered_themes = filtered_themes[filtered_themes[grp_dim_themes].isin(sel_vals_themes)]

    # Tag filter
    sel_tag_themes = st.selectbox("Filter by Tag", options=["All"] + tags, index=0, key='theme_tag_filter')
    if sel_tag_themes != "All":
        # Ensure the tag column exists and filter
        if sel_tag_themes in filtered_themes.columns:
            filtered_themes = filtered_themes[filtered_themes[sel_tag_themes].astype(str).str.lower().isin(['yes','true','1'])]
        else:
            st.warning(f"Tag column '{sel_tag_themes}' not found in the data.")


    # Response counts
    count_filtered_themes = len(filtered_themes)
    st.write(
        f"Showing {count_filtered_themes} out of {total_responses} responses"
        if count_filtered_themes != total_responses else
        f"Showing {total_responses} responses"
    )

    # AI disclaimer with icon
    st.markdown("ℹ️ *These themes and tags were identified and assigned using AI. AI isn’t perfect and may make mistakes.*")

    # Count themes
    theme_counts = []
    if count_filtered_themes > 0: # Avoid division by zero if no responses after filtering
        for theme in theme_cols:
            if theme in filtered_themes.columns: # Check if theme column exists
                ct = filtered_themes[theme].astype(str).str.lower().isin(['yes','true','1']).sum()
                pct = ct / count_filtered_themes 
                theme_counts.append({'Theme': theme, 'Count': ct, 'Percent': f"{pct:.1%}"})
            else:
                st.warning(f"Theme column '{theme}' not found in the data for counting.")
    else: # Handle case with no responses after filtering
         for theme in theme_cols:
            theme_counts.append({'Theme': theme, 'Count': 0, 'Percent': f"{0:.1%}"})

    theme_df = pd.DataFrame(theme_counts).sort_values('Count', ascending=False)
    st.dataframe(theme_df)

# --- Quotation Bank Tab ---
with quotes_tab:
    st.header("Quotation Bank")
    st.markdown("Zero in on the most telling comments to uncover actionable insights within each topic. Filter by demographic group, theme, and tag (e.g., suggestions or urgent issues) to surface real staff voices that can drive targeted improvements in policy, process, and people strategy.")
    
    q_filtered = df.copy() # Start with the full dataframe

    # Demographic filter
    q_dim = st.selectbox("Staff group dimension", ["All"] + demographic_cols, key='quote_dim')
    if q_dim != "All":
        options_quotes = sorted(df[q_dim].dropna().unique().tolist())
        q_sel = st.multiselect(f"Select {q_dim}", options=["All"] + options_quotes, default=["All"], key='quote_vals')
        if "All" in q_sel and len(q_sel) > 1:
            q_sel = [v for v in q_sel if v != "All"]
        if not q_sel:
            q_sel = ["All"]
        if "All" not in q_sel:
            q_filtered = q_filtered[q_filtered[q_dim].isin(q_sel)]

    # Theme filter
    sel_theme_quotes = st.selectbox("Filter by Theme", options=["All"] + theme_cols, key='quote_theme')
    if sel_theme_quotes != "All":
        if sel_theme_quotes in q_filtered.columns:
            q_filtered = q_filtered[q_filtered[sel_theme_quotes].astype(str).str.lower().isin(['yes','true','1'])]
        else:
            st.warning(f"Theme column '{sel_theme_quotes}' not found for filtering.")


    # Tag filter
    sel_tag_quotes = st.selectbox("Filter by Tag", options=["All"] + tags, index=0, key='quote_tag')
    if sel_tag_quotes != "All":
        if sel_tag_quotes in q_filtered.columns:
            q_filtered = q_filtered[q_filtered[sel_tag_quotes].astype(str).str.lower().isin(['yes','true','1'])]
        else:
            st.warning(f"Tag column '{sel_tag_quotes}' not found for filtering.")


    # Response counts
    count_filtered_quotes = len(q_filtered)
    st.write(
        f"Showing {count_filtered_quotes} out of {total_responses} responses"
        if count_filtered_quotes != total_responses else
        f"Showing {total_responses} responses"
    )

    # AI disclaimer with icon
    st.markdown("ℹ️ *Themes and tags were identified and assigned using AI. AI isn’t perfect and may make mistakes.*")

    # Display comments
    cols_to_display = []
    if q_dim != "All" and q_dim in q_filtered.columns : cols_to_display.append(q_dim)
    if 'Comment' in q_filtered.columns: cols_to_display.append('Comment')
    if sel_theme_quotes != "All" and sel_theme_quotes in q_filtered.columns: cols_to_display.append(sel_theme_quotes)
    if sel_tag_quotes != "All" and sel_tag_quotes in q_filtered.columns: cols_to_display.append(sel_tag_quotes)
    
    # Ensure all columns to display actually exist in q_filtered
    final_cols_to_display = [col for col in cols_to_display if col in q_filtered.columns]
    if not q_filtered.empty and final_cols_to_display:
        st.dataframe(q_filtered[final_cols_to_display])
    elif q_filtered.empty:
        st.write("No comments match the selected filters.")
    else:
        st.write("Select columns to display comments.")


    # Context viewer
    if not q_filtered.empty and 'Comment' in q_filtered.columns:
        sel_idx = st.selectbox(
            "Select a response to see context:",
            options=[None] + q_filtered.index.tolist(),
            format_func=lambda x: f"{x}: {q_filtered.loc[x,'Comment'][:50]}..." if x is not None and x in q_filtered.index else "None",
            key='quote_context_select'
        )
        if sel_idx is not None and st.button("See context", key='quote_context_button'):
            context_cols_base = demographic_cols + theme_cols + tags + ['Comment']
            # Ensure context columns exist in the dataframe
            final_context_cols = [col for col in context_cols_base if col in q_filtered.columns]
            if sel_idx in q_filtered.index:
                 st.write("**Context for selected response:**")
                 st.dataframe(q_filtered.loc[[sel_idx], final_context_cols])
            else:
                 st.warning("Selected response index is no longer valid. Please re-select.")