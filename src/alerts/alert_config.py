"""Alert threshold configuration for CustomerVoice AI.

Defines configurable alert parameters with initial defaults.
Enables runtime or environment variable overrides without hardcoding in business logic.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AlertThresholds:
    """Configurable alert threshold parameters."""

    # Default thresholds specified in requirements
    negative_sentiment_increase_pct: float = float(
        os.getenv("ALERT_NEGATIVE_SENTIMENT_INCREASE_PCT", "20.0")
    )
    topic_volume_increase_pct: float = float(
        os.getenv("ALERT_TOPIC_VOLUME_INCREASE_PCT", "30.0")
    )
    rating_decrease_absolute: float = float(
        os.getenv("ALERT_RATING_DECREASE_ABSOLUTE", "0.5")
    )
    model_f1_decrease_absolute: float = float(
        os.getenv("ALERT_MODEL_F1_DECREASE_ABSOLUTE", "0.10")
    )

    # Escalated / High Severity thresholds
    high_negative_sentiment_increase_pct: float = float(
        os.getenv("ALERT_HIGH_NEGATIVE_SENTIMENT_PCT", "40.0")
    )
    high_topic_volume_increase_pct: float = float(
        os.getenv("ALERT_HIGH_TOPIC_VOLUME_PCT", "50.0")
    )
    high_rating_decrease_absolute: float = float(
        os.getenv("ALERT_HIGH_RATING_DECREASE", "1.0")
    )
    high_model_f1_decrease_absolute: float = float(
        os.getenv("ALERT_HIGH_MODEL_F1_DECREASE", "0.20")
    )


# Singleton default configuration
default_thresholds = AlertThresholds()
