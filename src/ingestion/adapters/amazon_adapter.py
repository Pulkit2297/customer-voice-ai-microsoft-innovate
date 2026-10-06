"""Amazon FastText Review Adapter for CustomerVoice AI.

Parses compressed or plain FastText Amazon customer reviews (.ft.txt.bz2).
Adheres strictly to Data Lineage and Semantic Integrity principles:
- review_date is set to None (no synthetic dates generated)
- rating is set to None (binary sentiment is NOT represented as actual customer rating)
- sentiment_proxy_rating is provided as an explicit separate proxy
- rating_source is set to 'not_available'
- product_id, product_name, and category are set to None (no pseudo-SKUs)
- segment is populated as an explicit 'inferred_category_segment'
- campaign is set to None (no placeholder campaigns)
- source is set to 'Amazon'
"""

import bz2
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd

from src.ingestion.schema import ALL_SCHEMA_COLUMNS

logger = logging.getLogger(__name__)

# Defensible keyword rules for INFERRED CATEGORY SEGMENTS (NOT product SKUs)
CATEGORY_SEGMENT_RULES: List[Tuple[str, str]] = [
    (
        r"\b(battery|batteries|charger|charging|power\s*bank|mah|rechargeable|ac\s*adapter)\b",
        "Power & Battery",
    ),
    (
        r"\b(headphone|headphones|earbud|earbuds|earphones|speaker|speakers|stereo|cd|soundtrack|audio|amplifier|mic|microphone)\b",
        "Audio & Sound",
    ),
    (
        r"\b(dvd|vcr|vhs|tv|television|monitor|player|hdmi|remote|bluray|blu-ray|screen)\b",
        "Video & Display",
    ),
    (
        r"\b(usb|laptop|pc|desktop|hard\s*drive|mouse|keyboard|router|software|motherboard|gpu|cpu|computer|printer|scanner)\b",
        "Computer Hardware",
    ),
    (
        r"\b(book|novel|biography|author|pages|paperback|hardcover|edition|story|reading|chapter)\b",
        "Books & Publications",
    ),
]

DEFAULT_SEGMENT = "General Consumer Goods"


def infer_category_segment(title: str, text: str) -> str:
    """Identify defensible category segment grouping from title and text."""
    combined = f"{title} {text}".lower()
    for pattern, segment_name in CATEGORY_SEGMENT_RULES:
        if re.search(pattern, combined, re.IGNORECASE):
            return segment_name
    return DEFAULT_SEGMENT


def parse_fasttext_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse a single FastText line into structured attributes.

    Format: __label__<1|2> <Title>: <Body>
    """
    line = line.strip()
    if not line:
        return None

    # Match __label__1 or __label__2 followed by title: body
    m = re.match(r"^__label__([12])\s+(?:([^:]+):\s*)?(.*)$", line)
    if not m:
        return None

    label_num, title, body = m.groups()
    title = (title or "").strip()
    body = (body or "").strip()

    if not body:
        body = title
    full_text = f"{title}. {body}" if title and title != body else body

    # Raw sentiment polarity from label
    sentiment = "negative" if label_num == "1" else "positive"
    # Proxy rating kept strictly separate from genuine customer rating
    sentiment_proxy = 1.0 if label_num == "1" else 5.0

    segment = infer_category_segment(title, body)

    return {
        "text": full_text,
        "sentiment": sentiment,
        "sentiment_proxy_rating": sentiment_proxy,
        "segment": segment,
        "rating": None,
        "rating_source": "not_available",
        "review_date": None,
        "product_id": None,
        "product_name": None,
        "category": None,
        "campaign": None,
        "source": "Amazon",
    }


def load_amazon_fasttext(
    file_path: Union[str, Path],
    max_records: int = 5000,
) -> pd.DataFrame:
    """Stream and extract structured reviews from Amazon FastText dataset.

    Enforces data lineage:
    - rating: None (no genuine star rating in source)
    - review_date: None (no genuine timestamp in source)
    - product_id: None (no genuine product SKU in source)
    - product_name: None
    - category: None
    - segment: Inferred category segment
    - campaign: None (no genuine campaign in source)
    - source: 'Amazon'

    Args:
        file_path: Path to .ft.txt.bz2 or .ft.txt file.
        max_records: Maximum number of records to ingest.

    Returns:
        DataFrame conforming to ALL_SCHEMA_COLUMNS.
    """
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Amazon FastText file not found: {path}")

    records: List[Dict[str, Any]] = []

    logger.info("Opening Amazon FastText file: %s (max_records=%d)", path.name, max_records)

    opener = bz2.open if str(path).endswith(".bz2") else open

    count = 0
    with opener(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            parsed = parse_fasttext_line(line)
            if not parsed:
                continue

            count += 1
            review_id = f"AMZ_REV_{count:06d}"

            records.append({
                "review_id": review_id,
                "review_text": parsed["text"],
                "rating": None,  # Genuine rating not available in FastText
                "rating_source": "not_available",
                "sentiment_proxy_rating": parsed["sentiment_proxy_rating"],
                "review_date": None,  # Genuine date not available in FastText
                "product_id": None,  # Genuine SKU not available in FastText
                "product_name": None,
                "category": None,
                "segment": parsed["segment"],  # Explicit inferred category segment
                "campaign": None,  # Genuine campaign not available
                "source": "Amazon",
            })

            if count >= max_records:
                break

    df = pd.DataFrame(records)
    logger.info(
        "Successfully parsed %d Amazon reviews (rating=None, review_date=None, product_id=None, campaign=None, segments=%d).",
        len(df),
        df["segment"].nunique(),
    )
    return df
