"""Dataset inspection script for CustomerVoice AI.

Accepts a CSV path and displays:
- Number of rows
- Number of columns
- Column names
- Missing values per column
- Duplicate count
- Sample rows
- Data types
"""

import argparse
import sys
from pathlib import Path
import pandas as pd


def inspect_dataset(csv_path: str, sample_size: int = 5) -> None:
    """Inspect a CSV dataset and print comprehensive metadata.

    Args:
        csv_path: Path to the target CSV file.
        sample_size: Number of sample rows to display.
    """
    path = Path(csv_path).resolve()

    if not path.is_file():
        print(f"Error: File not found at '{path}'", file=sys.stderr)
        sys.exit(1)

    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"Error reading CSV file at '{path}': {e}", file=sys.stderr)
        sys.exit(1)

    num_rows, num_cols = df.shape
    columns = list(df.columns)
    missing_per_col = df.isnull().sum()
    duplicate_rows = df.duplicated().sum()

    print("=" * 70)
    print(f"DATASET INSPECTION REPORT: {path.name}")
    print(f"Full Path: {path}")
    print("=" * 70)

    print(f"\n1. Dimensions:")
    print(f"   - Number of rows:    {num_rows:,}")
    print(f"   - Number of columns: {num_cols}")

    print(f"\n2. Column Names ({len(columns)}):")
    for i, col in enumerate(columns, 1):
        print(f"   {i:2d}. {col}")

    print(f"\n3. Data Types:")
    for col, dtype in df.dtypes.items():
        print(f"   - {col:25s}: {dtype}")

    print(f"\n4. Missing Values per Column:")
    for col, count in missing_per_col.items():
        pct = (count / num_rows * 100) if num_rows > 0 else 0.0
        print(f"   - {col:25s}: {count:6d} missing ({pct:5.2f}%)")

    print(f"\n5. Duplicate Count:")
    print(f"   - Total exact duplicate rows: {duplicate_rows:,}")
    if "review_id" in df.columns:
        id_dups = df.duplicated(subset=["review_id"]).sum()
        print(f"   - Duplicate 'review_id' entries: {id_dups:,}")

    print(f"\n6. Sample Rows (First {min(sample_size, num_rows)}):")
    print("-" * 70)
    if num_rows > 0:
        print(df.head(sample_size).to_string())
    else:
        print("   (Dataset is empty - no rows to preview)")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Inspect a customer review CSV dataset for CustomerVoice AI."
    )
    parser.add_argument(
        "csv_path",
        type=str,
        help="Path to the customer review CSV file.",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=5,
        help="Number of preview sample rows to display (default: 5).",
    )
    args = parser.parse_args()

    inspect_dataset(args.csv_path, sample_size=args.samples)


if __name__ == "__main__":
    main()
