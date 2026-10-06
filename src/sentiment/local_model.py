"""Local baseline sentiment analysis model implementation for CustomerVoice AI.

Implements BaseSentimentEngine using VADER (Valence Aware Dictionary and sEntiment Reasoner),
an open-source, deterministic, rule-based model tuned for customer feedback and social text.
"""

from typing import Any, List, Optional
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from src.sentiment.sentiment_engine import BaseSentimentEngine, SentimentResult


class LocalSentimentModel(BaseSentimentEngine):
    """Local sentiment analysis baseline engine using VADER."""

    def __init__(
        self,
        pos_threshold: float = 0.05,
        neg_threshold: float = -0.05,
    ):
        """Initialize the local sentiment engine.

        Args:
            pos_threshold: Compound polarity threshold for 'positive' classification.
            neg_threshold: Compound polarity threshold for 'negative' classification.
        """
        self._pos_threshold = pos_threshold
        self._neg_threshold = neg_threshold
        self._analyzer = SentimentIntensityAnalyzer()
        self._model_name = "VADER-Baseline"
        self._model_version = "3.3.2"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_version(self) -> str:
        return self._model_version

    def predict(self, text: Any) -> SentimentResult:
        """Analyze sentiment for a single text instance deterministically.

        Args:
            text: Customer review text.

        Returns:
            SentimentResult with sentiment ('positive', 'neutral', 'negative'),
            sentiment_score, confidence, model_name, and model_version.
        """
        # Handle missing, null, or empty string inputs
        if text is None or pd.isna(text) or str(text).strip() == "":
            return SentimentResult(
                sentiment="neutral",
                sentiment_score=0.0,
                confidence=0.0,
                model_name=self.model_name,
                model_version=self.model_version,
            )

        text_str = str(text)
        scores = self._analyzer.polarity_scores(text_str)
        compound = round(float(scores["compound"]), 4)

        # Classify sentiment label based on compound score
        if compound >= self._pos_threshold:
            sentiment = "positive"
            # Confidence proportional to positive polarity strength
            confidence = round(max(0.0, min(1.0, abs(compound))), 4)
        elif compound <= self._neg_threshold:
            sentiment = "negative"
            # Confidence proportional to negative polarity strength
            confidence = round(max(0.0, min(1.0, abs(compound))), 4)
        else:
            sentiment = "neutral"
            confidence = round(max(0.0, min(1.0, float(scores["neu"]))), 4)

        return SentimentResult(
            sentiment=sentiment,
            sentiment_score=compound,
            confidence=confidence,
            model_name=self.model_name,
            model_version=self.model_version,
        )

    def predict_batch(
        self,
        texts: List[Any],
        batch_size: int = 100,
    ) -> List[SentimentResult]:
        """Perform batch prediction over a list of texts.

        Args:
            texts: List of review texts.
            batch_size: Batch size for processing chunked data.

        Returns:
            List of SentimentResult objects.
        """
        results: List[SentimentResult] = []
        total = len(texts)

        for i in range(0, total, batch_size):
            chunk = texts[i : i + batch_size]
            for item in chunk:
                results.append(self.predict(item))

        return results


def add_sentiment_to_dataframe(
    df: pd.DataFrame,
    text_column: str = "cleaned_text",
    model: Optional[BaseSentimentEngine] = None,
    batch_size: int = 100,
) -> pd.DataFrame:
    """Enrich a reviews DataFrame with sentiment analysis baseline columns.

    Args:
        df: Input DataFrame containing customer feedback.
        text_column: Column name to run sentiment inference on.
        model: Sentiment engine instance (defaults to LocalSentimentModel).
        batch_size: Chunk size for batch evaluation.

    Returns:
        A new DataFrame enriched with sentiment columns.
    """
    if df is None or len(df) == 0:
        return pd.DataFrame() if df is None else df.copy()

    enriched_df = df.copy(deep=True)

    if text_column not in enriched_df.columns:
        if "review_text" in enriched_df.columns:
            target_col = "review_text"
        else:
            raise ValueError(
                f"Neither '{text_column}' nor 'review_text' found in DataFrame."
            )
    else:
        target_col = text_column

    engine = model or LocalSentimentModel()
    predictions = engine.predict_batch(
        enriched_df[target_col].tolist(),
        batch_size=batch_size,
    )

    enriched_df["sentiment"] = [p.sentiment for p in predictions]
    enriched_df["sentiment_score"] = [p.sentiment_score for p in predictions]
    enriched_df["confidence"] = [p.confidence for p in predictions]
    enriched_df["model_name"] = [p.model_name for p in predictions]
    enriched_df["model_version"] = [p.model_version for p in predictions]

    return enriched_df
