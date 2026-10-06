"""Unit tests for Phase 4: Sentiment analysis baseline."""

import pandas as pd
import pytest

from src.sentiment.local_model import LocalSentimentModel, add_sentiment_to_dataframe
from src.sentiment.sentiment_engine import ALLOWED_SENTIMENTS, SentimentResult


@pytest.fixture
def sentiment_model() -> LocalSentimentModel:
    """Fixture providing initialized LocalSentimentModel."""
    return LocalSentimentModel()


def test_valid_sentiment_output(sentiment_model: LocalSentimentModel):
    """Verify that model returns a valid SentimentResult object with required attributes."""
    text = "The screen clarity is amazing and the battery life lasts for days!"
    result = sentiment_model.predict(text)

    assert isinstance(result, SentimentResult)
    assert hasattr(result, "sentiment")
    assert hasattr(result, "sentiment_score")
    assert hasattr(result, "confidence")
    assert hasattr(result, "model_name")
    assert hasattr(result, "model_version")

    assert result.sentiment == "positive"
    assert result.model_name == "VADER-Baseline"
    assert result.model_version == "3.3.2"


def test_valid_sentiment_labels(sentiment_model: LocalSentimentModel):
    """Verify that predictions only yield labels from ALLOWED_SENTIMENTS."""
    sample_texts = [
        ("I absolutely love this product, it works brilliantly!", "positive"),
        ("The device broke on day two, completely useless garbage.", "negative"),
        ("The package contains one cable and two connectors.", "neutral"),
    ]

    for text, expected_label in sample_texts:
        result = sentiment_model.predict(text)
        assert result.sentiment in ALLOWED_SENTIMENTS
        assert result.sentiment == expected_label


def test_score_range(sentiment_model: LocalSentimentModel):
    """Verify that sentiment_score is in [-1.0, 1.0] and confidence is in [0.0, 1.0]."""
    test_cases = [
        "Highly recommended, flawless experience!",
        "Disastrous failure, worst purchase ever made.",
        "The package arrived on Tuesday.",
        "It is okay, not good not terrible.",
    ]

    for text in test_cases:
        res = sentiment_model.predict(text)
        assert -1.0 <= res.sentiment_score <= 1.0, f"Score {res.sentiment_score} out of bounds"
        assert 0.0 <= res.confidence <= 1.0, f"Confidence {res.confidence} out of bounds"


def test_missing_text_handling(sentiment_model: LocalSentimentModel):
    """Verify that empty string, None, and whitespace return neutral with safe defaults."""
    empty_cases = [None, "", "   ", "\t\n"]

    for text in empty_cases:
        res = sentiment_model.predict(text)
        assert res.sentiment == "neutral"
        assert res.sentiment_score == 0.0
        assert res.confidence == 0.0
        assert res.sentiment in ALLOWED_SENTIMENTS


def test_deterministic_output(sentiment_model: LocalSentimentModel):
    """Verify that the model yields identical results given the exact same input."""
    text = "The customer support team resolved my issue within five minutes!"

    res1 = sentiment_model.predict(text)
    res2 = sentiment_model.predict(text)

    assert res1.sentiment == res2.sentiment
    assert res1.sentiment_score == res2.sentiment_score
    assert res1.confidence == res2.confidence


def test_batch_prediction_consistency(sentiment_model: LocalSentimentModel):
    """Verify batch predictions yield identical results to individual predictions."""
    texts = [
        "Great audio quality and compact design.",
        "Terrible customer service experience.",
        "The color is matte black.",
    ]

    batch_results = sentiment_model.predict_batch(texts, batch_size=2)
    single_results = [sentiment_model.predict(t) for t in texts]

    assert len(batch_results) == len(single_results)
    for b_res, s_res in zip(batch_results, single_results):
        assert b_res.sentiment == s_res.sentiment
        assert b_res.sentiment_score == s_res.sentiment_score
        assert b_res.confidence == s_res.confidence


def test_add_sentiment_to_dataframe(sentiment_model: LocalSentimentModel):
    """Verify DataFrame batch enrichment pipeline."""
    df = pd.DataFrame([
        {"review_id": "REV_01", "cleaned_text": "I really enjoy using this app every day!"},
        {"review_id": "REV_02", "cleaned_text": "Worst purchase, defective and noisy."},
    ])

    enriched = add_sentiment_to_dataframe(df, model=sentiment_model)

    assert "sentiment" in enriched.columns
    assert "sentiment_score" in enriched.columns
    assert "confidence" in enriched.columns
    assert "model_name" in enriched.columns
    assert "model_version" in enriched.columns

    assert enriched.loc[0, "sentiment"] == "positive"
    assert enriched.loc[1, "sentiment"] == "negative"
    assert len(enriched) == 2
