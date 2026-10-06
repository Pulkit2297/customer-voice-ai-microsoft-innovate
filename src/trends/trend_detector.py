"""Trend and anomaly detection engine for CustomerVoice AI.

Provides modular temporal analytics:
1. Review volume over time
2. Positive, neutral, and negative sentiment over time
3. Topic volume over time
4. Negative sentiment percentage by topic
5. Negative sentiment percentage by product
6. Week-over-week (WoW) change
7. Month-over-month (MoM) change

Includes transparent, statistical anomaly detection (Z-score and rate-of-change)
without opaque or unnecessarily complex ML models.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnomalyResult:
    """Standardized result schema for detected trends and anomalies."""

    metric: str
    topic: str
    product: str
    previous_value: float
    current_value: float
    percentage_change: float
    anomaly_score: float
    is_anomaly: bool
    detected_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def calculate_percentage_change(previous_val: float, current_val: float) -> float:
    """Calculate percentage change between two values.

    Handles zero-denominator boundaries safely:
    - 0 to 0 -> 0.0%
    - 0 to positive -> 100.0%
    - 0 to negative -> -100.0%
    """
    prev = float(previous_val)
    curr = float(current_val)

    if prev == 0.0:
        if curr == 0.0:
            return 0.0
        return 100.0 if curr > 0.0 else -100.0

    pct = ((curr - prev) / abs(prev)) * 100.0
    return round(pct, 2)


def detect_series_anomalies(
    time_series: pd.Series,
    metric_name: str,
    topic: str = "all",
    product: str = "all",
    z_threshold: float = 2.0,
    pct_change_threshold: float = 50.0,
    min_volume_diff: float = 3.0,
) -> List[AnomalyResult]:
    """Detect statistical anomalies across a sequential time series.

    Uses a transparent statistical approach combining:
    1. Z-Score against baseline distribution: |x - mean| / std
    2. Rate of change (percentage change from previous interval)

    Args:
        time_series: Sequential pandas Series indexed by period strings/dates.
        metric_name: Name of metric (e.g. 'review_volume', 'negative_pct').
        topic: Topic scope or 'all'.
        product: Product scope or 'all'.
        z_threshold: Z-score cutoff for anomaly flag (default: 2.0).
        pct_change_threshold: Percentage spike threshold (default: 50.0%).
        min_volume_diff: Minimum absolute difference to trigger percentage anomaly.

    Returns:
        List of AnomalyResult objects.
    """
    results: List[AnomalyResult] = []
    if time_series is None or len(time_series) < 2:
        return results

    values = time_series.values.astype(float)
    periods = [str(idx) for idx in time_series.index]

    mean_val = float(np.mean(values))
    std_val = float(np.std(values))

    for i in range(1, len(values)):
        prev = values[i - 1]
        curr = values[i]
        period_str = periods[i]

        pct_change = calculate_percentage_change(prev, curr)

        # Z-score relative to overall distribution
        z_score = abs(curr - mean_val) / std_val if std_val > 1e-6 else 0.0

        # Anomaly determination
        is_z_anomaly = z_score >= z_threshold
        is_pct_anomaly = (
            abs(pct_change) >= pct_change_threshold
            and abs(curr - prev) >= min_volume_diff
        )

        is_anomaly = bool(is_z_anomaly or is_pct_anomaly)
        anomaly_score = round(max(z_score, abs(pct_change) / 100.0), 4)

        results.append(
            AnomalyResult(
                metric=metric_name,
                topic=topic,
                product=product,
                previous_value=round(prev, 2),
                current_value=round(curr, 2),
                percentage_change=pct_change,
                anomaly_score=anomaly_score,
                is_anomaly=is_anomaly,
                detected_at=period_str,
            )
        )

    return results


class TrendDetector:
    """Analyzer for temporal aggregations, trends, and statistical anomaly detection."""

    def __init__(self, z_threshold: float = 2.0, pct_threshold: float = 50.0):
        self.z_threshold = z_threshold
        self.pct_threshold = pct_threshold

    @staticmethod
    def has_temporal_data(df: pd.DataFrame) -> bool:
        """Check whether dataset contains genuine parseable timestamps."""
        if df is None or df.empty or "review_date" not in df.columns:
            return False
        return not df["review_date"].dropna().empty

    @staticmethod
    def _prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Ensure date column is parsed without manufacturing synthetic dates."""
        if df is None or df.empty or "review_date" not in df.columns or df["review_date"].isna().all():
            logger.info("review_date column absent or entirely null: insufficient_temporal_data.")
            return pd.DataFrame()

        clean_df = df.copy()
        clean_df["parsed_date"] = pd.to_datetime(clean_df["review_date"], errors="coerce")
        # Drop rows where date could not be parsed
        clean_df = clean_df.dropna(subset=["parsed_date"]).sort_values("parsed_date")
        return clean_df

    def calculate_review_volume_over_time(
        self,
        df: pd.DataFrame,
        freq: str = "W-MON",
    ) -> pd.DataFrame:
        """Calculate total customer review volume per period.

        Args:
            df: Reviews DataFrame.
            freq: Pandas period frequency ('W-MON' for weekly, 'ME' for monthly).

        Returns:
            DataFrame with columns: period, review_volume, wow_change (if weekly)
        """
        prepared = self._prepare_dataframe(df)
        if prepared.empty:
            empty_df = pd.DataFrame(columns=["period", "review_volume", "percentage_change"])
            empty_df.attrs["status"] = "insufficient_temporal_data"
            return empty_df

        volume_series = (
            prepared.set_index("parsed_date")
            .to_period(freq[0])
            .groupby("parsed_date")
            .size()
        )
        volume_df = volume_series.reset_index(name="review_volume")
        volume_df["period"] = volume_df["parsed_date"].astype(str)
        volume_df["percentage_change"] = (
            volume_df["review_volume"].pct_change().fillna(0.0) * 100.0
        ).round(2)

        return volume_df[["period", "review_volume", "percentage_change"]]

    def calculate_sentiment_over_time(
        self,
        df: pd.DataFrame,
        freq: str = "W-MON",
    ) -> pd.DataFrame:
        """Calculate positive, neutral, and negative counts and negative % over time."""
        prepared = self._prepare_dataframe(df)
        if prepared.empty or "sentiment" not in prepared.columns:
            empty_sent = pd.DataFrame(
                columns=[
                    "period",
                    "positive",
                    "neutral",
                    "negative",
                    "total_volume",
                    "negative_sentiment_pct",
                ]
            )
            empty_sent.attrs["status"] = "insufficient_temporal_data"
            return empty_sent

        prepared["period"] = prepared["parsed_date"].dt.to_period(freq[0]).astype(str)

        grouped = (
            prepared.groupby(["period", "sentiment"])
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )

        for col in ["positive", "neutral", "negative"]:
            if col not in grouped.columns:
                grouped[col] = 0

        grouped["total_volume"] = (
            grouped["positive"] + grouped["neutral"] + grouped["negative"]
        )
        grouped["negative_sentiment_pct"] = np.where(
            grouped["total_volume"] > 0,
            (grouped["negative"] / grouped["total_volume"] * 100.0).round(2),
            0.0,
        )

        return grouped[
            [
                "period",
                "positive",
                "neutral",
                "negative",
                "total_volume",
                "negative_sentiment_pct",
            ]
        ]

    def calculate_negative_sentiment_by_topic(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate negative sentiment count and percentage broken down by topic."""
        if df.empty or "topics" not in df.columns or "sentiment" not in df.columns:
            return pd.DataFrame(
                columns=["topic", "total_reviews", "negative_reviews", "negative_sentiment_pct"]
            )

        # Unnest multi-topic reviews
        records = []
        for _, row in df.iterrows():
            t_str = row.get("topics", "")
            sent = row.get("sentiment", "neutral")
            if pd.isna(t_str) or not str(t_str).strip():
                records.append({"topic": "unassigned", "sentiment": sent})
            else:
                for t in str(t_str).split(","):
                    t_clean = t.strip()
                    if t_clean:
                        records.append({"topic": t_clean, "sentiment": sent})

        topics_df = pd.DataFrame(records)
        if topics_df.empty:
            return pd.DataFrame(
                columns=["topic", "total_reviews", "negative_reviews", "negative_sentiment_pct"]
            )

        agg = (
            topics_df.groupby("topic")
            .agg(
                total_reviews=("sentiment", "count"),
                negative_reviews=("sentiment", lambda s: (s == "negative").sum()),
            )
            .reset_index()
        )

        agg["negative_sentiment_pct"] = (
            agg["negative_reviews"] / agg["total_reviews"] * 100.0
        ).round(2)

        return agg.sort_values("total_reviews", ascending=False).reset_index(drop=True)

    def calculate_negative_sentiment_by_product(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate negative sentiment count and percentage broken down by product."""
        if df.empty or "sentiment" not in df.columns:
            return pd.DataFrame()

        clean_df = df.copy()
        for col in ["product_id", "product_name"]:
            if col not in clean_df.columns:
                clean_df[col] = "unknown"
            else:
                clean_df[col] = clean_df[col].fillna("unknown")

        agg = (
            clean_df.groupby(["product_id", "product_name"])
            .agg(
                total_reviews=("sentiment", "count"),
                negative_reviews=("sentiment", lambda s: (s == "negative").sum()),
            )
            .reset_index()
        )

        agg["negative_sentiment_pct"] = (
            agg["negative_reviews"] / agg["total_reviews"] * 100.0
        ).round(2)

        return agg.sort_values("total_reviews", ascending=False).reset_index(drop=True)

    def run_full_anomaly_detection(
        self,
        df: pd.DataFrame,
        freq: str = "W",
    ) -> List[AnomalyResult]:
        """Execute anomaly detection across volume, overall sentiment, and topic volumes.

        Args:
            df: Enriched and attributed customer reviews DataFrame.
            freq: Aggregation interval ('W' for weekly, 'M' for monthly).

        Returns:
            List of detected AnomalyResult items.
        """
        all_anomalies: List[AnomalyResult] = []
        prepared = self._prepare_dataframe(df)
        if prepared.empty:
            return all_anomalies

        # 1. Total volume over time
        vol_df = self.calculate_review_volume_over_time(prepared, freq=freq)
        if len(vol_df) >= 2:
            vol_series = vol_df.set_index("period")["review_volume"]
            vol_anomalies = detect_series_anomalies(
                vol_series,
                metric_name="review_volume",
                z_threshold=self.z_threshold,
                pct_change_threshold=self.pct_threshold,
            )
            all_anomalies.extend(vol_anomalies)

        # 2. Negative sentiment % over time
        sent_df = self.calculate_sentiment_over_time(prepared, freq=freq)
        if len(sent_df) >= 2:
            neg_series = sent_df.set_index("period")["negative_sentiment_pct"]
            neg_anomalies = detect_series_anomalies(
                neg_series,
                metric_name="negative_sentiment_pct",
                z_threshold=self.z_threshold,
                pct_change_threshold=self.pct_threshold,
            )
            all_anomalies.extend(neg_anomalies)

        # 3. Per-topic negative sentiment
        topic_metrics = self.calculate_negative_sentiment_by_topic(prepared)
        for _, row in topic_metrics.iterrows():
            t_name = row["topic"]
            t_reviews = row["total_reviews"]
            t_neg_pct = row["negative_sentiment_pct"]
            # Flag severe negative topic concentration (>50% negative with >= 3 reviews)
            if t_neg_pct >= 50.0 and t_reviews >= 3:
                all_anomalies.append(
                    AnomalyResult(
                        metric="high_negative_topic_concentration",
                        topic=t_name,
                        product="all",
                        previous_value=0.0,
                        current_value=float(t_neg_pct),
                        percentage_change=float(t_neg_pct),
                        anomaly_score=round(t_neg_pct / 50.0, 4),
                        is_anomaly=True,
                        detected_at=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    )
                )

        return all_anomalies
