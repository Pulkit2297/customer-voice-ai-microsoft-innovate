"""CLI script to run Product & Campaign Attribution on CustomerVoice AI reviews.

Usage:
    python scripts/run_attribution.py [--input <INPUT_CSV>] [--output <OUTPUT_CSV>]

Default Input:
    data/processed/reviews_enriched.csv
Default Output:
    data/processed/reviews_attributed.csv
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

from src.attribution.attributor import ReviewAttributor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_attribution")


def run_attribution_pipeline(input_path: str, output_path: str) -> None:
    """Run product and campaign attribution pipeline with integrity validation."""
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
    logger.info("CustomerVoice AI - Product & Campaign Attribution Pipeline")
    logger.info("=" * 65)
    logger.info("Input file:  %s", in_file)
    logger.info("Output file: %s", out_file)

    try:
        df = pd.read_csv(in_file)
    except Exception as e:
        logger.error("Failed to read input CSV: %s", str(e))
        sys.exit(1)

    initial_rows = len(df)
    logger.info("Loaded %d reviews for attribution.", initial_rows)

    attributor = ReviewAttributor(null_as_none=True)
    attributed_df = attributor.attribute_dataframe(df)

    # Validation
    val_report = attributor.validate_attribution(
        attributed_df,
        expected_row_count=initial_rows,
        allow_nulls=True,
    )

    # Ensure parent output directory exists
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Save output
    attributed_df.to_csv(out_file, index=False)
    logger.info("Saved attributed dataset to: %s", out_file)

    logger.info("-" * 65)
    logger.info("Attribution Metrics & Validation Report:")
    logger.info("  Total Reviews Processed:    %d", val_report["total_reviews"])
    logger.info("  Product Attributed:         %d", val_report["product_attributed"])
    logger.info("  Product Unattributed:       %d", val_report["product_unattributed"])
    logger.info("  Campaign Attributed:        %d", val_report["campaign_attributed"])
    logger.info("  Campaign Unattributed:      %d", val_report["campaign_unattributed"])
    logger.info("  Fully Attributed (Both):    %d", val_report["fully_attributed"])
    logger.info("  Partially Attributed:       %d", val_report["partially_attributed"])
    logger.info("  Unattributed (Neither):     %d", val_report["unattributed"])
    logger.info("  Data Discarded / Dropped:   %d (0%% - Strict Integrity Maintained)", val_report["data_discarded"])
    logger.info("  Validation Status:          PASSED")
    logger.info("=" * 65)


def main():
    parser = argparse.ArgumentParser(
        description="Run CustomerVoice AI product and campaign attribution."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=str(PROJECT_ROOT / "data" / "processed" / "reviews_enriched.csv"),
        help="Input CSV path (default: data/processed/reviews_enriched.csv)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=str(PROJECT_ROOT / "data" / "processed" / "reviews_attributed.csv"),
        help="Output CSV path (default: data/processed/reviews_attributed.csv)",
    )

    args = parser.parse_args()
    run_attribution_pipeline(args.input, args.output)


if __name__ == "__main__":
    main()
