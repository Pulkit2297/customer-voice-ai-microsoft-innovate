"""Semantic integrity and data lineage verification tests.

Verifies that no business attributes (dates, ratings, campaigns, product SKUs)
are fabricated, that missing fields are strictly NULL, and that provenance
is maintained accurately across the CustomerVoice AI pipeline.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.alerts.alert_engine import AlertEngine
from src.ingestion.adapters.amazon_adapter import parse_fasttext_line
from src.ingestion.adapters.sentiment140_adapter import load_sentiment140_csv
from src.trends.trend_detector import TrendDetector

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# -----------------------------------------------------------------------------
# 1. No Synthetic Dates Test
# -----------------------------------------------------------------------------
def test_no_synthetic_dates_generated():
    """Verify that FastText parser sets review_date to None (no modulo offsets)."""
    raw_line = "__label__2 Fantastic gadget! Worked seamlessly out of the box."
    parsed = parse_fasttext_line(raw_line)

    assert parsed is not None
    assert parsed["review_date"] is None, "review_date must be None when absent in source"


# -----------------------------------------------------------------------------
# 2. No Inferred Ratings Stored as Real Ratings Test
# -----------------------------------------------------------------------------
def test_no_inferred_ratings_stored_as_real_ratings():
    """Verify that binary sentiment is not represented as an actual 1-5 customer rating."""
    raw_pos = "__label__2 Great product!"
    parsed_pos = parse_fasttext_line(raw_pos)

    assert parsed_pos is not None
    assert parsed_pos["rating"] is None, "Actual customer rating must be None"
    assert parsed_pos["rating_source"] == "not_available"
    assert parsed_pos["sentiment_proxy_rating"] == 5.0

    raw_neg = "__label__1 Terrible item."
    parsed_neg = parse_fasttext_line(raw_neg)
    assert parsed_neg is not None
    assert parsed_neg["rating"] is None
    assert parsed_neg["rating_source"] == "not_available"
    assert parsed_neg["sentiment_proxy_rating"] == 1.0


# -----------------------------------------------------------------------------
# 3. No Pseudo-Product IDs Test
# -----------------------------------------------------------------------------
def test_no_pseudo_product_ids():
    """Verify that product_id, product_name, and category are None (no pseudo-SKUs)."""
    raw_line = "__label__2 The battery life on this charger is amazing."
    parsed = parse_fasttext_line(raw_line)

    assert parsed is not None
    assert parsed["product_id"] is None, "product_id must be None"
    assert parsed["product_name"] is None, "product_name must be None"
    assert parsed["category"] is None, "category must be None"
    # Inferred topical grouping must be in segment, not product_id
    assert parsed["segment"] == "Power & Battery"


# -----------------------------------------------------------------------------
# 4. Sentiment140 Has No Product ID and No Segment Test
# -----------------------------------------------------------------------------
def test_sentiment140_has_no_product_or_segment(tmp_path):
    """Verify Sentiment140 tweets are treated as social channel, not products."""
    csv_file = tmp_path / "sample_tweet.csv"
    csv_file.write_text("sentence,sentiment\nloving the sunny afternoon,1\n")

    df = load_sentiment140_csv(csv_file, max_records=10)
    assert len(df) == 1
    record = df.iloc[0]

    assert pd.isna(record["product_id"]) or record["product_id"] is None
    assert pd.isna(record["product_name"]) or record["product_name"] is None
    assert pd.isna(record["category"]) or record["category"] is None
    assert pd.isna(record["segment"]) or record["segment"] is None
    assert record["source"] == "Twitter/Social"
    assert pd.isna(record["rating"]) or record["rating"] is None
    assert record["rating_source"] == "not_available"


# -----------------------------------------------------------------------------
# 5. No Placeholder Campaigns Test
# -----------------------------------------------------------------------------
def test_no_placeholder_campaigns():
    """Verify that campaign is None (no placeholder strings)."""
    raw_line = "__label__2 Loved it."
    parsed = parse_fasttext_line(raw_line)

    assert parsed is not None
    assert parsed["campaign"] is None, "campaign must be None"


# -----------------------------------------------------------------------------
# 6. Genuine Source Attribution Preserved Test
# -----------------------------------------------------------------------------
def test_genuine_source_attribution_preserved():
    """Verify authentic source channel identity is preserved."""
    raw_line = "__label__1 Defective cable."
    parsed = parse_fasttext_line(raw_line)
    assert parsed["source"] == "Amazon"


# -----------------------------------------------------------------------------
# 7. Trend Engine Gracefully Handles Missing Dates Test
# -----------------------------------------------------------------------------
def test_trend_engine_handles_missing_dates_without_crashing():
    """Verify trend detector reports insufficient_temporal_data when review_date is NULL."""
    df_no_dates = pd.DataFrame([
        {"review_date": None, "sentiment": "negative", "topics": "battery"},
        {"review_date": None, "sentiment": "positive", "topics": "battery"},
        {"review_date": np.nan, "sentiment": "negative", "topics": "pricing"},
    ])

    detector = TrendDetector()
    assert detector.has_temporal_data(df_no_dates) is False

    vol = detector.calculate_review_volume_over_time(df_no_dates)
    assert vol.empty
    assert vol.attrs.get("status") == "insufficient_temporal_data"

    sent = detector.calculate_sentiment_over_time(df_no_dates)
    assert sent.empty
    assert sent.attrs.get("status") == "insufficient_temporal_data"

    anomalies = detector.run_full_anomaly_detection(df_no_dates)
    assert anomalies == []


# -----------------------------------------------------------------------------
# 8. Alert Engine Demonstration Labeling Test
# -----------------------------------------------------------------------------
def test_alert_engine_demonstration_labeling():
    """Verify that demonstration alerts are explicitly marked."""
    engine = AlertEngine()

    demo_alert = engine.check_negative_sentiment_surge(
        previous_pct=10.0,
        current_pct=40.0,
        product="Demo_Product",
        topic="battery",
        is_demonstration=True,
    )

    assert demo_alert is not None
    assert demo_alert.alert_type == "DEMONSTRATION - NEGATIVE_SENTIMENT_SURGE"
    assert demo_alert.message.startswith("[Algorithmic Alert Demonstration]")

    # Check that insufficient_temporal_data skips temporal alerts in evaluate_all
    trends_insufficient = pd.DataFrame([
        {
            "metric": "review_volume",
            "topic": "all",
            "product": "all",
            "previous_value": 0.0,
            "current_value": 0.0,
            "percentage_change": 0.0,
            "anomaly_score": 0.0,
            "is_anomaly": False,
            "detected_at": "insufficient_temporal_data",
        }
    ])
    alerts = engine.evaluate_all(trends_df=trends_insufficient)
    assert alerts == [], "Temporal alerts must be skipped when status is insufficient_temporal_data"


# -----------------------------------------------------------------------------
# 9. Data Lineage Report Integrity Test
# -----------------------------------------------------------------------------
def test_data_lineage_report_verifications():
    """Verify that data_lineage_report.json accurately reflects 0 fabricated attributes."""
    report_file = PROJECT_ROOT / "data" / "processed" / "data_lineage_report.json"
    assert report_file.is_file(), "data_lineage_report.json must exist"

    with open(report_file, "r", encoding="utf-8") as f:
        report = json.load(f)

    checks = report.get("verification_checks", {})
    assert checks.get("products_are_actual_skus") is False
    assert checks.get("actual_product_count") == 0
    assert checks.get("genuine_date_count") == 0
    assert checks.get("genuine_rating_count") == 0
    assert checks.get("genuine_campaign_count") == 0
    assert checks.get("synthetic_values_introduced") is False
    assert report.get("audit_conclusion", {}).get("is_production_ready") is False
