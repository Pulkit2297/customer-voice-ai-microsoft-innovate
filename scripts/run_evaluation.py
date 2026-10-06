"""CLI script to run Model Evaluation (Sentiment and Topic Detection).

Usage:
    python scripts/run_evaluation.py [--predictions <PATH>] [--validation <PATH>] [--output <PATH>]

Defaults:
    --predictions: data/processed/reviews_attributed.csv
    --validation:  data/validation/validation_set.csv
    --output:      data/processed/model_metrics.csv
"""

import argparse
import logging
import sys
from pathlib import Path
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.evaluate_sentiment import evaluate_sentiment
from src.evaluation.evaluate_topics import evaluate_topics, save_model_metrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_evaluation")


def run_evaluation_pipeline(
    predictions_path: str,
    validation_path: str,
    output_path: str,
) -> None:
    """Execute model evaluation against labelled ground-truth validation set."""
    pred_file = Path(predictions_path).resolve()
    val_file = Path(validation_path).resolve()
    out_file = Path(output_path).resolve()

    if not pred_file.is_file():
        logger.error("Predictions file not found at: %s", pred_file)
        sys.exit(1)

    if not val_file.is_file():
        logger.error("Validation set not found at: %s", val_file)
        sys.exit(1)

    logger.info("=" * 65)
    logger.info("CustomerVoice AI - Model Evaluation Pipeline")
    logger.info("=" * 65)
    logger.info("Predictions file: %s", pred_file)
    logger.info("Validation file:  %s", val_file)
    logger.info("Metrics output:   %s", out_file)

    try:
        val_df = pd.read_csv(val_file, comment="#")
    except Exception as e:
        logger.error("Failed to read validation set: %s", e)
        sys.exit(1)

    try:
        pred_df = pd.read_csv(pred_file)
    except Exception as e:
        logger.error("Failed to read predictions dataset: %s", e)
        sys.exit(1)

    # Merge on review_id
    merged = pd.merge(
        val_df,
        pred_df,
        on="review_id",
        how="inner",
        suffixes=("_truth", "_pred"),
    )

    if merged.empty:
        logger.error("Zero matching review_id records found between validation set and predictions!")
        sys.exit(1)

    logger.info("Found %d matching validation records for evaluation.", len(merged))

    # 1. Evaluate Sentiment
    sentiment_report = evaluate_sentiment(
        y_true=merged["actual_sentiment"],
        y_pred=merged["sentiment"],
    )
    sentiment_report.print_summary()

    # 2. Evaluate Topics
    topic_report = evaluate_topics(
        y_true_topics=merged["actual_topic"],
        y_pred_topics=merged["topics"],
    )
    topic_report.print_summary()

    # 3. Export tidy metrics to data/processed/model_metrics.csv
    all_records = sentiment_report.to_tidy_records() + topic_report.to_tidy_records()
    save_model_metrics(
        records=all_records,
        output_path=out_file,
        sample_size=len(merged),
    )
    logger.info("Evaluation metrics successfully written to: %s", out_file)


def main():
    parser = argparse.ArgumentParser(
        description="Run CustomerVoice AI model evaluation."
    )
    parser.add_argument(
        "--predictions",
        "-p",
        type=str,
        default=str(PROJECT_ROOT / "data" / "processed" / "reviews_attributed.csv"),
        help="Path to predictions dataset (default: data/processed/reviews_attributed.csv)",
    )
    parser.add_argument(
        "--validation",
        "-v",
        type=str,
        default=str(PROJECT_ROOT / "data" / "validation" / "validation_set.csv"),
        help="Path to validation ground truth CSV (default: data/validation/validation_set.csv)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=str(PROJECT_ROOT / "data" / "processed" / "model_metrics.csv"),
        help="Path for metrics output CSV (default: data/processed/model_metrics.csv)",
    )

    args = parser.parse_args()
    run_evaluation_pipeline(args.predictions, args.validation, args.output)


if __name__ == "__main__":
    main()
