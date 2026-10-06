"""CLI execution script for CustomerVoice AI Sentiment Analysis baseline.

Usage:
    python scripts/run_sentiment.py [--input <INPUT_CSV>] [--output <OUTPUT_CSV>] [--batch-size <INT>]

Default Input:
    data/processed/reviews_pii_safe.csv
Default Output:
    data/processed/reviews_with_sentiment.csv
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

from src.sentiment.local_model import LocalSentimentModel, add_sentiment_to_dataframe

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_sentiment")


def run_sentiment_pipeline(
    input_path: str,
    output_path: str,
    batch_size: int = 100,
) -> None:
    """Execute sentiment classification pipeline and persist output."""
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
    logger.info("CustomerVoice AI - Sentiment Analysis Baseline Pipeline")
    logger.info("=" * 65)
    logger.info("Input file:  %s", in_file)
    logger.info("Output file: %s", out_file)
    logger.info("Batch size:  %d", batch_size)

    try:
        df = pd.read_csv(in_file)
    except Exception as e:
        logger.error("Failed to read input CSV: %s", str(e))
        sys.exit(1)

    total_rows = len(df)
    if total_rows == 0:
        logger.warning("Input file is empty (0 rows).")
        sys.exit(0)

    logger.info("Loaded %d rows for sentiment evaluation.", total_rows)

    # Instantiate local baseline model
    model = LocalSentimentModel()
    logger.info("Using sentiment model: %s (v%s)", model.model_name, model.model_version)

    # Process in batches
    try:
        enriched_df = add_sentiment_to_dataframe(
            df=df,
            text_column="cleaned_text",
            model=model,
            batch_size=batch_size,
        )
    except Exception as e:
        logger.error("Error during sentiment batch processing: %s", str(e))
        sys.exit(1)

    # Output directory verification
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Save output
    enriched_df.to_csv(out_file, index=False)
    logger.info("Saved sentiment-annotated dataset to: %s", out_file)

    # Distribution summary
    counts = Counter(enriched_df["sentiment"])
    logger.info("-" * 65)
    logger.info("Sentiment Distribution Summary:")
    for label in ["positive", "neutral", "negative"]:
        c = counts.get(label, 0)
        pct = (c / total_rows * 100) if total_rows > 0 else 0.0
        logger.info("  - %-8s: %6d (%5.2f%%)", label.capitalize(), c, pct)
    logger.info("=" * 65)


def main():
    parser = argparse.ArgumentParser(
        description="Run CustomerVoice AI sentiment analysis baseline."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=str(PROJECT_ROOT / "data" / "processed" / "reviews_pii_safe.csv"),
        help="Input CSV file (default: data/processed/reviews_pii_safe.csv)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=str(PROJECT_ROOT / "data" / "processed" / "reviews_with_sentiment.csv"),
        help="Output CSV file (default: data/processed/reviews_with_sentiment.csv)",
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=100,
        help="Batch size for text chunk processing (default: 100)",
    )

    args = parser.parse_args()
    run_sentiment_pipeline(
        input_path=args.input,
        output_path=args.output,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
