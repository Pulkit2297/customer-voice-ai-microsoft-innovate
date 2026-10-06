"""CLI execution script for CustomerVoice AI review preprocessing pipeline.

Usage:
    python scripts/run_preprocessing.py --input <CSV_PATH>

Output:
    data/processed/reviews_cleaned.csv
"""

import argparse
import sys
from pathlib import Path
import pandas as pd

# Add project root to sys.path so modules can be imported directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocessing.clean_reviews import clean_reviews_dataframe, PREPROCESSED_COLUMNS


def run_pipeline(input_path: str, output_path: str) -> None:
    """Run the review cleaning pipeline and persist results."""
    in_file = Path(input_path).resolve()
    out_file = Path(output_path).resolve()

    if not in_file.is_file():
        print(f"Error: Input file does not exist at '{in_file}'", file=sys.stderr)
        sys.exit(1)

    print("=" * 65)
    print("CustomerVoice AI - Review Preprocessing Pipeline")
    print("=" * 65)
    print(f"Input file:  {in_file}")
    print(f"Output file: {out_file}")

    try:
        raw_df = pd.read_csv(in_file)
    except Exception as e:
        print(f"Error reading input CSV: {e}", file=sys.stderr)
        sys.exit(1)

    initial_count = len(raw_df)
    print(f"Loaded {initial_count:,} raw rows.")

    # Harmonize common column name variations if present
    df = raw_df.copy()
    if "review_text" not in df.columns:
        if "sentence" in df.columns:
            print("Mapping column 'sentence' -> 'review_text'")
            df["review_text"] = df["sentence"]
        elif "text" in df.columns:
            print("Mapping column 'text' -> 'review_text'")
            df["review_text"] = df["text"]

    if "review_id" not in df.columns:
        if "id" in df.columns:
            print("Mapping column 'id' -> 'review_id'")
            df["review_id"] = df["id"]
        else:
            print("Notice: 'review_id' not found in input; generating synthetic IDs.")
            df["review_id"] = [f"REV_{i+1:06d}" for i in range(len(df))]

    # Run preprocessing
    cleaned_df = clean_reviews_dataframe(df)
    final_count = len(cleaned_df)

    # Ensure parent output directory exists
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Save to data/processed/
    cleaned_df.to_csv(out_file, index=False)

    print("-" * 65)
    print(f"Initial raw rows:       {initial_count:,}")
    print(f"Filtered / Cleaned rows:{final_count:,}")
    print(f"Removed invalid rows:   {initial_count - final_count:,}")
    print(f"Output saved to:        {out_file}")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(
        description="Run CustomerVoice AI review preprocessing pipeline."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        required=True,
        help="Path to the input customer review CSV file.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=str(PROJECT_ROOT / "data" / "processed" / "reviews_cleaned.csv"),
        help="Path for output cleaned CSV (default: data/processed/reviews_cleaned.csv)",
    )

    args = parser.parse_args()
    run_pipeline(args.input, args.output)


if __name__ == "__main__":
    main()
