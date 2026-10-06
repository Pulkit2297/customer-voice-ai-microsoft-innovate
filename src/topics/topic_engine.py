"""Topic detection engine for CustomerVoice AI.

Implements a taxonomy-driven, rule-based multi-topic classifier capable of assigning
one or multiple product/service topics to unstructured customer reviews.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import pandas as pd
import yaml

logger = logging.getLogger(__name__)

# Path to the default taxonomy definition
DEFAULT_TAXONOMY_PATH = Path(__file__).resolve().parent / "taxonomy.yaml"


@dataclass(frozen=True)
class TopicResult:
    """Standardized result of topic classification."""

    topics: List[str]  # All matched topics
    topic_confidence: Dict[str, float]  # Per-topic confidence scores [0.0, 1.0]
    primary_topic: Optional[str]  # Highest confidence topic (or None if none matched)


class TopicClassifier:
    """Multi-topic classifier based on a controlled, domain-specific taxonomy."""

    def __init__(self, taxonomy_path: Optional[Union[str, Path]] = None):
        """Load taxonomy rules and compile keyword matching patterns.

        Args:
            taxonomy_path: Optional path to YAML taxonomy file. Defaults to taxonomy.yaml.
        """
        self.taxonomy_path = Path(taxonomy_path or DEFAULT_TAXONOMY_PATH).resolve()
        self.taxonomy: Dict[str, Dict[str, Any]] = self._load_taxonomy()
        self._compiled_patterns: Dict[str, List[re.Pattern]] = self._compile_patterns()

    def _load_taxonomy(self) -> Dict[str, Dict[str, Any]]:
        """Read and validate the YAML taxonomy definition."""
        if not self.taxonomy_path.is_file():
            raise FileNotFoundError(f"Taxonomy file not found at: {self.taxonomy_path}")

        with open(self.taxonomy_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "taxonomy" not in data:
            raise ValueError(f"Invalid taxonomy structure in {self.taxonomy_path}")

        return data["taxonomy"]

    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Pre-compile regex word-boundary patterns for each keyword in taxonomy."""
        compiled: Dict[str, List[re.Pattern]] = {}
        for topic, details in self.taxonomy.items():
            keywords = details.get("keywords", [])
            # Sort keywords by length descending so multi-word phrases match cleanly
            sorted_keywords = sorted(keywords, key=len, reverse=True)
            patterns = []
            for kw in sorted_keywords:
                # Use word boundaries around escaped keyword
                pattern = re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
                patterns.append(pattern)
            compiled[topic] = patterns
        return compiled

    def get_supported_topics(self) -> List[str]:
        """Return list of all registered topic keys in the taxonomy."""
        return list(self.taxonomy.keys())

    def predict(self, text: Any) -> TopicResult:
        """Assign one or more topics to the input review text.

        Args:
            text: Customer review text.

        Returns:
            TopicResult containing:
            - topics (List[str]): List of detected topics.
            - topic_confidence (Dict[str, float]): Confidence scores per topic.
            - primary_topic (Optional[str]): Topic with highest confidence, or None.
        """
        if text is None or pd.isna(text) or str(text).strip() == "":
            return TopicResult(topics=[], topic_confidence={}, primary_topic=None)

        text_str = str(text)
        detected_scores: Dict[str, float] = {}

        for topic, patterns in self._compiled_patterns.items():
            match_count = 0
            for pattern in patterns:
                matches = pattern.findall(text_str)
                match_count += len(matches)

            if match_count > 0:
                # Confidence scales with match occurrences: 1 match -> 0.75, 2 -> 0.85, 3+ -> 0.95+
                confidence = min(1.0, round(0.65 + 0.10 * match_count, 4))
                detected_scores[topic] = confidence

        if not detected_scores:
            return TopicResult(topics=[], topic_confidence={}, primary_topic=None)

        # Sort topics by confidence descending, then alphabetically for deterministic order
        sorted_topics = sorted(
            detected_scores.keys(),
            key=lambda t: (-detected_scores[t], t),
        )

        primary_topic = sorted_topics[0]

        return TopicResult(
            topics=sorted_topics,
            topic_confidence=detected_scores,
            primary_topic=primary_topic,
        )

    def predict_batch(self, texts: List[Any]) -> List[TopicResult]:
        """Batch predict topics across a sequence of texts."""
        return [self.predict(t) for t in texts]


def add_topics_to_dataframe(
    df: pd.DataFrame,
    text_column: str = "cleaned_text",
    classifier: Optional[TopicClassifier] = None,
) -> pd.DataFrame:
    """Enrich a reviews DataFrame with topic detection columns.

    Preserves all existing columns without deletion or modification.

    Args:
        df: Input DataFrame with customer feedback.
        text_column: Text column to classify.
        classifier: Initialized TopicClassifier instance (or None for default).

    Returns:
        New DataFrame containing all original columns plus:
        - topics (str): Comma-separated list of detected topics.
        - topic_confidence (str): JSON string mapping detected topics to confidence.
        - primary_topic (str): Primary topic or None if no topic detected.
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

    clf = classifier or TopicClassifier()
    results = clf.predict_batch(enriched_df[target_col].tolist())

    enriched_df["topics"] = [",".join(r.topics) if r.topics else "" for r in results]
    enriched_df["topic_confidence"] = [
        json.dumps(r.topic_confidence) if r.topic_confidence else "{}" for r in results
    ]
    enriched_df["primary_topic"] = [r.primary_topic for r in results]

    return enriched_df
