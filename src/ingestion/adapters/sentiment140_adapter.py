"""Sentiment140 Social Reviews Adapter for CustomerVoice AI.

Extracts customer tweets and social feedback from archive/train_data.csv.
Adheres strictly to Data Lineage and Semantic Integrity principles:
- Sentiment140 is an ingestion channel, NOT a product:
  product_id = None
  product_name = None
  category = None
  segment = None
- rating = None (binary sentiment is NOT represented as actual customer rating)
- sentiment_proxy_rating provided as a separate proxy
- rating_source = 'not_available'
- review_date = None (no timestamps in dataset)
- campaign = None (no marketing campaigns in dataset)
- source = 'Twitter/Social'
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pandas as pd

logger = logging.getLogger(__name__)


def load_sentiment140_csv(
    file_path: Union[str, Path],
    max_records: int = 1000,
) -> pd.DataFrame:
    """Read a batch of social commentary from Sentiment140 train_data.csv.

    Args:
        file_path: Path to train_data.csv or test_data.csv.
        max_records: Number of rows to sample.

    Returns:
        DataFrame conforming to ALL_SCHEMA_COLUMNS.
    """
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Sentiment140 CSV not found at: {path}")

    logger.info("Reading %d records from %s", max_records, path.name)
    raw_df = pd.read_csv(path, nrows=max_records)

    records: List[Dict[str, Any]] = []
    count = 0
    for idx, row in raw_df.iterrows():
        sentence = str(row.get("sentence", "")).strip()
        if not sentence or sentence.lower() == "nan":
            continue

        raw_sentiment = int(row.get("sentiment", 1))
        # Proxy rating kept strictly separate from genuine customer rating
        proxy_rating = 5.0 if raw_sentiment == 1 else 1.0

        count += 1
        review_id = f"S140_REV_{count:06d}"

        records.append({
            "review_id": review_id,
            "review_text": sentence,
            "rating": None,  # Genuine rating not available in Sentiment140
            "rating_source": "not_available",
            "sentiment_proxy_rating": proxy_rating,
            "review_date": None,  # Genuine date not available in Sentiment140
            "product_id": None,  # Sentiment140 is NOT a product
            "product_name": None,
            "category": None,
            "segment": None,  # Social media stream has no product segment
            "campaign": None,  # Genuine campaign not available
            "source": "Twitter/Social",
        })

    df = pd.DataFrame(records)
    logger.info("Successfully loaded %d records from %s (product_id=None, segment=None).", len(df), path.name)
    return df
