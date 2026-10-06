"""Unit tests for Phase 7: Model Evaluation (Sentiment and Topics)."""

from pathlib import Path
import pandas as pd
import pytest

from src.evaluation.evaluate_sentiment import (
    SentimentEvaluationReport,
    evaluate_sentiment,
    evaluate_sentiment_datasets,
)
from src.evaluation.evaluate_topics import (
    TopicEvaluationReport,
    evaluate_topics,
    parse_topic_tokens,
    save_model_metrics,
)


def test_evaluate_sentiment_perfect_match():
    """Verify perfect predictions yield 1.0 accuracy and F1."""
    y_true = ["positive", "neutral", "negative", "positive"]
    y_pred = ["positive", "neutral", "negative", "positive"]

    report = evaluate_sentiment(y_true, y_pred)

    assert report.accuracy == 1.0
    assert report.macro_f1 == 1.0
    assert report.weighted_f1 == 1.0
    assert report.total_samples == 4
    assert len(report.confusion_matrix) == 3
    assert "precision" in report.per_class_metrics["positive"]


def test_evaluate_sentiment_with_errors():
    """Verify metrics computation with mixed predictions."""
    y_true = ["positive", "positive", "negative", "neutral"]
    y_pred = ["positive", "neutral", "negative", "negative"]

    report = evaluate_sentiment(y_true, y_pred)

    assert report.accuracy == 0.50
    assert 0.0 <= report.macro_f1 <= 1.0
    assert report.per_class_metrics["positive"]["precision"] == 1.0
    assert report.per_class_metrics["positive"]["recall"] == 0.5
    assert "positive" in report.classification_report_str


def test_evaluate_sentiment_length_mismatch():
    """Verify ValueError is raised when true and pred lengths differ."""
    with pytest.raises(ValueError):
        evaluate_sentiment(["positive"], ["positive", "negative"])


def test_parse_topic_tokens():
    """Verify parsing various string/list representations of topics."""
    assert parse_topic_tokens("battery, customer_support") == ["battery", "customer_support"]
    assert parse_topic_tokens(["pricing", "pricing", "delivery"]) == ["delivery", "pricing"]
    assert parse_topic_tokens("") == []
    assert parse_topic_tokens(None) == []


def test_evaluate_topics_perfect_match():
    """Verify multi-label topic evaluation on exact predictions."""
    y_true = ["battery,customer_support", "delivery", "pricing"]
    y_pred = ["customer_support,battery", "delivery", "pricing"]

    report = evaluate_topics(y_true, y_pred)

    assert report.exact_match_ratio == 1.0
    assert report.hamming_loss_score == 0.0
    assert report.micro_f1 == 1.0
    assert report.macro_f1 == 1.0
    assert "battery" in report.per_topic_metrics


def test_evaluate_topics_partial_mismatch():
    """Verify multi-label topic metrics with partial and incorrect topic labels."""
    y_true = ["battery,customer_support", "delivery", "refund"]
    y_pred = ["battery", "delivery,packaging", "refund"]

    report = evaluate_topics(y_true, y_pred)

    # 1 of 3 matched exactly ("refund")
    assert report.exact_match_ratio == pytest.approx(0.3333, abs=0.01)
    assert report.hamming_loss_score > 0.0
    assert 0.0 <= report.macro_f1 <= 1.0


def test_save_model_metrics(tmp_path: Path):
    """Verify saving metrics to CSV with timestamp and validation sample size."""
    out_file = tmp_path / "test_metrics.csv"
    records = [
        {"evaluation_type": "sentiment", "category": "overall", "metric_name": "accuracy", "metric_value": 0.85},
        {"evaluation_type": "topic", "category": "battery", "metric_name": "f1_score", "metric_value": 0.90},
    ]

    saved_path = save_model_metrics(records, output_path=out_file, sample_size=100)

    assert saved_path.is_file()
    df = pd.read_csv(saved_path)
    assert len(df) == 2
    assert "evaluation_timestamp" in df.columns
    assert df.loc[0, "validation_sample_size"] == 100
    assert df.loc[0, "metric_name"] == "accuracy"
