"""Unit tests for Database Configuration and Data Quality Validation Gate."""

from pathlib import Path
import pytest
import pandas as pd

from src.database.connection import mask_database_url, normalize_database_url
from src.database.data_quality import (
    DataQualityGate,
    validate_data_quality,
)


@pytest.fixture
def valid_multi_product_df() -> pd.DataFrame:
    """Fixture providing a valid DataFrame with multiple products and valid metadata."""
    return pd.DataFrame({
        "review_id": ["REV_001", "REV_002", "REV_003"],
        "review_text": [
            "Battery lasts all day, very impressed!",
            "Customer support took two weeks to answer my ticket.",
            "Great display and reliable performance.",
        ],
        "cleaned_text": [
            "Battery lasts all day, very impressed!",
            "Customer support took two weeks to answer my ticket.",
            "Great display and reliable performance.",
        ],
        "rating": [5.0, 2.0, 4.0],
        "review_date": ["2023-01-15", "2023-01-16", "2023-01-17"],
        "product_id": ["PROD_101", "PROD_202", "PROD_101"],
        "product_name": ["Kindle Paperwhite", "Echo Dot", "Kindle Paperwhite"],
        "category": ["E-Readers", "Smart Speakers", "E-Readers"],
        "campaign": ["Holiday_2023", "Holiday_2023", "Spring_2024"],
        "source": ["Amazon", "Website", "Amazon"],
        "sentiment": ["positive", "negative", "positive"],
        "topics": ["battery", "customer_support", "performance"],
    })


# ==============================================================================
# 1. Database Configuration Tests (URL parsing, driver normalization, credential masking)
# ==============================================================================

def test_database_url_normalization():
    """Verify driver normalization from postgresql:// to postgresql+psycopg2://."""
    url1 = "postgresql://user:pass@localhost:5432/test_db"
    assert normalize_database_url(url1) == "postgresql+psycopg2://user:pass@localhost:5432/test_db"

    url2 = "postgres://user:pass@localhost:5432/test_db"
    assert normalize_database_url(url2) == "postgresql+psycopg2://user:pass@localhost:5432/test_db"

    url3 = "postgresql+psycopg2://user:pass@aws-0.pooler.supabase.com:6543/postgres?sslmode=require"
    assert normalize_database_url(url3) == url3

    url4 = "sqlite:///:memory:"
    assert normalize_database_url(url4) == "sqlite:///:memory:"


def test_database_credential_masking():
    """Verify passwords are completely hidden in masked connection strings."""
    secret = "TopSecretSupabasePassword123"
    raw_url = f"postgresql+psycopg2://postgres.{'myproject'}:{secret}@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require"

    masked = mask_database_url(raw_url)
    assert secret not in masked
    assert "***" in masked
    assert "aws-0-us-east-1.pooler.supabase.com" in masked
    assert "postgres" in masked
    assert "sslmode=require" in masked


# ==============================================================================
# 2. Data Quality Gate: Valid Data (Passes)
# ==============================================================================

def test_data_quality_gate_valid_data(valid_multi_product_df: pd.DataFrame):
    """Verify that a compliant dataset with multi-product reviews passes validation."""
    gate = DataQualityGate()
    report = gate.validate(valid_multi_product_df, dataset_name="multi_prod_test")

    assert report["quality_status"] == "PASSED"
    assert report["row_count"] == 3
    assert report["unique_reviews"] == 3
    assert report["unique_products"] == 2
    assert report["invalid_values"] == {}
    assert len(report["limitations"]) == 0


# ==============================================================================
# 3. Data Quality Gate: Invalid Product Count (Flags Warning & Limitation)
# ==============================================================================

def test_data_quality_gate_single_product_limitation(valid_multi_product_df: pd.DataFrame):
    """Verify that single-product datasets trigger WARNING status and explicit limitation."""
    df = valid_multi_product_df.copy()
    df["product_id"] = "unknown"

    gate = DataQualityGate()
    report = gate.validate(df, dataset_name="single_prod_test")

    assert report["quality_status"] == "WARNING"
    assert report["unique_products"] == 1
    assert any("Product-level comparison requires ingesting multi-product review data" in lim for lim in report["limitations"])


# ==============================================================================
# 4. Data Quality Gate: Invalid Sentiment Values (Fails)
# ==============================================================================

def test_data_quality_gate_invalid_sentiment(valid_multi_product_df: pd.DataFrame):
    """Verify that unexpected sentiment values trigger FAILED status."""
    df = valid_multi_product_df.copy()
    df.loc[0, "sentiment"] = "super_happy"

    gate = DataQualityGate()
    report = gate.validate(df)

    assert report["quality_status"] == "FAILED"
    assert "invalid_sentiment_count" in report["invalid_values"]
    assert report["invalid_values"]["invalid_sentiment_count"] == 1


# ==============================================================================
# 5. Data Quality Gate: Invalid Rating Values (Fails)
# ==============================================================================

def test_data_quality_gate_invalid_rating(valid_multi_product_df: pd.DataFrame):
    """Verify that out-of-range ratings (< 1.0 or > 5.0) trigger FAILED status."""
    df = valid_multi_product_df.copy()
    df.loc[1, "rating"] = 6.5

    gate = DataQualityGate()
    report = gate.validate(df)

    assert report["quality_status"] == "FAILED"
    assert "invalid_rating_count" in report["invalid_values"]
    assert report["invalid_values"]["invalid_rating_count"] == 1


# ==============================================================================
# 6. Data Quality Gate: Missing Required Analytical Fields (Fails)
# ==============================================================================

def test_data_quality_gate_missing_required_analytical_field(valid_multi_product_df: pd.DataFrame):
    """Verify that dropping a required analytical column triggers FAILED status."""
    df = valid_multi_product_df.drop(columns=["sentiment"])

    gate = DataQualityGate()
    report = gate.validate(df)

    assert report["quality_status"] == "FAILED"
    assert "missing_required_fields" in report["invalid_values"]
    assert "sentiment" in report["invalid_values"]["missing_required_fields"]


def test_data_quality_gate_null_in_required_id(valid_multi_product_df: pd.DataFrame):
    """Verify that unexpected nulls in review_id trigger FAILED status."""
    df = valid_multi_product_df.copy()
    df.loc[0, "review_id"] = None

    gate = DataQualityGate()
    report = gate.validate(df)

    assert report["quality_status"] == "FAILED"
    assert "null_review_id_count" in report["invalid_values"]


def test_data_quality_gate_file_export(valid_multi_product_df: pd.DataFrame, tmp_path: Path):
    """Verify export of data quality report to JSON on disk."""
    json_path = tmp_path / "test_report.json"
    report = validate_data_quality(valid_multi_product_df, output_report_path=json_path)

    assert json_path.is_file()
    assert report["quality_status"] == "PASSED"
