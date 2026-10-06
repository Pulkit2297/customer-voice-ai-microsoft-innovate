"""CLI execution script for CustomerVoice AI Trend and Anomaly Detection.

Usage:
    python scripts/run_trends.py [--input <INPUT_CSV>] [--output <OUTPUT_CSV>]

Default Input:
    data/processed/reviews_attributed.csv
Default Output:
    data/processed/trends.csv
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

from src.trends.trend_detector import TrendDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_trends")


def run_trend_pipeline(input_path: str, output_path: str) -> None:
    """Execute trend analysis and statistical anomaly detection."""
    in_file = Path(input_path).resolve()
    out_file = Path(output_path).resolve()

    if not in_file.is_file():
        logger.error("Input file not found at: %s", in_file)
        sys.exit(1)

    # Safeguard against raw dataset modification
    raw_dir = (PROJECT_ROOT / "data" / "raw").resolve()
    try:
        out_file.relative_to(raw_dir)
        logger.error(
            "Security Error: Output destination '%s' cannot be within data/raw/.",
            out_file,
        )
        sys.exit(1)
    except ValueError:
        pass

    logger.info("=" * 65)
    logger.info("CustomerVoice AI - Trend & Anomaly Detection Pipeline")
    logger.info("=" * 65)
    logger.info("Input file:  %s", in_file)
    logger.info("Output file: %s", out_file)

    try:
        df = pd.read_csv(in_file)
    except Exception as e:
        logger.error("Failed to read input CSV: %s", e)
        sys.exit(1)

    logger.info("Loaded %d reviews for trend evaluation.", len(df))

    detector = TrendDetector(z_threshold=2.0, pct_threshold=50.0)

    # Check temporal data presence
    if not detector.has_temporal_data(df):
        logger.warning(
            "Input dataset contains no genuine dates (review_date is NULL/missing). "
            "Temporal trends skipped: status = 'insufficient_temporal_data'."
        )
        trends_df = pd.DataFrame(
            [
                {
                    "metric": "review_volume",
                    "topic": "all",
                    "product": "all",
                    "previous_value": 0.0,
                    "current_value": 0.0,
                    "percentage_change": 0.0,
                    "anomaly_score": 0.0,
                    "is_anomaly": False,
                    "detected_at": "insufficient_temporal_data",
                }
            ]
        )
        out_file.parent.mkdir(parents=True, exist_ok=True)
        trends_df.to_csv(out_file, index=False)
        logger.info("Saved marked status record to: %s", out_file)
        logger.info("-" * 65)
        logger.info("Detected Anomalies Summary (0 items flagged):")
        logger.info("  - Temporal analytics skipped due to insufficient_temporal_data.")
        logger.info("=" * 65)
        return

    # 1. Review volume over time (Weekly)
    vol_weekly = detector.calculate_review_volume_over_time(df, freq="W-MON")
    logger.info("Computed weekly review volume over %d time intervals.", len(vol_weekly))

    # 2. Sentiment distribution over time
    sent_weekly = detector.calculate_sentiment_over_time(df, freq="W-MON")
    logger.info("Computed temporal sentiment distribution.")

    # 3. Negative sentiment by topic
    topic_neg = detector.calculate_negative_sentiment_by_topic(df)
    logger.info("Computed negative sentiment percentage across %d topics.", len(topic_neg))

    # 4. Negative sentiment by product
    prod_neg = detector.calculate_negative_sentiment_by_product(df)
    logger.info("Computed negative sentiment percentage across %d products.", len(prod_neg))

    # 5. Full anomaly detection
    anomalies = detector.run_full_anomaly_detection(df, freq="W")
    logger.info("Evaluated statistical anomalies: %d items analyzed.", len(anomalies))

    # Convert anomalies to DataFrame
    if anomalies:
        trends_df = pd.DataFrame([a.to_dict() for a in anomalies])
    else:
        trends_df = pd.DataFrame(
            columns=[
                "metric",
                "topic",
                "product",
                "previous_value",
                "current_value",
                "percentage_change",
                "anomaly_score",
                "is_anomaly",
                "detected_at",
            ]
        )

    # Ensure parent output directory exists
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Save to data/processed/trends.csv
    trends_df.to_csv(out_file, index=False)
    logger.info("Saved trend and anomaly records to: %s", out_file)

    # Display detected anomalies
    detected_subset = trends_df[trends_df["is_anomaly"] == True]
    logger.info("-" * 65)
    logger.info("Detected Anomalies Summary (%d items flagged):", len(detected_subset))
    if not detected_subset.empty:
        for _, row in detected_subset.iterrows():
            logger.info(
                "  - [%s | %s] Prev=%.2f -> Curr=%.2f (%+.2f%%) | Score=%.2f (Date: %s)",
                row["metric"],
                row["topic"],
                row["previous_value"],
                row["current_value"],
                row["percentage_change"],
                row["anomaly_score"],
                row["detected_at"],
            )
    else:
        logger.info("  - No statistical anomalies or critical spikes detected.")
    logger.info("=" * 65)


def main():
    parser = argparse.ArgumentParser(
        description="Run CustomerVoice AI trend and anomaly detection."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=str(PROJECT_ROOT / "data" / "processed" / "reviews_attributed.csv"),
        help="Input CSV path (default: data/processed/reviews_attributed.csv)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=str(PROJECT_ROOT / "data" / "processed" / "trends.csv"),
        help="Output CSV path (default: data/processed/trends.csv)",
    )

    args = parser.parse_args()
    run_trend_pipeline(args.input, args.output)


if __name__ == "__main__":
    main()
