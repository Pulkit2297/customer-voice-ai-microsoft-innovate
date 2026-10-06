"""CLI script to run PII detection and redaction on cleaned customer reviews.

Usage:
    python scripts/run_pii_redaction.py [--input <INPUT_CSV>] [--output <OUTPUT_CSV>]

Default Input:
    data/processed/reviews_cleaned.csv
Default Output:
    data/processed/reviews_pii_safe.csv
"""

import argparse
import sys
from collections import Counter
from pathlib import Path
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pii.redactor import redact_reviews_dataframe


def run_redaction(input_path: str, output_path: str) -> None:
    """Run PII redaction pipeline and save privacy-compliant output."""
    in_file = Path(input_path).resolve()
    out_file = Path(output_path).resolve()

    # Safeguard: Never overwrite raw datasets
    raw_dir = (PROJECT_ROOT / "data" / "raw").resolve()
    try:
        out_file.relative_to(raw_dir)
        print(
            f"Security Error: Output path '{out_file}' is inside raw data directory. "
            "Raw datasets must never be overwritten.",
            file=sys.stderr,
        )
        sys.exit(1)
    except ValueError:
        pass  # out_file is safely outside raw_dir

    if not in_file.is_file():
        print(f"Error: Input file does not exist at '{in_file}'", file=sys.stderr)
        sys.exit(1)

    print("=" * 65)
    print("CustomerVoice AI - PII Detection & Redaction Pipeline")
    print("=" * 65)
    print(f"Input file:  {in_file}")
    print(f"Output file: {out_file}")

    try:
        df = pd.read_csv(in_file)
    except Exception as e:
        print(f"Error reading input CSV: {e}", file=sys.stderr)
        sys.exit(1)

    total_rows = len(df)
    print(f"Loaded {total_rows:,} rows from input.")

    # Execute redaction
    safe_df = redact_reviews_dataframe(df)

    # Compute PII statistics
    pii_count = int(safe_df["pii_detected"].sum())
    pii_pct = (pii_count / total_rows * 100) if total_rows > 0 else 0.0

    # Aggregate detected types
    all_types = []
    for entry in safe_df["pii_types"].dropna():
        if entry:
            all_types.extend(entry.split(","))
    type_counts = Counter(all_types)

    # Ensure target output directory exists
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Save to destination
    safe_df.to_csv(out_file, index=False)

    print("-" * 65)
    print(f"Total Rows Processed:    {total_rows:,}")
    print(f"Rows with PII Detected:  {pii_count:,} ({pii_pct:.2f}%)")
    print(f"Clean Rows without PII:  {total_rows - pii_count:,}")
    print("\nDetected PII Types Breakdown:")
    if type_counts:
        for pii_type, count in type_counts.most_common():
            print(f"  - [{pii_type}]: {count:,} occurrences")
    else:
        print("  - No PII patterns detected.")

    print(f"\nPrivacy-safe dataset saved to:\n  {out_file}")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(
        description="Run PII detection and redaction on CustomerVoice AI reviews."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=str(PROJECT_ROOT / "data" / "processed" / "reviews_cleaned.csv"),
        help="Input CSV path (default: data/processed/reviews_cleaned.csv)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=str(PROJECT_ROOT / "data" / "processed" / "reviews_pii_safe.csv"),
        help="Output CSV path (default: data/processed/reviews_pii_safe.csv)",
    )

    args = parser.parse_args()
    run_redaction(args.input, args.output)


if __name__ == "__main__":
    main()
