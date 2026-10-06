"""Multi-Source Archive Ingestion & Pipeline Runner for CustomerVoice AI.

Ingests real customer reviews from:
1. archive (1)/test.ft.txt.bz2 (Amazon multi-product reviews)
2. archive/train_data.csv (Sentiment140 social feedback)

Combines them into a multi-product, multi-source raw dataset and executes
the complete CustomerVoice AI pipeline end-to-end:
Preprocessing -> PII Scrubbing -> Sentiment Analysis -> Topic Detection ->
Product/Campaign Attribution -> Trend Detection -> Alerting ->
Model Evaluation -> Data Quality Gate Validation.

Usage:
    python scripts/ingest_archives.py [--amazon-count 4000] [--sentiment-count 1000] [--run-pipeline]
"""

import argparse
import logging
from pathlib import Path
import subprocess
import sys
import time
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.adapters.amazon_adapter import load_amazon_fasttext
from src.ingestion.adapters.sentiment140_adapter import load_sentiment140_csv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ingest_archives")

DEFAULT_AMAZON_BZ2 = WORKSPACE_ROOT / "archive (1)" / "test.ft.txt.bz2"
DEFAULT_SENTIMENT_CSV = WORKSPACE_ROOT / "archive" / "train_data.csv"
DEFAULT_OUTPUT_RAW = PROJECT_ROOT / "data" / "raw" / "reviews_multi_source.csv"


def ingest_and_combine(
    amazon_file: Path,
    sentiment_file: Path,
    amazon_count: int,
    sentiment_count: int,
    output_path: Path,
) -> pd.DataFrame:
    """Ingest from both archive sources and merge into single raw dataset."""
    frames = []

    if amazon_file.is_file() and amazon_count > 0:
        logger.info("Ingesting %d Amazon reviews from %s", amazon_count, amazon_file)
        amz_df = load_amazon_fasttext(amazon_file, max_records=amazon_count)
        frames.append(amz_df)
    else:
        logger.warning("Amazon archive file not found or count is 0: %s", amazon_file)

    if sentiment_file.is_file() and sentiment_count > 0:
        logger.info("Ingesting %d Sentiment140 reviews from %s", sentiment_count, sentiment_file)
        s140_df = load_sentiment140_csv(sentiment_file, max_records=sentiment_count)
        frames.append(s140_df)
    else:
        logger.warning("Sentiment140 archive file not found or count is 0: %s", sentiment_file)

    if not frames:
        raise ValueError("No records could be ingested from the specified archives.")

    combined_df = pd.concat(frames, ignore_index=True)
    # Ensure standard unique IDs across merged sources matching validation set schema
    combined_df["review_id"] = [f"REV_{i+1:06d}" for i in range(len(combined_df))]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(output_path, index=False)
    logger.info(
        "Successfully combined and saved %d multi-product reviews to %s",
        len(combined_df),
        output_path,
    )
    return combined_df


def execute_pipeline(raw_csv_path: Path) -> bool:
    """Run all CustomerVoice AI pipeline stages in sequence on the newly ingested raw dataset."""
    logger.info("=" * 70)
    logger.info("Starting Full CustomerVoice AI Pipeline Execution")
    logger.info("=" * 70)

    stages = [
        (
            "Phase 2: Preprocessing & Cleaning",
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "run_preprocessing.py"),
                "--input",
                str(raw_csv_path),
            ],
        ),
        (
            "Phase 3: PII Detection & Redaction",
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "run_pii_redaction.py"),
            ],
        ),
        (
            "Phase 4: Sentiment Analysis",
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "run_sentiment.py"),
            ],
        ),
        (
            "Phase 5: Topic Detection",
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "run_topics.py"),
            ],
        ),
        (
            "Phase 6: Product & Campaign Attribution",
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "run_attribution.py"),
            ],
        ),
        (
            "Phase 8: Trend & Anomaly Detection",
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "run_trends.py"),
            ],
        ),
        (
            "Phase 9: Operational Alert Generation",
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "generate_alerts.py"),
            ],
        ),
        (
            "Phase 7: Model Evaluation Benchmark",
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "run_evaluation.py"),
            ],
        ),
        (
            "Data Quality Validation Gate",
            [
                sys.executable,
                str(PROJECT_ROOT / "src" / "database" / "data_quality.py"),
            ],
        ),
    ]

    total_start = time.time()
    for name, cmd in stages:
        logger.info("--> Executing stage: %s", name)
        step_start = time.time()
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        step_duration = time.time() - step_start

        if res.returncode != 0:
            logger.error("Stage FAILED: %s (exit code %d)", name, res.returncode)
            logger.error("STDOUT:\n%s", res.stdout)
            logger.error("STDERR:\n%s", res.stderr)
            return False
        else:
            logger.info("Stage COMPLETED: %s (%.2fs)", name, step_duration)

    logger.info("=" * 70)
    logger.info("Full Pipeline Execution Completed Successfully in %.2fs", time.time() - total_start)
    logger.info("=" * 70)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest customer feedback from archive and archive (1) folders."
    )
    parser.add_argument(
        "--amazon-file",
        type=str,
        default=str(DEFAULT_AMAZON_BZ2),
        help="Path to Amazon FastText dataset file (.ft.txt.bz2)",
    )
    parser.add_argument(
        "--sentiment-file",
        type=str,
        default=str(DEFAULT_SENTIMENT_CSV),
        help="Path to Sentiment140 CSV file",
    )
    parser.add_argument(
        "--amazon-count",
        type=int,
        default=4000,
        help="Number of Amazon reviews to ingest (default: 4000)",
    )
    parser.add_argument(
        "--sentiment-count",
        type=int,
        default=1000,
        help="Number of Sentiment140 reviews to ingest (default: 1000)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_OUTPUT_RAW),
        help="Output raw CSV path (default: data/raw/reviews_multi_source.csv)",
    )
    parser.add_argument(
        "--run-pipeline",
        action="store_true",
        help="Automatically execute the complete pipeline on ingested reviews",
    )
    args = parser.parse_args()

    amazon_path = Path(args.amazon_file).resolve()
    sentiment_path = Path(args.sentiment_file).resolve()
    out_path = Path(args.output).resolve()

    df = ingest_and_combine(
        amazon_file=amazon_path,
        sentiment_file=sentiment_path,
        amazon_count=args.amazon_count,
        sentiment_count=args.sentiment_count,
        output_path=out_path,
    )

    print("\n" + "=" * 65)
    print("Archive Ingestion Summary:")
    print("=" * 65)
    print(f"Total Reviews Ingested: {len(df)}")
    print(f"Unique Products:        {df['product_id'].nunique()}")
    print("\nProducts Breakdown:")
    for pid, count in df["product_id"].value_counts().items():
        print(f"  - {pid:25s}: {count:5d} reviews")
    print("\nSource Breakdown:")
    for src, count in df["source"].value_counts().items():
        print(f"  - {src:25s}: {count:5d} reviews")
    print("=" * 65)

    if args.run_pipeline:
        success = execute_pipeline(out_path)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
