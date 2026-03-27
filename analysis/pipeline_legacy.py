from __future__ import annotations

import json
import os
from typing import Dict, List, Literal

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ValidationError, create_model


class Theme(BaseModel):
    name: str
    description: str


class ThemeList(BaseModel):
    themes: List[Theme]


class MetaLabels(BaseModel):
    suggestion: Literal["Yes", "No"]
    urgent: Literal["Yes", "No"]
    positive: Literal["Yes", "No"]
    negative: Literal["Yes", "No"]


def _strip_json_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").strip()
    if cleaned.endswith("```"):
        cleaned = cleaned.removesuffix("```").strip()
    return cleaned


def _load_client() -> OpenAI:
    load_dotenv("api.env")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not found. Set it in environment or api.env before running analyse."
        )
    return OpenAI(api_key=api_key)


def _build_theme_prompt(themes_text: str) -> str:
    return f"""
You are an expert in qualitative analysis and topic modelling for internal staff surveys, with the goal of supporting organisational change.

Given the following anonymised NHS staff survey responses, identify latent topics or themes that emerge organically from the data. Avoid simply repeating comments; instead, synthesise underlying patterns, concepts, concerns, or sentiments expressed by staff.

Ensure that the themes you identify are fair, logical, and consistent, as I will be tabulating this information for further analysis.

Group similar ideas together unless there are clear, meaningful differences. Only split into separate themes when distinct patterns, concerns, or experiences emerge.

Keep the number of themes proportionate to the diversity of the staff comments: if many comments express similar ideas, consolidate them into broader themes; if comments express genuinely different ideas, capture those differences.

Your themes should be blind to sentiment; there should be no good or bad themes. For example, there shouldn't be a "Positive team dynamics and support" theme. Instead, there should be a "Team dynamics/support" theme which holds both positive and negative responses.

Do not use nested or sub-themes.

Return your output strictly as a JSON object with a single key "themes", which maps to a list of objects. Each object must have two keys:
- "name": the concise theme name (string)
- "description": a very brief, 1–2 sentence description of what the theme covers (string)

Here are the survey responses:

{themes_text}
"""


def _generate_theme_list(client: OpenAI, comments: pd.Series) -> tuple[ThemeList, str]:
    prompt = _build_theme_prompt("\n".join(comments.dropna().astype(str)))
    response = client.responses.create(model="gpt-4.1", input=prompt)
    raw_text = _strip_json_fence(response.output_text)
    parsed = ThemeList(**json.loads(raw_text))
    return parsed, raw_text


def _assign_themes_for_comment(
    client: OpenAI, comment_text: str, theme_names: list[str], assignment_model
) -> Dict[str, str]:
    prompt = f"""
You are an expert in qualitative analysis for internal staff surveys.

Given the following survey comment:

"{comment_text}"

Assign "Yes" or "No" to each of the following themes based on whether the comment clearly relates to it. Be strict: only assign "Yes" if the theme is explicitly relevant.

Return your response strictly as a JSON object with each theme as a key and "Yes" or "No" as the value. No commentary.

Themes:
{theme_names}
"""
    response = client.responses.create(model=assignment_model, input=prompt)
    text = _strip_json_fence(response.output_text)

    ThemeAssignment = create_model(
        "ThemeAssignment",
        **{name: (Literal["Yes", "No"], ...) for name in theme_names},
    )
    try:
        validated = ThemeAssignment(**json.loads(text))
        return validated.model_dump()
    except (json.JSONDecodeError, ValidationError):
        return {name: "No" for name in theme_names}


def _assign_meta_for_comment(client: OpenAI, comment_text: str, assignment_model) -> Dict[str, str]:
    prompt = f"""
You are an expert in analysing internal NHS staff survey responses.

Given the following staff comment, label the presence of the following features using "Yes" or "No" only:

1. **suggestion**: Does the comment contain a **tangible** suggestion, proposal, or ask that could, in theory, be easily actioned? Purely negative comments that do not lend themselves to precise actionability are **not** suggestions. A suggestion **must** also be precise and **not** vague or general
2. **urgent**: Does the comment contain an urgent or time-sensitive concern which is **serious**? Long-standing issues are likely not urgent.
3. **positive**: Does the comment contain praise, appreciation, or a generally positive sentiment?
4. **negative**: Does the comment contain criticism, complaint, or a generally negative sentiment?

Be strict and consistent in your interpretation. None of the above flags are mutually exclusive (i.e. something can contain both positive and negative sentiment, or can be a suggestion and urgent).

Equally, it is perfectly acceptable if the comment reflects none of the above tags.

Output only a valid JSON object for each of the above flags.

Comment:
"{comment_text}"
"""
    response = client.responses.create(model=assignment_model, input=prompt)
    text = _strip_json_fence(response.output_text)

    try:
        validated = MetaLabels(**json.loads(text))
        return validated.model_dump()
    except (json.JSONDecodeError, ValidationError):
        return {"suggestion": "No", "urgent": "No", "positive": "No", "negative": "No"}


def run_legacy_pipeline(
    merged_df: pd.DataFrame,
    theme_model: str = "gpt-4.1",
    assignment_model: str = "gpt-4.1-mini",
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """Reproduce the legacy notebook method over a merged survey dataframe."""
    client = _load_client()

    parsed_themes, raw_themes_json = _generate_theme_list(client, merged_df["Comment"])
    theme_names = [theme.name for theme in parsed_themes.themes]

    theme_assignments = [
        _assign_themes_for_comment(client, str(comment), theme_names, assignment_model)
        for comment in merged_df["Comment"]
    ]
    theme_assignments_df = pd.DataFrame(theme_assignments)
    merged_assigned_full = pd.concat(
        [merged_df.reset_index(drop=True), theme_assignments_df], axis=1
    )

    meta_assignments = [
        _assign_meta_for_comment(client, str(comment), assignment_model)
        for comment in merged_df["Comment"]
    ]
    meta_labels_df = pd.DataFrame(meta_assignments)
    merged_assigned_tagged_full = pd.concat([merged_assigned_full, meta_labels_df], axis=1)

    return merged_assigned_full, merged_assigned_tagged_full, raw_themes_json
