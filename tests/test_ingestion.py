"""Unit tests for Phase 1 Customer Review Ingestion pipeline."""

from pathlib import Path
import pandas as pd
import pytest

from src.ingestion.load_reviews import (
    ReviewLoader,
    load_reviews,
    save_processed_reviews,
)
from src.ingestion.schema import (
    EmptyDatasetError,
    REQUIRED_COLUMNS,
    SchemaValidationError,
)


@pytest.fixture
def valid_csv_path(tmp_path: Path) -> Path:
    """Fixture to generate a standard valid review CSV."""
    csv_file = tmp_path / "valid_reviews.csv"
    data = {
        "review_id": ["REV_001", "REV_002", "REV_003"],
        "review_text": [
            "Outstanding service and very fast delivery!",
            "The product stopped working after three days.",
            "Average quality, could be better for the price.",
        ],
        "rating": [5, 1, 3],
        "category": ["Electronics", "Electronics", "Home"],
        "source": ["Amazon", "Website", "Store"],
    }
    df = pd.DataFrame(data)
    df.to_csv(csv_file, index=False)
    return csv_file


@pytest.fixture
def duplicate_csv_path(tmp_path: Path) -> Path:
    """Fixture to generate a CSV with exact duplicates and ID duplicates."""
    csv_file = tmp_path / "duplicates.csv"
    data = {
        "review_id": ["REV_001", "REV_001", "REV_002", "REV_003", "REV_003"],
        "review_text": [
            "Great product!",
            "Great product!",  # exact duplicate
            "Not worth the price.",
            "Love the fast shipping!",
            "Love the fast shipping!",  # duplicate
        ],
        "rating": [5, 5, 2, 5, 5],
    }
    df = pd.DataFrame(data)
    df.to_csv(csv_file, index=False)
    return csv_file


def test_valid_csv(valid_csv_path: Path):
    """Verify that a well-formed CSV is successfully ingested and cleaned."""
    loader = ReviewLoader(verbose=False)
    df = loader.load(valid_csv_path)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    for col in REQUIRED_COLUMNS:
        assert col in df.columns
    assert loader.last_report is not None
    assert loader.last_report.total_raw_rows == 3
    assert len(loader.last_report.missing_required_columns) == 0
    assert loader.last_report.clean_rows_count == 3


def test_missing_review_text(tmp_path: Path):
    """Verify that missing review_text column raises SchemaValidationError."""
    csv_file = tmp_path / "missing_text.csv"
    df = pd.DataFrame({
        "review_id": ["REV_001", "REV_002"],
        "rating": [5, 4],
        "product_name": ["Widget A", "Widget B"],
    })
    df.to_csv(csv_file, index=False)

    loader = ReviewLoader(verbose=False)
    with pytest.raises(SchemaValidationError) as exc_info:
        loader.load(csv_file)

    assert "review_text" in str(exc_info.value)
    assert loader.last_report is not None
    assert "review_text" in loader.last_report.missing_required_columns


def test_missing_review_id(tmp_path: Path):
    """Verify that missing review_id column raises SchemaValidationError."""
    csv_file = tmp_path / "missing_id.csv"
    df = pd.DataFrame({
        "review_text": ["Terrific battery life", "Poor display contrast"],
        "rating": [5, 2],
    })
    df.to_csv(csv_file, index=False)

    loader = ReviewLoader(verbose=False)
    with pytest.raises(SchemaValidationError) as exc_info:
        loader.load(csv_file)

    assert "review_id" in str(exc_info.value)
    assert loader.last_report is not None
    assert "review_id" in loader.last_report.missing_required_columns


def test_duplicate_detection(duplicate_csv_path: Path):
    """Verify that duplicates are detected, reported, and removed from clean DataFrame."""
    loader = ReviewLoader(verbose=False)
    df = loader.load(duplicate_csv_path)

    assert loader.last_report is not None
    assert loader.last_report.total_raw_rows == 5
    assert loader.last_report.duplicate_rows_count >= 2
    assert loader.last_report.duplicate_id_count >= 2

    # Cleaned DataFrame should have deduplicated rows (3 unique reviews)
    assert len(df) == 3
    assert df["review_id"].tolist() == ["REV_001", "REV_002", "REV_003"]


def test_empty_dataset_zero_bytes(tmp_path: Path):
    """Verify that a 0-byte file raises EmptyDatasetError."""
    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("")

    with pytest.raises(EmptyDatasetError):
        load_reviews(empty_file, verbose=False)


def test_empty_dataset_headers_only(tmp_path: Path):
    """Verify that a CSV with headers but zero data rows raises EmptyDatasetError."""
    empty_df_file = tmp_path / "empty_rows.csv"
    df = pd.DataFrame(columns=["review_id", "review_text", "rating"])
    df.to_csv(empty_df_file, index=False)

    with pytest.raises(EmptyDatasetError):
        load_reviews(empty_df_file, verbose=False)


def test_raw_dataset_not_modified(valid_csv_path: Path):
    """Verify that original raw file on disk is not altered in any way."""
    original_mtime = valid_csv_path.stat().st_mtime
    original_size = valid_csv_path.stat().st_size
    original_content = valid_csv_path.read_text()

    # Load and clean
    load_reviews(valid_csv_path, verbose=False)

    assert valid_csv_path.stat().st_mtime == original_mtime
    assert valid_csv_path.stat().st_size == original_size
    assert valid_csv_path.read_text() == original_content


def test_save_processed_reviews_enforces_directory(tmp_path: Path):
    """Verify that save_processed_reviews only saves to data/processed."""
    df = pd.DataFrame({
        "review_id": ["REV_100"],
        "review_text": ["Superb experience!"],
    })

    # Saving to unauthorized directory outside data/processed should raise ValueError
    unauthorized_dir = tmp_path / "forbidden_dir"
    unauthorized_dir.mkdir()

    with pytest.raises(ValueError) as exc_info:
        save_processed_reviews(df, filename="test.csv", processed_dir=unauthorized_dir)

    assert "Processed data can only be saved under" in str(exc_info.value)
