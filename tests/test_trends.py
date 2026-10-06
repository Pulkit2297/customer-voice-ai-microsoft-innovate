"""Unit tests for Phase 8: Trend and Anomaly Detection."""

import numpy as np
import pandas as pd
import pytest

from src.trends.trend_detector import (
    AnomalyResult,
    TrendDetector,
    calculate_percentage_change,
    detect_series_anomalies,
)


# -----------------------------------------------------------------------------
# Percentage Change Tests
# -----------------------------------------------------------------------------


def test_calculate_percentage_change_standard():
    """Verify standard positive and negative rate-of-change computations."""
    assert calculate_percentage_change(100.0, 150.0) == 50.0
    assert calculate_percentage_change(50.0, 25.0) == -50.0
    assert calculate_percentage_change(10.0, 10.0) == 0.0


def test_calculate_percentage_change_zero_boundary():
    """Verify safe handling of zero denominators without division errors."""
    assert calculate_percentage_change(0.0, 0.0) == 0.0
    assert calculate_percentage_change(0.0, 20.0) == 100.0
    assert calculate_percentage_change(0.0, -10.0) == -100.0


# -----------------------------------------------------------------------------
# Statistical Anomaly Detection Tests
# -----------------------------------------------------------------------------


def test_detect_series_anomalies_normal_distribution():
    """Verify that stable time series with minor fluctuations do not trigger anomalies."""
    dates = pd.date_range("2023-01-01", periods=6, freq="W")
    stable_series = pd.Series([20, 21, 19, 20, 22, 20], index=dates)

    anomalies = detect_series_anomalies(
        stable_series,
        metric_name="review_volume",
        z_threshold=2.0,
        pct_change_threshold=50.0,
    )

    assert len(anomalies) == 5  # 5 interval comparisons
    for anom in anomalies:
        assert isinstance(anom, AnomalyResult)
        assert anom.is_anomaly is False
        assert anom.anomaly_score < 2.0


def test_detect_series_anomalies_spike_detection():
    """Verify that a sudden 5x volume spike is detected as an anomaly."""
    dates = pd.date_range("2023-01-01", periods=6, freq="W")
    spike_series = pd.Series([10, 10, 12, 11, 80, 12], index=dates)

    anomalies = detect_series_anomalies(
        spike_series,
        metric_name="review_volume",
        z_threshold=2.0,
        pct_change_threshold=50.0,
    )

    # Interval from index 3 (11) to index 4 (80) should be an anomaly
    spike_anomaly = [a for a in anomalies if a.detected_at == str(dates[4])]
    assert len(spike_anomaly) == 1
    assert spike_anomaly[0].is_anomaly is True
    assert spike_anomaly[0].previous_value == 11.0
    assert spike_anomaly[0].current_value == 80.0
    assert spike_anomaly[0].percentage_change > 500.0
    assert spike_anomaly[0].metric == "review_volume"


def test_anomaly_result_schema_fields():
    """Verify that AnomalyResult strictly populates all required schema fields."""
    anom = AnomalyResult(
        metric="negative_sentiment_pct",
        topic="battery",
        product="PROD_1",
        previous_value=12.5,
        current_value=45.0,
        percentage_change=260.0,
        anomaly_score=2.85,
        is_anomaly=True,
        detected_at="2023-W05",
    )
    d = anom.to_dict()
    assert d["metric"] == "negative_sentiment_pct"
    assert d["topic"] == "battery"
    assert d["product"] == "PROD_1"
    assert d["previous_value"] == 12.5
    assert d["current_value"] == 45.0
    assert d["percentage_change"] == 260.0
    assert d["anomaly_score"] == 2.85
    assert d["is_anomaly"] is True
    assert d["detected_at"] == "2023-W05"


# -----------------------------------------------------------------------------
# TrendDetector Aggregation Tests
# -----------------------------------------------------------------------------


@pytest.fixture
def dated_reviews_df() -> pd.DataFrame:
    """Fixture providing dated reviews across multiple weeks and topics."""
    return pd.DataFrame([
        # Week 1
        {"review_date": "2023-01-02", "sentiment": "positive", "topics": "battery", "product_id": "P1", "product_name": "Kindle"},
        {"review_date": "2023-01-03", "sentiment": "positive", "topics": "battery", "product_id": "P1", "product_name": "Kindle"},
        # Week 2
        {"review_date": "2023-01-09", "sentiment": "negative", "topics": "battery", "product_id": "P1", "product_name": "Kindle"},
        {"review_date": "2023-01-10", "sentiment": "negative", "topics": "delivery", "product_id": "P2", "product_name": "Echo"},
        {"review_date": "2023-01-11", "sentiment": "negative", "topics": "battery,delivery", "product_id": "P1", "product_name": "Kindle"},
        # Week 3
        {"review_date": "2023-01-16", "sentiment": "positive", "topics": "features", "product_id": "P2", "product_name": "Echo"},
        {"review_date": "2023-01-17", "sentiment": "neutral", "topics": "pricing", "product_id": "P1", "product_name": "Kindle"},
    ])


def test_calculate_review_volume_over_time(dated_reviews_df: pd.DataFrame):
    """Verify weekly review volume aggregation."""
    detector = TrendDetector()
    vol = detector.calculate_review_volume_over_time(dated_reviews_df, freq="W")

    assert len(vol) >= 3
    assert "period" in vol.columns
    assert "review_volume" in vol.columns
    assert "percentage_change" in vol.columns


def test_calculate_sentiment_over_time(dated_reviews_df: pd.DataFrame):
    """Verify temporal sentiment aggregation."""
    detector = TrendDetector()
    sent = detector.calculate_sentiment_over_time(dated_reviews_df, freq="W")

    assert len(sent) >= 3
    assert "positive" in sent.columns
    assert "negative" in sent.columns
    assert "negative_sentiment_pct" in sent.columns


def test_calculate_negative_sentiment_by_topic(dated_reviews_df: pd.DataFrame):
    """Verify negative sentiment percentage calculation by topic."""
    detector = TrendDetector()
    topic_agg = detector.calculate_negative_sentiment_by_topic(dated_reviews_df)

    assert "topic" in topic_agg.columns
    assert "negative_sentiment_pct" in topic_agg.columns
    battery_row = topic_agg[topic_agg["topic"] == "battery"].iloc[0]
    # Total battery reviews = 4 (2 positive, 2 negative) -> 50.0%
    assert battery_row["total_reviews"] == 4
    assert battery_row["negative_reviews"] == 2
    assert battery_row["negative_sentiment_pct"] == 50.0



def test_calculate_negative_sentiment_by_product(dated_reviews_df: pd.DataFrame):
    """Verify negative sentiment percentage calculation by product."""
    detector = TrendDetector()
    prod_agg = detector.calculate_negative_sentiment_by_product(dated_reviews_df)

    assert "product_id" in prod_agg.columns
    assert "negative_sentiment_pct" in prod_agg.columns
    assert len(prod_agg) == 2
