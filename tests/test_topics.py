"""Unit tests for Phase 5: Controlled Taxonomy Topic Detection."""

import pandas as pd
import pytest

from src.topics.topic_engine import (
    TopicClassifier,
    TopicResult,
    add_topics_to_dataframe,
)


@pytest.fixture
def classifier() -> TopicClassifier:
    """Fixture providing initialized TopicClassifier."""
    return TopicClassifier()


def test_taxonomy_loading(classifier: TopicClassifier):
    """Verify that taxonomy loads all 12 initial product/customer topics."""
    expected_topics = {
        "product_quality",
        "battery",
        "performance",
        "delivery",
        "customer_support",
        "pricing",
        "refund",
        "return",
        "packaging",
        "usability",
        "features",
        "reliability",
    }
    supported = set(classifier.get_supported_topics())
    assert expected_topics.issubset(supported)


def test_single_topic(classifier: TopicClassifier):
    """Verify detection when only one topic is referenced."""
    text = "The courier took two weeks for delivery, package arrived late."
    result = classifier.predict(text)

    assert isinstance(result, TopicResult)
    assert "delivery" in result.topics
    assert result.primary_topic == "delivery"
    assert result.topic_confidence["delivery"] >= 0.70


def test_multiple_topics_prompt_example(classifier: TopicClassifier):
    """Verify detection on the multi-topic example specified in the prompt:

    Input: "The battery is terrible and customer support never replied."
    Expected topics: 'battery' and 'customer_support'.
    """
    text = "The battery is terrible and customer support never replied."
    result = classifier.predict(text)

    assert "battery" in result.topics
    assert "customer_support" in result.topics
    assert len(result.topics) >= 2
    assert result.primary_topic in {"battery", "customer_support"}
    assert "battery" in result.topic_confidence
    assert "customer_support" in result.topic_confidence


def test_no_detected_topic(classifier: TopicClassifier):
    """Verify that generic feedback without topic keywords returns empty topic list."""
    text = "Just a general comment about things in life today."
    result = classifier.predict(text)

    assert result.topics == []
    assert result.topic_confidence == {}
    assert result.primary_topic is None


def test_empty_review(classifier: TopicClassifier):
    """Verify that empty, whitespace, and None reviews handle cleanly."""
    for empty_input in [None, "", "   ", "\n\t"]:
        result = classifier.predict(empty_input)
        assert result.topics == []
        assert result.topic_confidence == {}
        assert result.primary_topic is None


def test_additional_multi_topic(classifier: TopicClassifier):
    """Verify multiple topics across pricing, refund, and packaging."""
    text = "The price was expensive, the packaging was completely crushed, and I asked for a refund."
    result = classifier.predict(text)

    assert "pricing" in result.topics
    assert "packaging" in result.topics
    assert "refund" in result.topics
    assert len(result.topics) == 3


def test_add_topics_to_dataframe_preserves_columns(classifier: TopicClassifier):
    """Verify DataFrame enrichment adds topic columns while preserving all existing columns."""
    df = pd.DataFrame([
        {
            "review_id": "REV_001",
            "cleaned_text": "The battery is terrible and customer support never replied.",
            "sentiment": "negative",
            "sentiment_score": -0.65,
        },
        {
            "review_id": "REV_002",
            "cleaned_text": "Random text without keywords.",
            "sentiment": "neutral",
            "sentiment_score": 0.0,
        },
    ])
    original_columns = list(df.columns)

    enriched = add_topics_to_dataframe(df, classifier=classifier)

    # Check all original columns preserved
    for col in original_columns:
        assert col in enriched.columns

    # Check new topic columns added
    assert "topics" in enriched.columns
    assert "topic_confidence" in enriched.columns
    assert "primary_topic" in enriched.columns

    # Verify values
    assert "battery" in enriched.loc[0, "topics"]
    assert "customer_support" in enriched.loc[0, "topics"]
    assert enriched.loc[1, "topics"] == ""
    assert pd.isna(enriched.loc[1, "primary_topic"])


