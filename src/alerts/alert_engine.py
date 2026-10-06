"""Alert generation engine for CustomerVoice AI.

Evaluates operational metrics against externalized thresholds and generates
actionable, structured alerts with severity levels (LOW, MEDIUM, HIGH).
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any, Dict, List, Optional, Union
import uuid
import pandas as pd

from src.alerts.alert_config import AlertThresholds, default_thresholds

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Allowed severity classifications."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AlertStatus(str, Enum):
    """Alert lifecycle statuses."""

    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


@dataclass(frozen=True)
class Alert:
    """Standardized alert record structure."""

    alert_id: str
    alert_type: str
    severity: str  # LOW, MEDIUM, HIGH
    product: str
    topic: str
    metric: str
    previous_value: float
    current_value: float
    percentage_change: float
    message: str
    created_at: str
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AlertEngine:
    """Evaluates customer voice metrics and triggers structured alerts."""

    def __init__(
        self,
        thresholds: Optional[AlertThresholds] = None,
        is_demonstration: bool = False,
    ):
        """Initialize engine with configurable thresholds and demonstration mode."""
        self.thresholds = thresholds or default_thresholds
        self.is_demonstration = is_demonstration

    def _format_alert_type(self, base_type: str, is_demo: bool) -> str:
        return f"DEMONSTRATION - {base_type}" if (is_demo or self.is_demonstration) else base_type

    def _format_message(self, base_msg: str, is_demo: bool) -> str:
        return f"[Algorithmic Alert Demonstration] {base_msg}" if (is_demo or self.is_demonstration) else base_msg

    def check_negative_sentiment_surge(
        self,
        previous_pct: float,
        current_pct: float,
        product: str = "all",
        topic: str = "all",
        is_demonstration: bool = False,
    ) -> Optional[Alert]:
        """Trigger alert if negative sentiment percentage increases by >= threshold."""
        delta = current_pct - previous_pct
        pct_increase = ((current_pct - previous_pct) / abs(previous_pct) * 100.0) if previous_pct > 0 else (100.0 if current_pct > 0 else 0.0)

        # Trigger if absolute delta or relative increase exceeds threshold
        if delta >= self.thresholds.negative_sentiment_increase_pct or pct_increase >= self.thresholds.negative_sentiment_increase_pct:
            if delta >= self.thresholds.high_negative_sentiment_increase_pct or pct_increase >= self.thresholds.high_negative_sentiment_increase_pct:
                severity = AlertSeverity.HIGH.value
            else:
                severity = AlertSeverity.MEDIUM.value

            return Alert(
                alert_id=f"ALT_{uuid.uuid4().hex[:8].upper()}",
                alert_type=self._format_alert_type("NEGATIVE_SENTIMENT_SURGE", is_demonstration),
                severity=severity,
                product=product,
                topic=topic,
                metric="negative_sentiment_pct",
                previous_value=round(previous_pct, 2),
                current_value=round(current_pct, 2),
                percentage_change=round(pct_increase, 2),
                message=self._format_message(
                    f"Negative sentiment surged from {previous_pct:.1f}% to {current_pct:.1f}% "
                    f"(+{pct_increase:.1f}% shift) for product='{product}', topic='{topic}'.",
                    is_demonstration,
                ),
                created_at=datetime.now(timezone.utc).isoformat(),
                status=AlertStatus.ACTIVE.value,
            )
        return None

    def check_topic_volume_surge(
        self,
        previous_volume: float,
        current_volume: float,
        topic: str,
        product: str = "all",
        is_demonstration: bool = False,
    ) -> Optional[Alert]:
        """Trigger alert if topic review volume increases by >= threshold."""
        if previous_volume <= 0:
            pct_change = 100.0 if current_volume > 0 else 0.0
        else:
            pct_change = ((current_volume - previous_volume) / previous_volume) * 100.0

        if pct_change >= self.thresholds.topic_volume_increase_pct and current_volume >= 3:
            severity = (
                AlertSeverity.HIGH.value
                if pct_change >= self.thresholds.high_topic_volume_increase_pct
                else AlertSeverity.MEDIUM.value
            )

            return Alert(
                alert_id=f"ALT_{uuid.uuid4().hex[:8].upper()}",
                alert_type=self._format_alert_type("TOPIC_VOLUME_SURGE", is_demonstration),
                severity=severity,
                product=product,
                topic=topic,
                metric="topic_volume",
                previous_value=round(previous_volume, 2),
                current_value=round(current_volume, 2),
                percentage_change=round(pct_change, 2),
                message=self._format_message(
                    f"Spike in discussion volume for topic '{topic}' "
                    f"from {int(previous_volume)} to {int(current_volume)} (+{pct_change:.1f}%).",
                    is_demonstration,
                ),
                created_at=datetime.now(timezone.utc).isoformat(),
                status=AlertStatus.ACTIVE.value,
            )
        return None

    def check_rating_drop(
        self,
        previous_rating: float,
        current_rating: float,
        product: str = "all",
        topic: str = "all",
        is_demonstration: bool = False,
    ) -> Optional[Alert]:
        """Trigger alert if average customer star rating drops by >= threshold."""
        drop = previous_rating - current_rating
        pct_change = ((current_rating - previous_rating) / previous_rating) * 100.0 if previous_rating > 0 else 0.0

        if drop >= self.thresholds.rating_decrease_absolute:
            severity = (
                AlertSeverity.HIGH.value
                if drop >= self.thresholds.high_rating_decrease_absolute
                else AlertSeverity.MEDIUM.value
            )

            return Alert(
                alert_id=f"ALT_{uuid.uuid4().hex[:8].upper()}",
                alert_type=self._format_alert_type("RATING_DROP", is_demonstration),
                severity=severity,
                product=product,
                topic=topic,
                metric="average_rating",
                previous_value=round(previous_rating, 2),
                current_value=round(current_rating, 2),
                percentage_change=round(pct_change, 2),
                message=self._format_message(
                    f"Average star rating fell by {drop:.2f} stars "
                    f"(from {previous_rating:.2f} to {current_rating:.2f}) for product='{product}'.",
                    is_demonstration,
                ),
                created_at=datetime.now(timezone.utc).isoformat(),
                status=AlertStatus.ACTIVE.value,
            )
        return None

    def check_model_f1_decay(
        self,
        previous_f1: float,
        current_f1: float,
        model_name: str = "sentiment_baseline",
        is_demonstration: bool = False,
    ) -> Optional[Alert]:
        """Trigger alert if model F1 validation score drops by >= threshold."""
        drop = previous_f1 - current_f1
        pct_change = ((current_f1 - previous_f1) / previous_f1) * 100.0 if previous_f1 > 0 else 0.0

        if drop >= self.thresholds.model_f1_decrease_absolute:
            severity = (
                AlertSeverity.HIGH.value
                if drop >= self.thresholds.high_model_f1_decrease_absolute
                else AlertSeverity.MEDIUM.value
            )

            return Alert(
                alert_id=f"ALT_{uuid.uuid4().hex[:8].upper()}",
                alert_type=self._format_alert_type("MODEL_F1_DECAY", is_demonstration),
                severity=severity,
                product="all",
                topic="all",
                metric="model_f1_score",
                previous_value=round(previous_f1, 4),
                current_value=round(current_f1, 4),
                percentage_change=round(pct_change, 2),
                message=self._format_message(
                    f"Model performance degradation detected for '{model_name}': "
                    f"F1 decreased by {drop:.4f} (from {previous_f1:.4f} to {current_f1:.4f}).",
                    is_demonstration,
                ),
                created_at=datetime.now(timezone.utc).isoformat(),
                status=AlertStatus.ACTIVE.value,
            )
        return None

    def evaluate_all(
        self,
        trends_df: Optional[pd.DataFrame] = None,
        model_metrics_df: Optional[pd.DataFrame] = None,
        is_demonstration: bool = False,
    ) -> List[Alert]:
        """Scan trends and model metrics datasets to generate a consolidated alerts list."""
        alerts: List[Alert] = []

        # 1. Evaluate trends DataFrame if provided
        if trends_df is not None and not trends_df.empty:
            # Skip temporal alerts if trends data has status 'insufficient_temporal_data'
            if "detected_at" in trends_df.columns and (trends_df["detected_at"] == "insufficient_temporal_data").any():
                logger.info("Skipping temporal alert evaluation: trends_df contains 'insufficient_temporal_data'.")
            else:
                for _, row in trends_df.iterrows():
                    metric = str(row.get("metric", ""))
                    prev = float(row.get("previous_value", 0.0))
                    curr = float(row.get("current_value", 0.0))
                    prod = str(row.get("product", "all"))
                    top = str(row.get("topic", "all"))

                    if "negative" in metric.lower():
                        a = self.check_negative_sentiment_surge(
                            previous_pct=prev,
                            current_pct=curr,
                            product=prod,
                            topic=top,
                            is_demonstration=is_demonstration,
                        )
                        if a:
                            alerts.append(a)

                    elif "topic_volume" in metric.lower():
                        a = self.check_topic_volume_surge(
                            previous_volume=prev,
                            current_volume=curr,
                            topic=top,
                            product=prod,
                            is_demonstration=is_demonstration,
                        )
                        if a:
                            alerts.append(a)

                    elif "rating" in metric.lower():
                        a = self.check_rating_drop(
                            previous_rating=prev,
                            current_rating=curr,
                            product=prod,
                            topic=top,
                            is_demonstration=is_demonstration,
                        )
                        if a:
                            alerts.append(a)

        # 2. Evaluate model metrics decay if provided
        if model_metrics_df is not None and not model_metrics_df.empty:
            f1_rows = model_metrics_df[
                model_metrics_df["metric_name"].isin(["macro_f1", "weighted_f1", "f1_score"])
            ]
            if len(f1_rows) >= 2:
                prev_f1 = float(f1_rows.iloc[-2]["metric_value"])
                curr_f1 = float(f1_rows.iloc[-1]["metric_value"])
                a = self.check_model_f1_decay(
                    previous_f1=prev_f1,
                    current_f1=curr_f1,
                    model_name=str(f1_rows.iloc[-1].get("category", "sentiment")),
                    is_demonstration=is_demonstration,
                )
                if a:
                    alerts.append(a)

        return alerts
