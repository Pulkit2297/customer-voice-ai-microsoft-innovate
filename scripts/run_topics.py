"""CLI execution script for CustomerVoice AI Topic Detection pipeline.

Usage:
    python scripts/run_topics.py [--input <INPUT_CSV>] [--output <OUTPUT_CSV>]

Default Input:
    data/processed/reviews_with_sentiment.csv
Default Output:
    data/processed/reviews_enriched.csv
"""

import argparse
import logging
import sys
from collections import Counter
from pathlib import Path
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.topics.topic_engine import TopicClassifier, add_topics_to_dataframe

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_topics")


def run_topic_pipeline(input_path: str, output_path: str) -> None:
    """Run topic classification on sentiment-annotated reviews and persist output."""
    in_file = Path(input_path).resolve()
    out_file = Path(output_path).resolve()

    if not in_file.is_file():
        logger.error("Input file does not exist at: %s", in_file)
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
    logger.info("CustomerVoice AI - Topic Detection Pipeline")
    logger.info("=" * 65)
    logger.info("Input file:  %s", in_file)
    logger.info("Output file: %s", out_file)

    try:
        df = pd.read_csv(in_file)
    except Exception as e:
        logger.error("Failed to read input CSV: %s", str(e))
        sys.exit(1)

    initial_columns = list(df.columns)
    total_rows = len(df)
    logger.info("Loaded %d rows with %d columns.", total_rows, len(initial_columns))

    # Initialize topic classifier
    classifier = TopicClassifier()
    logger.info(
        "Loaded taxonomy with %d topics: %s",
        len(classifier.get_supported_topics()),
        ", ".join(classifier.get_supported_topics()),
    )

    # Enrich DataFrame
    enriched_df = add_topics_to_dataframe(
        df=df,
        text_column="cleaned_text",
        classifier=classifier,
    )

    # Verify no previous columns were deleted
    for col in initial_columns:
        if col not in enriched_df.columns:
            logger.error("Regression error: Previous column '%s' was deleted!", col)
            sys.exit(1)

    # Ensure parent directory exists
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Save output
    enriched_df.to_csv(out_file, index=False)
    logger.info("Saved enriched dataset to: %s", out_file)

    # Aggregate topic statistics
    reviews_with_topics = enriched_df[enriched_df["primary_topic"].notna() & (enriched_df["primary_topic"] != "")]
    coverage_pct = (len(reviews_with_topics) / total_rows * 100) if total_rows > 0 else 0.0

    all_assigned_topics = []
    for t_str in enriched_df["topics"]:
        if t_str and isinstance(t_str, str):
            all_assigned_topics.extend(t_str.split(","))

    topic_counts = Counter(all_assigned_topics)

    logger.info("-" * 65)
    logger.info("Topic Detection Summary:")
    logger.info("  Total Reviews Evaluated:  %d", total_rows)
    logger.info("  Reviews with Topics:      %d (%.2f%%)", len(reviews_with_topics), coverage_pct)
    logger.info("  Reviews without Topics:   %d (%.2f%%)", total_rows - len(reviews_with_topics), 100.0 - coverage_pct)
    logger.info("\nMost Frequent Topics Detected:")
    for topic, count in topic_counts.most_common(10):
        logger.info("  - %-20s: %5d mentions", topic, count)
    logger.info("=" * 65)


def main():
    parser = argparse.ArgumentParser(
        description="Run CustomerVoice AI topic detection on reviews."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=str(PROJECT_ROOT / "data" / "processed" / "reviews_with_sentiment.csv"),
        help="Input CSV path (default: data/processed/reviews_with_sentiment.csv)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=str(PROJECT_ROOT / "data" / "processed" / "reviews_enriched.csv"),
        help="Output CSV path (default: data/processed/reviews_enriched.csv)",
    )

    args = parser.parse_args()
    run_topic_pipeline(args.input, args.output)


if __name__ == "__main__":
    main()
