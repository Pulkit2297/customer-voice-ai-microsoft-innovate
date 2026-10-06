"""Dataset adapters for importing external customer feedback sources."""

from src.ingestion.adapters.amazon_adapter import load_amazon_fasttext
from src.ingestion.adapters.sentiment140_adapter import load_sentiment140_csv

__all__ = ["load_amazon_fasttext", "load_sentiment140_csv"]
