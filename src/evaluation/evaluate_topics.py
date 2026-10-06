"""Multi-label topic evaluation module for CustomerVoice AI.

Computes multi-label metrics (Hamming Loss, Subset Accuracy/Exact Match Ratio,
Micro/Macro Precision, Recall, F1-score, and per-topic performance)
against ground-truth validation sets.
"""

from datetime import datetime, timezone
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.metrics import (
    f1_score,
    hamming_loss,
    precision_score,
    recall_score,
)
from sklearn.preprocessing import MultiLabelBinarizer

logger = logging.getLogger(__name__)


def parse_topic_tokens(raw_topics: Any) -> List[str]:
    """Parse comma-separated or list-like topic values into clean sorted list of unique topics."""
    if raw_topics is None:
        return []

    if isinstance(raw_topics, (list, set, tuple)):
        return sorted(list({str(t).strip().lower() for t in raw_topics if str(t).strip()}))

    if pd.isna(raw_topics):
        return []


    text = str(raw_topics).strip()
    if text == "" or text.lower() in {"nan", "none", "{}", "[]"}:
        return []

    tokens = [t.strip().lower() for t in text.split(",") if t.strip()]
    return sorted(list(set(tokens)))


@dataclass
class TopicEvaluationReport:
    """Structured report holding multi-label topic evaluation metrics."""

    total_samples: int
    exact_match_ratio: float  # Subset accuracy
    hamming_loss_score: float  # Lower is better (0.0 is perfect)
    macro_precision: float
    macro_recall: float
    macro_f1: float
    micro_precision: float
    micro_recall: float
    micro_f1: float
    per_topic_metrics: Dict[str, Dict[str, float]]
    evaluated_topics: List[str]

    def print_summary(self) -> None:
        """Display formatted multi-label topic evaluation summary."""
        print("=" * 65)
        print("CustomerVoice AI - Multi-Label Topic Model Evaluation Report")
        print("=" * 65)
        print(f"Validation Samples Evaluated: {self.total_samples}")
        print(f"Exact Match Ratio (Subset Acc): {self.exact_match_ratio:.4f} ({self.exact_match_ratio * 100:.2f}%)")
        print(f"Hamming Loss:                   {self.hamming_loss_score:.4f}")
        print(f"Micro F1-Score:                 {self.micro_f1:.4f}")
        print(f"Macro F1-Score:                 {self.macro_f1:.4f}")
        print("-" * 65)
        print("Per-Topic Metrics:")
        for topic, m in self.per_topic_metrics.items():
            print(
                f"  - {topic:<20}: Precision={m['precision']:.4f}, "
                f"Recall={m['recall']:.4f}, F1={m['f1']:.4f} (Support={int(m['support'])})"
            )
        print("=" * 65)

    def to_tidy_records(self, evaluation_type: str = "topic") -> List[Dict[str, Any]]:
        """Convert metrics to normalized tidy records for model_metrics.csv."""
        records: List[Dict[str, Any]] = [
            {"evaluation_type": evaluation_type, "category": "overall", "metric_name": "exact_match_ratio", "metric_value": self.exact_match_ratio},
            {"evaluation_type": evaluation_type, "category": "overall", "metric_name": "hamming_loss", "metric_value": self.hamming_loss_score},
            {"evaluation_type": evaluation_type, "category": "overall", "metric_name": "micro_f1", "metric_value": self.micro_f1},
            {"evaluation_type": evaluation_type, "category": "overall", "metric_name": "macro_f1", "metric_value": self.macro_f1},
            {"evaluation_type": evaluation_type, "category": "overall", "metric_name": "macro_precision", "metric_value": self.macro_precision},
            {"evaluation_type": evaluation_type, "category": "overall", "metric_name": "macro_recall", "metric_value": self.macro_recall},
        ]
        for topic, m in self.per_topic_metrics.items():
            records.append({"evaluation_type": evaluation_type, "category": topic, "metric_name": "precision", "metric_value": m["precision"]})
            records.append({"evaluation_type": evaluation_type, "category": topic, "metric_name": "recall", "metric_value": m["recall"]})
            records.append({"evaluation_type": evaluation_type, "category": topic, "metric_name": "f1_score", "metric_value": m["f1"]})
            records.append({"evaluation_type": evaluation_type, "category": topic, "metric_name": "support", "metric_value": m["support"]})
        return records


def evaluate_topics(
    y_true_topics: List[Any],
    y_pred_topics: List[Any],
    all_known_topics: Optional[List[str]] = None,
) -> TopicEvaluationReport:
    """Compute multi-label topic evaluation metrics.

    Args:
        y_true_topics: Ground-truth topic sequences (e.g. ['battery', 'customer_support']).
        y_pred_topics: Predicted topic sequences.
        all_known_topics: Optional predefined taxonomy topics list.

    Returns:
        TopicEvaluationReport instance.
    """
    if len(y_true_topics) != len(y_pred_topics):
        raise ValueError(
            f"Length mismatch: {len(y_true_topics)} true topic entries vs {len(y_pred_topics)} predicted."
        )

    if len(y_true_topics) == 0:
        raise ValueError("Cannot evaluate an empty topic set.")

    # Parse and clean topic sets
    parsed_true = [parse_topic_tokens(t) for t in y_true_topics]
    parsed_pred = [parse_topic_tokens(t) for t in y_pred_topics]

    # Collect universal vocabulary of topics
    mlb = MultiLabelBinarizer()
    if all_known_topics:
        mlb.fit([[t] for t in all_known_topics])
    else:
        mlb.fit(parsed_true + parsed_pred)

    all_topics = list(mlb.classes_)
    y_true_bin = mlb.transform(parsed_true)
    y_pred_bin = mlb.transform(parsed_pred)

    total_samples = len(parsed_true)

    # Subset accuracy (Exact Match Ratio)
    exact_matches = np.all(y_true_bin == y_pred_bin, axis=1)
    exact_match_ratio = float(round(np.mean(exact_matches), 4))

    # Hamming loss (fraction of labels incorrectly predicted)
    h_loss = float(round(hamming_loss(y_true_bin, y_pred_bin), 4))

    # Macro and Micro metrics
    macro_p = float(round(precision_score(y_true_bin, y_pred_bin, average="macro", zero_division=0), 4))
    macro_r = float(round(recall_score(y_true_bin, y_pred_bin, average="macro", zero_division=0), 4))
    macro_f = float(round(f1_score(y_true_bin, y_pred_bin, average="macro", zero_division=0), 4))

    micro_p = float(round(precision_score(y_true_bin, y_pred_bin, average="micro", zero_division=0), 4))
    micro_r = float(round(recall_score(y_true_bin, y_pred_bin, average="micro", zero_division=0), 4))
    micro_f = float(round(f1_score(y_true_bin, y_pred_bin, average="micro", zero_division=0), 4))

    # Per-topic metrics
    per_topic_dict: Dict[str, Dict[str, float]] = {}
    for idx, topic_name in enumerate(all_topics):
        col_true = y_true_bin[:, idx]
        col_pred = y_pred_bin[:, idx]
        p = float(round(precision_score(col_true, col_pred, zero_division=0), 4))
        r = float(round(recall_score(col_true, col_pred, zero_division=0), 4))
        f = float(round(f1_score(col_true, col_pred, zero_division=0), 4))
        supp = float(np.sum(col_true))
        per_topic_dict[topic_name] = {
            "precision": p,
            "recall": r,
            "f1": f,
            "support": supp,
        }

    return TopicEvaluationReport(
        total_samples=total_samples,
        exact_match_ratio=exact_match_ratio,
        hamming_loss_score=h_loss,
        macro_precision=macro_p,
        macro_recall=macro_r,
        macro_f1=macro_f,
        micro_precision=micro_p,
        micro_recall=micro_r,
        micro_f1=micro_f,
        per_topic_metrics=per_topic_dict,
        evaluated_topics=all_topics,
    )


def save_model_metrics(
    records: List[Dict[str, Any]],
    output_path: Union[str, Path] = "data/processed/model_metrics.csv",
    sample_size: int = 0,
) -> Path:
    """Save evaluation metrics into standardized data/processed/model_metrics.csv.

    Args:
        records: List of tidy metric records from sentiment or topic reports.
        output_path: Destination CSV path.
        sample_size: Number of validation samples evaluated.

    Returns:
        Path to the saved CSV file.
    """
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()

    enriched_records = []
    for r in records:
        row = dict(r)
        row["validation_sample_size"] = sample_size
        row["evaluation_timestamp"] = timestamp
        enriched_records.append(row)

    metrics_df = pd.DataFrame(enriched_records)
    metrics_df.to_csv(out_file, index=False)
    logger.info("Saved %d model evaluation metrics to %s", len(metrics_df), out_file)
    return out_file
