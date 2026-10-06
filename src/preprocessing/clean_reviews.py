"""Customer review preprocessing pipeline for CustomerVoice AI.

Provides modular cleaning functions for:
- Removing completely empty rows
- Removing duplicate review IDs and redundant review texts
- Normalizing whitespace without stripping punctuation or critical stopwords
- Preserving negations (e.g., 'not', 'never', 'don't', 'didn't')
- Normalizing date formats to ISO-8601 (YYYY-MM-DD)
- Validating rating ranges
- Standardizing final output schema
"""

import html
import logging
import re
from typing import Any, List, Optional, Union
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Standardized output schema columns
PREPROCESSED_COLUMNS: List[str] = [
    "review_id",
    "review_text",
    "cleaned_text",
    "rating",
    "review_date",
    "product_id",
    "product_name",
    "category",
    "campaign",
    "source",
]


def clean_text(text: Any) -> str:
    """Normalize text while preserving punctuation, stopwords, and negations.

    Performs:
    - HTML entity unescaping (&amp; -> &, &quot; -> ", etc.)
    - HTML tag removal (<br>, <p>, etc.)
    - Smart quote / typographic character normalization
    - Whitespace normalization (collapsing tabs, newlines, multiple spaces)
    - Trimming leading/trailing whitespace

    Preserves:
    - Punctuation (critical for sentiment analysis)
    - Negations (not, never, don't, didn't, etc.)
    - Letter casing
    """
    if text is None or pd.isna(text):
        return ""

    text_str = str(text)

    # 1. Unescape HTML entities
    text_str = html.unescape(text_str)

    # 2. Remove HTML tags
    text_str = re.sub(r"<[^>]+>", " ", text_str)

    # 3. Normalize curly / smart quotes
    text_str = text_str.replace("’", "'").replace("‘", "'")
    text_str = text_str.replace("“", '"').replace("”", '"')

    # 4. Collapse multiple whitespace characters into a single space
    text_str = re.sub(r"\s+", " ", text_str)

    # 5. Trim leading and trailing whitespace
    return text_str.strip()


def normalize_date(date_val: Any) -> Optional[str]:
    """Convert various date representations into ISO YYYY-MM-DD string.

    Returns None if date_val is missing, empty, or unparseable.
    """
    if date_val is None or pd.isna(date_val) or str(date_val).strip() == "":
        return None

    try:
        dt = pd.to_datetime(date_val, errors="coerce")
        if pd.isna(dt):
            return None
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None


def validate_rating(
    rating_val: Any,
    min_rating: float = 1.0,
    max_rating: float = 5.0,
) -> Optional[float]:
    """Validate that rating is numeric and falls within [min_rating, max_rating].

    Returns float rating if valid, otherwise returns None.
    """
    if rating_val is None or pd.isna(rating_val):
        return None

    try:
        val = float(rating_val)
        if min_rating <= val <= max_rating:
            return val
        return None
    except (ValueError, TypeError):
        return None


def clean_reviews_dataframe(
    df: pd.DataFrame,
    drop_duplicate_ids: bool = True,
    drop_duplicate_texts: bool = True,
    min_rating: float = 1.0,
    max_rating: float = 5.0,
) -> pd.DataFrame:
    """Preprocess customer reviews DataFrame.

    Preserves the original DataFrame (works strictly on a copy).

    Steps:
    1. Remove completely empty rows.
    2. Ensure review_id and review_text exist.
    3. Drop rows with null or empty review_id / review_text.
    4. Remove duplicate review IDs.
    5. Remove duplicate review text (where identical).
    6. Normalize whitespace to generate `cleaned_text`.
    7. Normalize date formats.
    8. Validate rating values.
    9. Standardize output schema to PREPROCESSED_COLUMNS.

    Args:
        df: Input raw or ingested DataFrame.
        drop_duplicate_ids: Whether to enforce unique review_id.
        drop_duplicate_texts: Whether to remove duplicate review_text.
        min_rating: Minimum acceptable rating value.
        max_rating: Maximum acceptable rating value.

    Returns:
        A new DataFrame strictly matching PREPROCESSED_COLUMNS.
    """
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=PREPROCESSED_COLUMNS)

    # 8. Preserve original raw data by working on a deep copy
    cleaned = df.copy()

    # 1. Remove completely empty rows
    cleaned = cleaned.dropna(how="all")
    if cleaned.empty:
        return pd.DataFrame(columns=PREPROCESSED_COLUMNS)

    # Validate review_id and review_text presence
    if "review_id" not in cleaned.columns or "review_text" not in cleaned.columns:
        raise ValueError(
            "DataFrame must contain 'review_id' and 'review_text' columns for preprocessing."
        )

    # Convert review_id and review_text to string and strip
    cleaned["review_id"] = cleaned["review_id"].astype(str).str.strip()
    cleaned["review_text"] = cleaned["review_text"].astype(str).str.strip()

    # 5. Handle null and empty review_id and review_text
    cleaned = cleaned[
        (cleaned["review_id"] != "")
        & (cleaned["review_id"].str.lower() != "nan")
        & (cleaned["review_id"].str.lower() != "none")
        & (cleaned["review_text"] != "")
        & (cleaned["review_text"].str.lower() != "nan")
        & (cleaned["review_text"].str.lower() != "none")
    ]

    # 2. Remove duplicate review IDs
    if drop_duplicate_ids:
        cleaned = cleaned.drop_duplicates(subset=["review_id"], keep="first")

    # 4. Generate cleaned_text (whitespace normalized, HTML removed, negations/punctuation preserved)
    cleaned["cleaned_text"] = cleaned["review_text"].apply(clean_text)

    # Filter out rows where cleaned_text is empty
    cleaned = cleaned[cleaned["cleaned_text"] != ""]

    # 3. Remove duplicate review text where appropriate
    if drop_duplicate_texts:
        cleaned = cleaned.drop_duplicates(subset=["cleaned_text"], keep="first")

    # 6. Normalize date formats
    if "review_date" in cleaned.columns:
        cleaned["review_date"] = cleaned["review_date"].apply(normalize_date)
    else:
        cleaned["review_date"] = None

    # 7. Validate rating values
    if "rating" in cleaned.columns:
        cleaned["rating"] = cleaned["rating"].apply(
            lambda r: validate_rating(r, min_rating=min_rating, max_rating=max_rating)
        )
    else:
        cleaned["rating"] = None

    # Fill optional columns if missing
    for col in PREPROCESSED_COLUMNS:
        if col not in cleaned.columns:
            cleaned[col] = None

    # Reorder and project strictly to required output columns
    cleaned = cleaned[PREPROCESSED_COLUMNS].reset_index(drop=True)

    logger.info(
        "Preprocessing complete: %d initial rows -> %d clean rows.",
        len(df),
        len(cleaned),
    )

    return cleaned
