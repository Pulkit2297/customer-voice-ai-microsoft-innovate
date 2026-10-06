"""Customer review ingestion and validation module for CustomerVoice AI.

Provides functionality to load, validate, report statistics on, and clean
customer review CSV datasets.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd

from src.ingestion.schema import (
    ALL_SCHEMA_COLUMNS,
    OPTIONAL_COLUMNS,
    REQUIRED_COLUMNS,
    EmptyDatasetError,
    SchemaValidationError,
)

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


@dataclass
class IngestionReport:
    """Summary of dataset ingestion, schema validation, and data quality checks."""

    file_path: str
    total_raw_rows: int = 0
    total_raw_columns: int = 0
    present_columns: List[str] = field(default_factory=list)
    missing_required_columns: List[str] = field(default_factory=list)
    missing_optional_columns: List[str] = field(default_factory=list)
    missing_values_per_column: Dict[str, int] = field(default_factory=dict)
    duplicate_rows_count: int = 0
    duplicate_id_count: int = 0
    clean_rows_count: int = 0

    def print_summary(self) -> None:
        """Print human-readable summary of ingestion metrics."""
        print("=" * 60)
        print(f"CustomerVoice AI - Ingestion Report: {self.file_path}")
        print("=" * 60)
        print(f"Raw Row Count: {self.total_raw_rows}")
        print(f"Raw Column Count: {self.total_raw_columns}")
        print(f"Present Columns: {', '.join(self.present_columns)}")

        if self.missing_required_columns:
            print(f"MISSING REQUIRED COLUMNS: {', '.join(self.missing_required_columns)}")
        else:
            print("Required Columns Validation: PASSED")

        if self.missing_optional_columns:
            print(f"Missing Optional Columns: {', '.join(self.missing_optional_columns)}")

        print("\nMissing Values per Column:")
        for col, count in self.missing_values_per_column.items():
            pct = (count / self.total_raw_rows * 100) if self.total_raw_rows > 0 else 0
            print(f"  - {col}: {count} ({pct:.2f}%)")

        print(f"\nExact Duplicate Rows: {self.duplicate_rows_count}")
        print(f"Duplicate 'review_id' Rows: {self.duplicate_id_count}")
        print(f"Final Cleaned Row Count: {self.clean_rows_count}")
        print("=" * 60)


class ReviewLoader:
    """Loader and validator for review datasets."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.last_report: Optional[IngestionReport] = None

    def load(
        self,
        csv_path: Union[str, Path],
        drop_duplicates: bool = True,
        dedup_subset: Optional[List[str]] = None,
        assign_defaults: bool = False,
        chunksize: Optional[int] = None,
    ) -> pd.DataFrame:
        """Load, validate, report on, and clean a customer reviews CSV file.

        Args:
            csv_path: Path to the input CSV file.
            drop_duplicates: Whether to drop duplicate rows in the cleaned DataFrame.
            dedup_subset: Specific columns to evaluate for deduplication. Defaults to ['review_id'].
            assign_defaults: Whether to populate missing optional schema fields with standard defaults ('unknown' / None).
            chunksize: Optional row chunk size for memory-efficient loading of large datasets.

        Returns:
            Cleaned and validated pandas DataFrame.

        Raises:
            FileNotFoundError: If the CSV file does not exist.
            EmptyDatasetError: If the file is empty (0 bytes or 0 data rows).
            SchemaValidationError: If any required columns are missing.
        """
        path = Path(csv_path).resolve()

        if not path.is_file():
            raise FileNotFoundError(f"Dataset file not found at: {path}")

        # Check for zero-byte empty file
        if path.stat().st_size == 0:
            raise EmptyDatasetError(f"Dataset file is empty (0 bytes): {path}")

        try:
            if chunksize is not None and chunksize > 0:
                chunks = []
                for chunk in pd.read_csv(path, chunksize=chunksize):
                    chunks.append(chunk)
                raw_df = pd.concat(chunks, ignore_index=True)
            else:
                raw_df = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            raise EmptyDatasetError(f"Dataset contains no data/columns: {path}")
        except Exception as e:
            raise IOError(f"Error reading CSV file at {path}: {str(e)}") from e

        if raw_df.empty or len(raw_df) == 0:
            raise EmptyDatasetError(f"Dataset contains 0 rows: {path}")

        # Validate Schema
        present_cols = list(raw_df.columns)
        missing_req = [col for col in REQUIRED_COLUMNS if col not in present_cols]
        missing_opt = [col for col in OPTIONAL_COLUMNS if col not in present_cols]

        # Generate Report Metrics
        raw_rows = len(raw_df)
        raw_cols = len(present_cols)
        missing_vals = raw_df.isnull().sum().to_dict()
        exact_dups = int(raw_df.duplicated().sum())
        id_dups = int(raw_df.duplicated(subset=["review_id"]).sum()) if "review_id" in present_cols else 0

        report = IngestionReport(
            file_path=str(path),
            total_raw_rows=raw_rows,
            total_raw_columns=raw_cols,
            present_columns=present_cols,
            missing_required_columns=missing_req,
            missing_optional_columns=missing_opt,
            missing_values_per_column=missing_vals,
            duplicate_rows_count=exact_dups,
            duplicate_id_count=id_dups,
        )

        logger.info(
            "Ingestion: %s loaded with %d rows, %d columns.",
            path.name,
            raw_rows,
            raw_cols,
        )
        logger.info("Missing values summary: %s", missing_vals)
        logger.info(
            "Duplicate rows: %d exact, %d on review_id",
            exact_dups,
            id_dups,
        )

        # Validate required columns
        if missing_req:
            logger.error(
                "Schema validation failed for %s. Missing required columns: %s",
                path.name,
                missing_req,
            )
            self.last_report = report
            if self.verbose:
                report.print_summary()
            raise SchemaValidationError(
                f"Validation failed. Missing required column(s): {', '.join(missing_req)}"
            )

        if missing_opt:
            logger.warning(
                "Dataset %s is missing optional schema columns: %s",
                path.name,
                missing_opt,
            )

        # Create clean copy (original raw dataset is never modified)
        clean_df = raw_df.copy()

        # Handle duplicates
        if drop_duplicates:
            subset = dedup_subset if dedup_subset is not None else ["review_id"]
            existing_subset = [c for c in subset if c in clean_df.columns]
            if existing_subset:
                clean_df = clean_df.drop_duplicates(subset=existing_subset, keep="first")
            else:
                clean_df = clean_df.drop_duplicates(keep="first")

        # Clean string columns: strip leading/trailing whitespace
        if "review_id" in clean_df.columns:
            clean_df["review_id"] = clean_df["review_id"].astype(str).str.strip()
        if "review_text" in clean_df.columns:
            clean_df["review_text"] = clean_df["review_text"].astype(str).str.strip()

        # Remove rows where required columns are null or empty whitespace
        clean_df = clean_df.dropna(subset=["review_id", "review_text"])
        clean_df = clean_df[
            (clean_df["review_id"] != "")
            & (clean_df["review_text"] != "")
            & (clean_df["review_text"].str.lower() != "nan")
        ]

        # Handle optional schema columns gracefully without inventing fake values
        if assign_defaults:
            for col in ["product_id", "product_name", "category", "campaign"]:
                if col not in clean_df.columns:
                    clean_df[col] = "unknown"
            for col in ["rating", "review_date", "source"]:
                if col not in clean_df.columns:
                    clean_df[col] = None

        clean_df = clean_df.reset_index(drop=True)
        report.clean_rows_count = len(clean_df)
        self.last_report = report

        if self.verbose:
            report.print_summary()

        return clean_df


def load_reviews(
    csv_path: Union[str, Path],
    drop_duplicates: bool = True,
    dedup_subset: Optional[List[str]] = None,
    verbose: bool = True,
    assign_defaults: bool = False,
    chunksize: Optional[int] = None,
) -> pd.DataFrame:
    """Convenience function to load and validate customer reviews.

    Args:
        csv_path: Path to the input review CSV file.
        drop_duplicates: Whether to remove duplicate rows.
        dedup_subset: Columns to consider for deduplication. Defaults to ['review_id'].
        verbose: If True, prints formatted validation and metrics report.
        assign_defaults: Whether to populate missing optional schema fields with standard defaults.
        chunksize: Optional row chunk size for memory-efficient loading of large datasets.

    Returns:
        Cleaned pandas DataFrame.
    """
    loader = ReviewLoader(verbose=verbose)
    return loader.load(
        csv_path=csv_path,
        drop_duplicates=drop_duplicates,
        dedup_subset=dedup_subset,
        assign_defaults=assign_defaults,
        chunksize=chunksize,
    )


def save_processed_reviews(
    df: pd.DataFrame,
    filename: str = "cleaned_reviews.csv",
    processed_dir: Optional[Union[str, Path]] = None,
) -> Path:
    """Save cleaned DataFrame strictly into the data/processed directory.

    Args:
        df: Cleaned reviews DataFrame to save.
        filename: Destination filename (e.g. 'cleaned_reviews.csv' or 'cleaned_reviews.parquet').
        processed_dir: Optional override directory, must be within data/processed/.

    Returns:
        Path to the saved file.

    Raises:
        ValueError: If destination path is outside data/processed/.
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    default_processed_dir = project_root / "data" / "processed"

    target_dir = Path(processed_dir).resolve() if processed_dir else default_processed_dir.resolve()

    # Enforce constraint: must be saved under data/processed/
    try:
        target_dir.relative_to(default_processed_dir)
    except ValueError as e:
        raise ValueError(
            f"Processed data can only be saved under {default_processed_dir}, got: {target_dir}"
        ) from e

    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / filename

    if str(filename).endswith(".parquet"):
        df.to_parquet(target_file, index=False)
    else:
        df.to_csv(target_file, index=False)

    logger.info("Saved processed dataset (%d rows) to %s", len(df), target_file)
    return target_file
