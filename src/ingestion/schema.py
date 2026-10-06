"""Review dataset schema definitions for CustomerVoice AI.

Defines required and optional fields for customer review ingestion.
"""

from typing import List, Set


# Required columns that MUST exist in any ingested review dataset
REQUIRED_COLUMNS: List[str] = [
    "review_id",
    "review_text",
]

# Optional columns that provide rich contextual attributes
OPTIONAL_COLUMNS: List[str] = [
    "rating",
    "rating_source",
    "sentiment_proxy_rating",
    "review_date",
    "product_id",
    "product_name",
    "category",
    "segment",
    "campaign",
    "source",
]

# Combined list of all known schema columns
ALL_SCHEMA_COLUMNS: List[str] = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

REQUIRED_COLUMNS_SET: Set[str] = set(REQUIRED_COLUMNS)
OPTIONAL_COLUMNS_SET: Set[str] = set(OPTIONAL_COLUMNS)
ALL_SCHEMA_COLUMNS_SET: Set[str] = set(ALL_SCHEMA_COLUMNS)


class SchemaValidationError(ValueError):
    """Raised when a dataset fails schema validation (e.g., missing required columns)."""

    pass


class EmptyDatasetError(ValueError):
    """Raised when an ingested dataset contains no rows or is empty."""

    pass
