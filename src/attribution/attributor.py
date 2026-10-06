"""Product and campaign attribution engine for CustomerVoice AI.

Associates each customer review with product metadata, product categories, and marketing
campaigns based strictly on authentic dataset metadata without inventing or hallucinating values.
Explicitly marks unassociated reviews with 'unknown'.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

UNKNOWN_VALUE: str = "unknown"

ATTRIBUTION_COLUMNS: List[str] = [
    "product_id",
    "product_name",
    "category",
    "campaign",
]


class AttributionValidationError(ValueError):
    """Raised when attribution integrity or validation constraints fail."""

    pass


def normalize_metadata_value(val: Any) -> str:
    """Normalize metadata value, strictly mapping nulls/empty values to 'unknown'.

    Does not invent, guess, or extrapolate values.
    """
    if val is None or pd.isna(val):
        return UNKNOWN_VALUE

    val_str = str(val).strip()
    if val_str == "" or val_str.lower() in {"nan", "none", "null", "n/a", "unknown"}:
        return UNKNOWN_VALUE

    return val_str


class ReviewAttributor:
    """Attribution processor for associating reviews with products and campaigns."""

    def __init__(self, null_as_none: bool = False):
        self.null_as_none = null_as_none

    def attribute_dataframe(
        self,
        df: pd.DataFrame,
        null_as_none: Optional[bool] = None,
    ) -> pd.DataFrame:
        """Process DataFrame to standardize product, category, and campaign attribution.

        Guarantees:
        1. Preserves all input rows (no data silently discarded).
        2. Normalizes missing/null metadata to 'unknown' (or None if null_as_none=True).
        3. Preserves 'segment' if present.
        4. Appends explicit product_attribution_status and campaign_attribution_status.

        Args:
            df: Input customer reviews DataFrame.
            null_as_none: If True, missing metadata is stored as None (NULL). Defaults to self.null_as_none.

        Returns:
            New DataFrame enriched with standardized attribution attributes.
        """
        if df is None:
            return pd.DataFrame()

        initial_row_count = len(df)
        attributed_df = df.copy(deep=True)
        use_null_as_none = self.null_as_none if null_as_none is None else null_as_none

        # Ensure all attribution metadata columns exist
        for col in ATTRIBUTION_COLUMNS:
            if col not in attributed_df.columns:
                attributed_df[col] = None if use_null_as_none else UNKNOWN_VALUE
            else:
                if use_null_as_none:
                    attributed_df[col] = attributed_df[col].apply(
                        lambda v: None if (v is None or pd.isna(v) or str(v).strip() in {"", "nan", "none", "null", "unknown"}) else str(v).strip()
                    )
                else:
                    attributed_df[col] = attributed_df[col].apply(normalize_metadata_value)

        # Compute explicit attribution statuses
        if use_null_as_none:
            is_product_known = attributed_df["product_id"].notna() | attributed_df["product_name"].notna()
            is_campaign_known = attributed_df["campaign"].notna()
        else:
            is_product_known = (attributed_df["product_id"] != UNKNOWN_VALUE) | (
                attributed_df["product_name"] != UNKNOWN_VALUE
            )
            is_campaign_known = attributed_df["campaign"] != UNKNOWN_VALUE

        attributed_df["product_attribution_status"] = np.where(
            is_product_known, "attributed", "unattributed"
        )
        attributed_df["campaign_attribution_status"] = np.where(
            is_campaign_known, "attributed", "unattributed"
        )

        # Overall attribution status
        attributed_df["attribution_status"] = np.where(
            is_product_known & is_campaign_known,
            "fully_attributed",
            np.where(
                is_product_known | is_campaign_known,
                "partially_attributed",
                "unattributed",
            ),
        )

        # Run validation checks
        self.validate_attribution(
            attributed_df,
            expected_row_count=initial_row_count,
            allow_nulls=use_null_as_none,
        )

        logger.info(
            "Attribution complete: %d reviews processed (%d fully, %d partially, %d unattributed).",
            len(attributed_df),
            int((attributed_df["attribution_status"] == "fully_attributed").sum()),
            int((attributed_df["attribution_status"] == "partially_attributed").sum()),
            int((attributed_df["attribution_status"] == "unattributed").sum()),
        )

        return attributed_df

    @staticmethod
    def validate_attribution(
        df: pd.DataFrame,
        expected_row_count: Optional[int] = None,
        allow_nulls: bool = False,
    ) -> Dict[str, Any]:
        """Perform validation checks on attributed DataFrame.

        Checks:
        1. No rows were discarded (row count matches expected).
        2. Every review has a valid product_attribution_status.
        3. No raw NaNs or unhandled nulls remain in metadata columns (unless allow_nulls=True).
        4. Unknown or null values are explicitly marked.

        Args:
            df: Attributed DataFrame to validate.
            expected_row_count: Expected number of rows before attribution.
            allow_nulls: If True, allows None/null for unattributed business metadata.

        Returns:
            Summary dictionary of validation metrics.

        Raises:
            AttributionValidationError: If any validation rule is violated.
        """
        if df is None:
            raise AttributionValidationError("Cannot validate None DataFrame.")

        current_count = len(df)

        # Check 1: No data silently discarded
        if expected_row_count is not None and current_count != expected_row_count:
            raise AttributionValidationError(
                f"Data loss detected! Initial rows: {expected_row_count}, "
                f"Current rows: {current_count}. Discarded: {expected_row_count - current_count}"
            )

        # Check 2: Every review has a product attribution status
        if "product_attribution_status" not in df.columns:
            raise AttributionValidationError(
                "Missing required column: 'product_attribution_status'"
            )

        invalid_prod_status = df["product_attribution_status"].isna() | (
            df["product_attribution_status"] == ""
        )
        if invalid_prod_status.any():
            raise AttributionValidationError(
                f"{invalid_prod_status.sum()} reviews have invalid product attribution status."
            )

        # Check 3: Check unhandled NaNs in attribution fields
        if not allow_nulls:
            for col in ATTRIBUTION_COLUMNS:
                nan_count = df[col].isna().sum()
                if nan_count > 0:
                    raise AttributionValidationError(
                        f"Column '{col}' contains {nan_count} unhandled NaN/null values. "
                        "All missing values must be explicitly marked as 'unknown'."
                    )

        prod_attr_count = int((df["product_attribution_status"] == "attributed").sum())
        camp_attr_count = int((df["campaign_attribution_status"] == "attributed").sum())
        full_attr_count = int((df["attribution_status"] == "fully_attributed").sum())
        part_attr_count = int((df["attribution_status"] == "partially_attributed").sum())
        unattr_count = int((df["attribution_status"] == "unattributed").sum())

        return {
            "total_reviews": current_count,
            "product_attributed": prod_attr_count,
            "product_unattributed": current_count - prod_attr_count,
            "campaign_attributed": camp_attr_count,
            "campaign_unattributed": current_count - camp_attr_count,
            "fully_attributed": full_attr_count,
            "partially_attributed": part_attr_count,
            "unattributed": unattr_count,
            "data_discarded": 0,
            "validation_passed": True,
        }


def attribute_reviews_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Convenience function to attribute product and campaign metadata."""
    attributor = ReviewAttributor()
    return attributor.attribute_dataframe(df)
