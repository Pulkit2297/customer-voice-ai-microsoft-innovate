"""Data Quality Validation Gate for CustomerVoice AI.

Validates analytical integrity of processed review datasets before database ingestion:
- Row count > 0
- Unique review IDs (no duplicate IDs)
- Product count check (flags warning/limitation if unique_products <= 1)
- Valid sentiment values ('positive', 'neutral', 'negative')
- Valid topic taxonomy adherence
- Rating values within [1.0, 5.0]
- Valid date formatting
- No unexpected nulls in required analytical fields

Outputs comprehensive quality report in JSON format to:
data/processed/data_quality_report.json
"""

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Set, Union
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.topics.topic_engine import TopicClassifier

logger = logging.getLogger(__name__)

# Required analytical fields that must be present in the dataset
REQUIRED_ANALYTICAL_FIELDS: List[str] = [
    "review_id",
    "review_text",
    "cleaned_text",
    "sentiment",
    "topics",
]

# Approved sentiment classifications
VALID_SENTIMENTS: Set[str] = {"positive", "neutral", "negative"}

DEFAULT_REPORT_PATH = PROJECT_ROOT / "data" / "processed" / "data_quality_report.json"
DEFAULT_INPUT_DATASET = PROJECT_ROOT / "data" / "processed" / "reviews_attributed.csv"


class DataQualityGate:
    """Validation engine for customer feedback data quality assurance."""

    def __init__(self, taxonomy_path: Optional[Union[str, Path]] = None):
        try:
            classifier = TopicClassifier(taxonomy_path=taxonomy_path)
            self.approved_topics = set(classifier.get_supported_topics()) | {"unknown"}
        except Exception as e:
            logger.warning("Could not load taxonomy from classifier: %s. Using default fallback topics.", e)
            self.approved_topics = {
                "product_quality",
                "battery",
                "performance",
                "delivery",
                "customer_support",
                "pricing",
                "refund",
                "return",
                "packaging",
                "usability",
                "features",
                "reliability",
                "unknown",
            }

    def validate(
        self,
        df: Any,
        dataset_name: str = "reviews_attributed.csv",
    ) -> Dict[str, Any]:
        """Perform comprehensive data quality checks on review DataFrame.

        Args:
            df: Input pandas DataFrame to evaluate.
            dataset_name: Name or path identifier of the dataset.

        Returns:
            Dictionary matching the required JSON quality report schema.
        """
        generated_at = datetime.now(timezone.utc).isoformat()
        invalid_values: Dict[str, Any] = {}
        missing_values: Dict[str, int] = {}
        limitations: List[str] = []

        if not isinstance(df, pd.DataFrame):
            return {
                "dataset": str(dataset_name),
                "row_count": 0,
                "unique_reviews": 0,
                "unique_products": 0,
                "missing_values": {},
                "invalid_values": {"input_error": "Provided input is not a pandas DataFrame."},
                "quality_status": "FAILED",
                "limitations": ["Input data invalid."],
                "generated_at": generated_at,
            }

        row_count = len(df)
        if row_count == 0:
            invalid_values["empty_dataset"] = "Dataset contains 0 rows."

        # Missing values across all present columns
        for col in df.columns:
            missing_values[col] = int(df[col].isnull().sum())

        # 1. Verify presence of required analytical fields
        missing_required = [col for col in REQUIRED_ANALYTICAL_FIELDS if col not in df.columns]
        if missing_required:
            invalid_values["missing_required_fields"] = missing_required

        # 2. Check unique review IDs
        unique_reviews = 0
        if "review_id" in df.columns:
            null_ids = int(df["review_id"].isnull().sum())
            if null_ids > 0:
                invalid_values["null_review_id_count"] = null_ids

            unique_reviews = int(df["review_id"].nunique(dropna=False))
            dup_reviews = int(df["review_id"].duplicated().sum())
            if dup_reviews > 0:
                invalid_values["duplicate_reviews"] = dup_reviews

        # 3. Check product count and enforce multi-product comparison limitation
        unique_products = 0
        prod_col = "product_id" if "product_id" in df.columns else ("product" if "product" in df.columns else None)
        if prod_col:
            unique_products = int(df[prod_col].nunique(dropna=True))

        if unique_products <= 1:
            limitation_msg = (
                f"Current dataset contains only {unique_products} product ('unknown'). "
                "Product-level comparison requires ingesting multi-product review data."
            )
            limitations.append(limitation_msg)

        # 4. Check sentiment values
        if "sentiment" in df.columns:
            null_sentiments = int(df["sentiment"].isnull().sum())
            if null_sentiments > 0:
                invalid_values["null_sentiment_count"] = null_sentiments

            non_null_sentiments = df["sentiment"].dropna()
            invalid_sentiments = [
                str(s) for s in non_null_sentiments if str(s).strip().lower() not in VALID_SENTIMENTS
            ]
            if invalid_sentiments:
                invalid_values["invalid_sentiment_count"] = len(invalid_sentiments)
                invalid_values["invalid_sentiment_samples"] = list(set(invalid_sentiments))[:5]

        # 5. Check topic values against taxonomy
        if "topics" in df.columns:
            invalid_topics = []
            for val in df["topics"].dropna():
                val_str = str(val).strip()
                if not val_str or val_str.lower() in {"nan", "none", "{}"}:
                    continue
                # Split comma-separated topics
                parts = [p.strip() for p in val_str.split(",") if p.strip()]
                for p in parts:
                    if p not in self.approved_topics:
                        invalid_topics.append(p)

            if invalid_topics:
                invalid_values["invalid_topic_count"] = len(invalid_topics)
                invalid_values["invalid_topic_samples"] = list(set(invalid_topics))[:5]

        # 6. Check rating range [1.0, 5.0]
        if "rating" in df.columns:
            invalid_ratings = []
            for val in df["rating"].dropna():
                try:
                    num = float(val)
                    if num < 1.0 or num > 5.0 or pd.isna(num):
                        invalid_ratings.append(num)
                except (ValueError, TypeError):
                    invalid_ratings.append(str(val))

            if invalid_ratings:
                invalid_values["invalid_rating_count"] = len(invalid_ratings)
                invalid_values["invalid_rating_samples"] = invalid_ratings[:5]

        # 7. Check date validity
        if "review_date" in df.columns:
            invalid_dates = []
            for val in df["review_date"].dropna():
                val_str = str(val).strip()
                if not val_str or val_str.lower() in {"nan", "none"}:
                    continue
                try:
                    pd.to_datetime(val_str)
                except Exception:
                    invalid_dates.append(val_str)

            if invalid_dates:
                invalid_values["invalid_date_count"] = len(invalid_dates)
                invalid_values["invalid_date_samples"] = invalid_dates[:5]

        # 8. Check unexpected nulls in text fields
        for text_col in ["review_text", "cleaned_text"]:
            if text_col in df.columns:
                null_texts = int(df[text_col].isnull().sum())
                empty_texts = int((df[text_col].astype(str).str.strip() == "").sum()) - null_texts
                if null_texts > 0 or empty_texts > 0:
                    invalid_values[f"missing_{text_col}_count"] = null_texts + max(0, empty_texts)

        # Determine overall quality status
        if invalid_values:
            quality_status = "FAILED"
        elif unique_products <= 1:
            quality_status = "WARNING"
        else:
            quality_status = "PASSED"

        report = {
            "dataset": str(dataset_name),
            "row_count": row_count,
            "unique_reviews": unique_reviews,
            "unique_products": unique_products,
            "missing_values": missing_values,
            "invalid_values": invalid_values,
            "quality_status": quality_status,
            "limitations": limitations,
            "generated_at": generated_at,
        }

        return report

    def validate_file(
        self,
        csv_path: Union[str, Path],
        output_report_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """Validate a CSV file on disk and optionally export the JSON report."""
        path = Path(csv_path).resolve()
        if not path.is_file():
            report = {
                "dataset": str(path),
                "row_count": 0,
                "unique_reviews": 0,
                "unique_products": 0,
                "missing_values": {},
                "invalid_values": {"file_not_found": f"File not found: {path}"},
                "quality_status": "FAILED",
                "limitations": ["Dataset file does not exist."],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            try:
                df = pd.read_csv(path)
                report = self.validate(df, dataset_name=path.name)
            except Exception as e:
                report = {
                    "dataset": str(path),
                    "row_count": 0,
                    "unique_reviews": 0,
                    "unique_products": 0,
                    "missing_values": {},
                    "invalid_values": {"read_error": f"Failed reading CSV: {str(e)}"},
                    "quality_status": "FAILED",
                    "limitations": ["Could not parse dataset."],
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                }

        if output_report_path:
            self.export_report(report, output_report_path)

        return report

    @staticmethod
    def export_report(report: Dict[str, Any], output_path: Union[str, Path]) -> Path:
        """Export quality report dictionary to a JSON file."""
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info("Saved Data Quality Report to: %s", out_file)
        return out_file


def validate_data_quality(
    df_or_path: Union[pd.DataFrame, str, Path],
    dataset_name: Optional[str] = None,
    output_report_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Convenience helper to validate DataFrame or CSV path and return quality report."""
    gate = DataQualityGate()
    if isinstance(df_or_path, pd.DataFrame):
        report = gate.validate(df_or_path, dataset_name=dataset_name or "in_memory_dataframe")
        if output_report_path:
            gate.export_report(report, output_report_path)
        return report
    else:
        return gate.validate_file(df_or_path, output_report_path=output_report_path)


def main():
    parser = argparse.ArgumentParser(
        description="Run Data Quality Validation Gate on CustomerVoice AI datasets."
    )
    parser.add_argument(
        "--input",
        type=str,
        default=str(DEFAULT_INPUT_DATASET),
        help="Path to input reviews CSV (default: data/processed/reviews_attributed.csv)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_REPORT_PATH),
        help="Path to output JSON report (default: data/processed/data_quality_report.json)",
    )
    args = parser.parse_args()

    report = validate_data_quality(
        df_or_path=args.input,
        output_report_path=args.output,
    )

    print("=" * 65)
    print("CustomerVoice AI - Data Quality Validation Report")
    print("=" * 65)
    print(f"Dataset:         {report['dataset']}")
    print(f"Row Count:       {report['row_count']}")
    print(f"Unique Reviews:  {report['unique_reviews']}")
    print(f"Unique Products: {report['unique_products']}")
    print(f"Quality Status:  {report['quality_status']}")
    if report["limitations"]:
        print("\nIdentified Limitations:")
        for lim in report["limitations"]:
            print(f"  - {lim}")
    if report["invalid_values"]:
        print(f"\nInvalid Values ({len(report['invalid_values'])} issues):")
        for k, v in report["invalid_values"].items():
            print(f"  - {k}: {v}")
    print("=" * 65)
    print(f"Detailed JSON report written to: {args.output}")


if __name__ == "__main__":
    main()
