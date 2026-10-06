"""Sentiment analysis base interface for CustomerVoice AI.

Provides an abstract interface (BaseSentimentEngine) and standardized schema
(SentimentResult) allowing models (local baseline, Azure AI Language, etc.)
to be swapped seamlessly without modifying downstream pipelines.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Set, Union
import pandas as pd

ALLOWED_SENTIMENTS: Set[str] = {"positive", "neutral", "negative"}


@dataclass(frozen=True)
class SentimentResult:
    """Standardized output structure for sentiment predictions."""

    sentiment: str  # 'positive', 'neutral', or 'negative'
    sentiment_score: float  # continuous sentiment score [-1.0, 1.0]
    confidence: float  # model confidence score [0.0, 1.0]
    model_name: str  # identifier of the generating model
    model_version: str  # version tag of the generating model

    def __post_init__(self):
        if self.sentiment not in ALLOWED_SENTIMENTS:
            raise ValueError(
                f"Invalid sentiment '{self.sentiment}'. Allowed values: {ALLOWED_SENTIMENTS}"
            )
        if not (-1.0 <= self.sentiment_score <= 1.0):
            raise ValueError(
                f"sentiment_score must be between -1.0 and 1.0, got: {self.sentiment_score}"
            )
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"confidence must be between 0.0 and 1.0, got: {self.confidence}"
            )


class BaseSentimentEngine(ABC):
    """Abstract base class for all sentiment analysis providers.

    Enables plug-and-play architecture for Local models, Azure AI Language,
    or transformer backends.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the sentiment model provider."""
        pass

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Version of the underlying model."""
        pass

    @abstractmethod
    def predict(self, text: Any) -> SentimentResult:
        """Analyze sentiment for a single text instance.

        Args:
            text: Unstructured review text.

        Returns:
            Standardized SentimentResult object.
        """
        pass

    def predict_batch(self, texts: List[Any]) -> List[SentimentResult]:
        """Analyze sentiment for a batch of text instances.

        Default implementation executes sequential predictions.
        Subclasses can override for vector-accelerated or API batch requests.

        Args:
            texts: List of review texts.

        Returns:
            List of SentimentResult objects.
        """
        return [self.predict(t) for t in texts]
