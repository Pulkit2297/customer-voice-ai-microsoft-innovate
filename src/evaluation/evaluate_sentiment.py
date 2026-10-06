"""Sentiment model evaluation module for CustomerVoice AI.

Computes accuracy, precision, recall, F1-score (overall and per sentiment class),
confusion matrix, and scikit-learn classification report against labelled validation data.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)

logger = logging.getLogger(__name__)

SENTIMENT_CLASSES: List[str] = ["positive", "neutral", "negative"]


@dataclass
class SentimentEvaluationReport:
    """Structured report holding sentiment evaluation metrics."""

    total_samples: int
    accuracy: float
    macro_precision: float
    macro_recall: float
    macro_f1: float
    weighted_precision: float
    weighted_recall: float
    weighted_f1: float
    per_class_metrics: Dict[str, Dict[str, float]]
    confusion_matrix: List[List[int]]
    confusion_matrix_labels: List[str]
    classification_report_str: str

    def print_summary(self) -> None:
        """Display formatted evaluation results."""
        print("=" * 65)
        print("CustomerVoice AI - Sentiment Model Evaluation Report")
        print("=" * 65)
        print(f"Validation Samples Evaluated: {self.total_samples}")
        print(f"Overall Accuracy:            {self.accuracy:.4f} ({self.accuracy * 100:.2f}%)")
        print(f"Macro F1-Score:              {self.macro_f1:.4f}")
        print(f"Weighted F1-Score:           {self.weighted_f1:.4f}")
        print("-" * 65)
        print("Per-Class Metrics:")
        for cls_name, m in self.per_class_metrics.items():
            print(
                f"  - {cls_name:<9}: Precision={m['precision']:.4f}, "
                f"Recall={m['recall']:.4f}, F1={m['f1']:.4f} (Support={int(m['support'])})"
            )
        print("-" * 65)
        print("Confusion Matrix:")
        header = "          " + "".join([f"{l:>10}" for l in self.confusion_matrix_labels])
        print(header)
        for i, row in enumerate(self.confusion_matrix):
            row_str = f"{self.confusion_matrix_labels[i]:<10}" + "".join([f"{val:>10}" for val in row])
            print(row_str)
        print("-" * 65)
        print("Detailed Classification Report:")
        print(self.classification_report_str)
        print("=" * 65)

    def to_tidy_records(self, evaluation_type: str = "sentiment") -> List[Dict[str, Any]]:
        """Convert metrics to normalized tidy records for model_metrics.csv export."""
        records: List[Dict[str, Any]] = [
            {"evaluation_type": evaluation_type, "category": "overall", "metric_name": "accuracy", "metric_value": self.accuracy},
            {"evaluation_type": evaluation_type, "category": "overall", "metric_name": "macro_precision", "metric_value": self.macro_precision},
            {"evaluation_type": evaluation_type, "category": "overall", "metric_name": "macro_recall", "metric_value": self.macro_recall},
            {"evaluation_type": evaluation_type, "category": "overall", "metric_name": "macro_f1", "metric_value": self.macro_f1},
            {"evaluation_type": evaluation_type, "category": "overall", "metric_name": "weighted_f1", "metric_value": self.weighted_f1},
        ]
        for cls_name, m in self.per_class_metrics.items():
            records.append({"evaluation_type": evaluation_type, "category": cls_name, "metric_name": "precision", "metric_value": m["precision"]})
            records.append({"evaluation_type": evaluation_type, "category": cls_name, "metric_name": "recall", "metric_value": m["recall"]})
            records.append({"evaluation_type": evaluation_type, "category": cls_name, "metric_name": "f1_score", "metric_value": m["f1"]})
            records.append({"evaluation_type": evaluation_type, "category": cls_name, "metric_name": "support", "metric_value": m["support"]})
        return records


def evaluate_sentiment(
    y_true: Union[List[str], pd.Series],
    y_pred: Union[List[str], pd.Series],
    labels: Optional[List[str]] = None,
) -> SentimentEvaluationReport:
    """Compute comprehensive sentiment evaluation metrics.

    Args:
        y_true: Ground-truth sentiment labels.
        y_pred: Predicted sentiment labels from model.
        labels: Class label ordering. Defaults to ['positive', 'neutral', 'negative'].

    Returns:
        SentimentEvaluationReport instance.
    """
    classes = labels or SENTIMENT_CLASSES

    # Normalize inputs
    true_labels = [str(y).strip().lower() for y in y_true]
    pred_labels = [str(y).strip().lower() for y in y_pred]

    if len(true_labels) != len(pred_labels):
        raise ValueError(
            f"Length mismatch: {len(true_labels)} true labels vs {len(pred_labels)} predicted labels."
        )

    if len(true_labels) == 0:
        raise ValueError("Cannot evaluate an empty label set.")

    total_samples = len(true_labels)
    acc = float(accuracy_score(true_labels, pred_labels))

    # Overall Macro & Weighted metrics
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
        true_labels, pred_labels, average="macro", zero_division=0
    )
    p_wt, r_wt, f1_wt, _ = precision_recall_fscore_support(
        true_labels, pred_labels, average="weighted", zero_division=0
    )

    # Per-class metrics
    p_cls, r_cls, f1_cls, supp_cls = precision_recall_fscore_support(
        true_labels, pred_labels, labels=classes, zero_division=0
    )

    per_class_dict: Dict[str, Dict[str, float]] = {}
    for i, cls_name in enumerate(classes):
        per_class_dict[cls_name] = {
            "precision": float(round(p_cls[i], 4)),
            "recall": float(round(r_cls[i], 4)),
            "f1": float(round(f1_cls[i], 4)),
            "support": float(supp_cls[i]),
        }

    # Confusion matrix
    cm = confusion_matrix(true_labels, pred_labels, labels=classes)
    cm_list = cm.tolist()

    # Classification report text
    report_str = classification_report(
        true_labels,
        pred_labels,
        labels=classes,
        zero_division=0,
    )

    return SentimentEvaluationReport(
        total_samples=total_samples,
        accuracy=float(round(acc, 4)),
        macro_precision=float(round(p_macro, 4)),
        macro_recall=float(round(r_macro, 4)),
        macro_f1=float(round(f1_macro, 4)),
        weighted_precision=float(round(p_wt, 4)),
        weighted_recall=float(round(r_wt, 4)),
        weighted_f1=float(round(f1_wt, 4)),
        per_class_metrics=per_class_dict,
        confusion_matrix=cm_list,
        confusion_matrix_labels=classes,
        classification_report_str=report_str,
    )


def evaluate_sentiment_datasets(
    predictions_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    id_column: str = "review_id",
    pred_col: str = "sentiment",
    true_col: str = "actual_sentiment",
) -> SentimentEvaluationReport:
    """Evaluate sentiment predictions by joining predictions with validation dataset on review_id.

    Args:
        predictions_df: DataFrame containing model outputs with `id_column` and `pred_col`.
        validation_df: DataFrame containing ground truth with `id_column` and `true_col`.
        id_column: Primary key to join on.
        pred_col: Column with predicted sentiment.
        true_col: Column with ground truth sentiment.

    Returns:
        SentimentEvaluationReport.
    """
    merged = pd.merge(
        validation_df[[id_column, true_col]],
        predictions_df[[id_column, pred_col]],
        on=id_column,
        how="inner",
    )

    if merged.empty:
        raise ValueError(
            f"No matching '{id_column}' records between validation set and predictions."
        )

    logger.info("Evaluating sentiment on %d matched validation records.", len(merged))
    return evaluate_sentiment(
        y_true=merged[true_col],
        y_pred=merged[pred_col],
    )
