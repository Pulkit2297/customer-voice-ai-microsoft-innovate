"""Unit tests for Phase 6: Product and Campaign Attribution."""

import numpy as np
import pandas as pd
import pytest

from src.attribution.attributor import (
    UNKNOWN_VALUE,
    AttributionValidationError,
    ReviewAttributor,
    attribute_reviews_dataframe,
    normalize_metadata_value,
)


@pytest.fixture
def attributor() -> ReviewAttributor:
    return ReviewAttributor()


def test_normalize_metadata_value():
    """Verify metadata normalization strictly converts missing/blank to 'unknown'."""
    assert normalize_metadata_value(None) == UNKNOWN_VALUE
    assert normalize_metadata_value(np.nan) == UNKNOWN_VALUE
    assert normalize_metadata_value("") == UNKNOWN_VALUE
    assert normalize_metadata_value("   ") == UNKNOWN_VALUE
    assert normalize_metadata_value("nan") == UNKNOWN_VALUE
    assert normalize_metadata_value("N/A") == UNKNOWN_VALUE
    assert normalize_metadata_value("PROD_123") == "PROD_123"
    assert normalize_metadata_value("  Kindle Oasis  ") == "Kindle Oasis"


def test_fully_attributed_review(attributor: ReviewAttributor):
    """Verify review with complete product, category, and campaign metadata."""
    df = pd.DataFrame([{
        "review_id": "REV_001",
        "cleaned_text": "Great kindle battery!",
        "product_id": "PROD_KINDLE_01",
        "product_name": "Kindle Paperwhite",
        "category": "E-Readers",
        "campaign": "Holiday_Special_2023",
    }])

    result = attributor.attribute_dataframe(df)

    assert len(result) == 1
    assert result.loc[0, "product_id"] == "PROD_KINDLE_01"
    assert result.loc[0, "product_name"] == "Kindle Paperwhite"
    assert result.loc[0, "category"] == "E-Readers"
    assert result.loc[0, "campaign"] == "Holiday_Special_2023"
    assert result.loc[0, "product_attribution_status"] == "attributed"
    assert result.loc[0, "campaign_attribution_status"] == "attributed"
    assert result.loc[0, "attribution_status"] == "fully_attributed"


def test_missing_metadata_explicitly_unknown(attributor: ReviewAttributor):
    """Verify reviews with missing metadata are explicitly marked 'unknown' and never invented."""
    df = pd.DataFrame([{
        "review_id": "REV_002",
        "cleaned_text": "Customer service was helpful.",
        "product_id": None,
        "product_name": np.nan,
        "category": "",
        "campaign": "   ",
    }])

    result = attributor.attribute_dataframe(df)

    assert len(result) == 1
    assert result.loc[0, "product_id"] == UNKNOWN_VALUE
    assert result.loc[0, "product_name"] == UNKNOWN_VALUE
    assert result.loc[0, "category"] == UNKNOWN_VALUE
    assert result.loc[0, "campaign"] == UNKNOWN_VALUE
    assert result.loc[0, "product_attribution_status"] == "unattributed"
    assert result.loc[0, "campaign_attribution_status"] == "unattributed"
    assert result.loc[0, "attribution_status"] == "unattributed"


def test_partially_attributed_review(attributor: ReviewAttributor):
    """Verify review with product known but campaign unknown."""
    df = pd.DataFrame([{
        "review_id": "REV_003",
        "cleaned_text": "Fast performance.",
        "product_id": "PROD_99",
        "product_name": "Pro Tablet",
        "category": "Tablets",
        "campaign": None,
    }])

    result = attributor.attribute_dataframe(df)

    assert result.loc[0, "product_attribution_status"] == "attributed"
    assert result.loc[0, "campaign_attribution_status"] == "unattributed"
    assert result.loc[0, "attribution_status"] == "partially_attributed"
    assert result.loc[0, "campaign"] == UNKNOWN_VALUE


def test_no_data_silently_discarded(attributor: ReviewAttributor):
    """Verify that every row in input is preserved in output."""
    rows = [
        {"review_id": f"REV_{i:03d}", "cleaned_text": f"Review {i}"}
        for i in range(50)
    ]
    df = pd.DataFrame(rows)

    result = attributor.attribute_dataframe(df)

    assert len(result) == 50
    assert (result["product_attribution_status"] == "unattributed").all()
    # No NaNs anywhere in attribution columns
    for col in ["product_id", "product_name", "category", "campaign"]:
        assert result[col].isna().sum() == 0


def test_validation_checks_detect_mismatches(attributor: ReviewAttributor):
    """Verify validation check detects simulated row loss."""
    df = pd.DataFrame([
        {
            "review_id": "REV_01",
            "product_id": "unknown",
            "product_name": "unknown",
            "category": "unknown",
            "campaign": "unknown",
            "product_attribution_status": "unattributed",
            "campaign_attribution_status": "unattributed",
            "attribution_status": "unattributed",
        }
    ])

    # Expecting 2 rows but DataFrame only has 1
    with pytest.raises(AttributionValidationError) as exc_info:
        attributor.validate_attribution(df, expected_row_count=2)

    assert "Data loss detected" in str(exc_info.value)
