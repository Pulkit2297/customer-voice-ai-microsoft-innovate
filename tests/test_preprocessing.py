"""Tests for Phase 2: Customer review preprocessing pipeline."""

import numpy as np
import pandas as pd
import pytest

from src.preprocessing.clean_reviews import (
    PREPROCESSED_COLUMNS,
    clean_reviews_dataframe,
    clean_text,
    normalize_date,
    validate_rating,
)


# -----------------------------------------------------------------------------
# Unit Tests for Individual Cleaning Helpers
# -----------------------------------------------------------------------------


def test_clean_text_normalizes_whitespace():
    """Verify that multiple spaces, tabs, and newlines collapse into single spaces."""
    raw = "   This   is   a \t review with   multiple\n\n\nspaces!   "
    cleaned = clean_text(raw)
    assert cleaned == "This is a review with multiple spaces!"


def test_clean_text_preserves_punctuation():
    """Verify that sentiment-critical punctuation is preserved."""
    raw = "Loved it! Best purchase ever?! Highly recommended..."
    cleaned = clean_text(raw)
    assert cleaned == "Loved it! Best purchase ever?! Highly recommended..."


def test_clean_text_preserves_negations():
    """Verify that negations (not, never, don't, didn't) are completely preserved."""
    raw = "I do not like this, never buy it, don't waste money, and didn't arrive on time."
    cleaned = clean_text(raw)
    assert "not" in cleaned
    assert "never" in cleaned
    assert "don't" in cleaned
    assert "didn't" in cleaned
    assert cleaned == raw


def test_clean_text_handles_html_entities_and_tags():
    """Verify that HTML tags and entities are stripped / unescaped."""
    raw = "Great product &amp; fast shipping!<br/><p>Will order again &gt; competitors.</p>"
    cleaned = clean_text(raw)
    assert cleaned == "Great product & fast shipping! Will order again > competitors."


def test_clean_text_handles_null():
    """Verify that None or NaN returns an empty string."""
    assert clean_text(None) == ""
    assert clean_text(np.nan) == ""


def test_normalize_date_formats():
    """Verify that various date representations normalize to YYYY-MM-DD."""
    assert normalize_date("2023-11-25") == "2023-11-25"
    assert normalize_date("11/25/2023") == "2023-11-25"
    assert normalize_date("2023-11-25 14:32:00") == "2023-11-25"
    assert normalize_date("25 Nov 2023") == "2023-11-25"
    assert normalize_date(None) is None
    assert normalize_date("invalid_date_string") is None
    assert normalize_date("") is None


def test_validate_rating():
    """Verify that rating validates numeric bounds 1.0 to 5.0."""
    assert validate_rating(5) == 5.0
    assert validate_rating("4.5") == 4.5
    assert validate_rating(1.0) == 1.0
    assert validate_rating(0.5) is None  # below 1.0
    assert validate_rating(6.0) is None  # above 5.0
    assert validate_rating(-1) is None
    assert validate_rating("invalid") is None
    assert validate_rating(None) is None


# -----------------------------------------------------------------------------
# Pipeline Tests on DataFrames
# -----------------------------------------------------------------------------


@pytest.fixture
def sample_dirty_dataframe() -> pd.DataFrame:
    """Fixture with various data quality issues."""
    return pd.DataFrame([
        # Valid row 1
        {
            "review_id": "REV_001",
            "review_text": "  Great device, highly recommended!  ",
            "rating": 5,
            "review_date": "2023-08-15",
            "product_id": "PROD_1",
            "product_name": "Kindle Reader",
            "category": "Electronics",
            "campaign": "Summer Sale",
            "source": "Amazon",
        },
        # Duplicate review_id (should be dropped)
        {
            "review_id": "REV_001",
            "review_text": "Different text with duplicate id",
            "rating": 4,
            "review_date": "2023-08-16",
        },
        # Duplicate review_text (should be dropped)
        {
            "review_id": "REV_002",
            "review_text": "Great device, highly recommended!",
            "rating": 5,
            "review_date": "2023-08-17",
        },
        # Null review_text (should be dropped)
        {
            "review_id": "REV_003",
            "review_text": None,
            "rating": 1,
            "review_date": "2023-08-18",
        },
        # Whitespace-only review_text (should be dropped)
        {
            "review_id": "REV_004",
            "review_text": "    ",
            "rating": 2,
            "review_date": "2023-08-19",
        },
        # Completely empty row (should be dropped)
        {
            "review_id": None,
            "review_text": None,
            "rating": None,
            "review_date": None,
        },
        # Out-of-bounds rating (should be coerced to None)
        {
            "review_id": "REV_005",
            "review_text": "I didn't like the battery life at all.",
            "rating": 10,
            "review_date": "08/20/2023",
        },
        # Non-standard date format (should normalize to 2023-08-21)
        {
            "review_id": "REV_006",
            "review_text": "Never buying this brand again, it is not durable.",
            "rating": "1.0",
            "review_date": "21 Aug 2023",
        },
    ])


def test_clean_reviews_dataframe_pipeline(sample_dirty_dataframe: pd.DataFrame):
    """Verify that end-to-end pipeline handles all cleaning requirements."""
    original_copy = sample_dirty_dataframe.copy(deep=True)

    cleaned = clean_reviews_dataframe(sample_dirty_dataframe)

    # 8. Verify original data was preserved and not modified
    pd.testing.assert_frame_equal(sample_dirty_dataframe, original_copy)

    # Verify output columns match the expected 10 columns exactly
    assert list(cleaned.columns) == PREPROCESSED_COLUMNS

    # 1. Completely empty row removed
    # 2. Duplicate ID REV_001 removed
    # 3. Duplicate text of REV_001 removed (REV_002)
    # 5. Null review text (REV_003) and empty whitespace text (REV_004) removed
    remaining_ids = set(cleaned["review_id"])
    assert "REV_001" in remaining_ids
    assert "REV_002" not in remaining_ids
    assert "REV_003" not in remaining_ids
    assert "REV_004" not in remaining_ids
    assert "REV_005" in remaining_ids
    assert "REV_006" in remaining_ids

    # 4. Whitespace normalized in cleaned_text
    rev1 = cleaned[cleaned["review_id"] == "REV_001"].iloc[0]
    assert rev1["cleaned_text"] == "Great device, highly recommended!"

    # 6. Date format normalized
    rev6 = cleaned[cleaned["review_id"] == "REV_006"].iloc[0]
    assert rev6["review_date"] == "2023-08-21"

    # 7. Rating validation
    rev5 = cleaned[cleaned["review_id"] == "REV_005"].iloc[0]
    assert pd.isna(rev5["rating"])  # Rating was 10 (out of bounds)
    assert rev1["rating"] == 5.0
    assert rev6["rating"] == 1.0

    # Negations preserved
    assert "didn't" in rev5["cleaned_text"].lower()
    assert "never" in rev6["cleaned_text"].lower()
    assert "not" in rev6["cleaned_text"].lower()

