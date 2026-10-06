"""Unit tests for Phase 9: Alert Generation Engine."""

import pytest

from src.alerts.alert_config import AlertThresholds
from src.alerts.alert_engine import Alert, AlertEngine, AlertSeverity, AlertStatus


@pytest.fixture
def default_engine() -> AlertEngine:
    """Fixture providing AlertEngine with standard baseline thresholds."""
    return AlertEngine()


@pytest.fixture
def custom_engine() -> AlertEngine:
    """Fixture providing AlertEngine with customized overrides."""
    thresholds = AlertThresholds(
        negative_sentiment_increase_pct=15.0,
        topic_volume_increase_pct=25.0,
        rating_decrease_absolute=0.3,
        model_f1_decrease_absolute=0.05,
    )
    return AlertEngine(thresholds=thresholds)


def test_negative_sentiment_surge_triggers_alert(default_engine: AlertEngine):
    """Verify negative sentiment surge >= 20% triggers an alert."""
    # 20% to 45% -> delta is +25% (>= 20% threshold)
    alert = default_engine.check_negative_sentiment_surge(
        previous_pct=20.0,
        current_pct=45.0,
        product="Kindle",
        topic="battery",
    )

    assert alert is not None
    assert isinstance(alert, Alert)
    assert alert.alert_type == "NEGATIVE_SENTIMENT_SURGE"
    assert alert.severity in [AlertSeverity.MEDIUM.value, AlertSeverity.HIGH.value]
    assert alert.product == "Kindle"
    assert alert.topic == "battery"
    assert alert.metric == "negative_sentiment_pct"
    assert alert.previous_value == 20.0
    assert alert.current_value == 45.0
    assert alert.status == AlertStatus.ACTIVE.value
    assert "battery" in alert.message


def test_negative_sentiment_surge_below_threshold(default_engine: AlertEngine):
    """Verify small negative sentiment increases do not trigger alerts."""
    # 20% to 22% -> +2% delta (below 20% threshold)
    alert = default_engine.check_negative_sentiment_surge(
        previous_pct=20.0,
        current_pct=22.0,
    )
    assert alert is None


def test_topic_volume_surge(default_engine: AlertEngine):
    """Verify topic volume increase >= 30% triggers alert."""
    # 10 to 18 -> +80% increase
    alert = default_engine.check_topic_volume_surge(
        previous_volume=10.0,
        current_volume=18.0,
        topic="customer_support",
    )

    assert alert is not None
    assert alert.alert_type == "TOPIC_VOLUME_SURGE"
    assert alert.percentage_change == 80.0
    assert alert.topic == "customer_support"


def test_rating_drop_alert(default_engine: AlertEngine):
    """Verify average rating drop >= 0.5 triggers alert."""
    # 4.5 to 3.8 -> 0.7 drop (>= 0.5 threshold)
    alert = default_engine.check_rating_drop(
        previous_rating=4.5,
        current_rating=3.8,
        product="Echo_Dot",
    )

    assert alert is not None
    assert alert.alert_type == "RATING_DROP"
    assert alert.previous_value == 4.5
    assert alert.current_value == 3.8
    assert alert.severity in [AlertSeverity.MEDIUM.value, AlertSeverity.HIGH.value]
    assert alert.status == AlertStatus.ACTIVE.value


def test_model_f1_decay_alert(default_engine: AlertEngine):
    """Verify model F1 score drop >= 0.10 triggers alert."""
    # 0.88 to 0.75 -> 0.13 drop (>= 0.10 threshold)
    alert = default_engine.check_model_f1_decay(
        previous_f1=0.88,
        current_f1=0.75,
        model_name="VADER-Baseline",
    )

    assert alert is not None
    assert alert.alert_type == "MODEL_F1_DECAY"
    assert alert.previous_value == 0.88
    assert alert.current_value == 0.75
    assert "VADER-Baseline" in alert.message


def test_severity_escalation(default_engine: AlertEngine):
    """Verify extreme surges escalate severity to HIGH."""
    # Severe rating drop: 4.8 down to 2.5 (drop of 2.3 >= 1.0 high threshold)
    alert = default_engine.check_rating_drop(previous_rating=4.8, current_rating=2.5)
    assert alert is not None
    assert alert.severity == AlertSeverity.HIGH.value


def test_configurable_threshold_overrides(custom_engine: AlertEngine):
    """Verify non-hardcoded custom thresholds trigger at custom levels."""
    # Custom threshold is 15% increase. 20% to 36% -> delta 16% (triggers custom, but would miss standard 20%)
    alert = custom_engine.check_negative_sentiment_surge(
        previous_pct=20.0,
        current_pct=36.0,
    )
    assert alert is not None


def test_alert_schema_completeness(default_engine: AlertEngine):
    """Verify that all 12 required alert schema fields are present."""
    alert = default_engine.check_negative_sentiment_surge(
        previous_pct=10.0,
        current_pct=50.0,
        product="P1",
        topic="delivery",
    )
    assert alert is not None
    d = alert.to_dict()

    required_fields = [
        "alert_id",
        "alert_type",
        "severity",
        "product",
        "topic",
        "metric",
        "previous_value",
        "current_value",
        "percentage_change",
        "message",
        "created_at",
        "status",
    ]
    for field in required_fields:
        assert field in d
        assert d[field] is not None
