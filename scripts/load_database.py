"""Database ETL loader script for CustomerVoice AI.

Loads processed analytical datasets from CSV artifacts into PostgreSQL:
- Products Dimension (from reviews_attributed.csv)
- Reviews Fact Table (from reviews_attributed.csv)
- Sentiment Results (from reviews_attributed.csv)
- Review Topics Bridge (from reviews_attributed.csv)
- Alerts Table (from alerts.csv)
- Model Evaluation Metrics Table (from model_metrics.csv)

Credentials are never hardcoded and are read dynamically from DATABASE_URL.
"""

import argparse
import json
import logging
from pathlib import Path
import sys
from typing import Optional, Tuple
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import settings
from src.database.connection import Base, mask_database_url, normalize_database_url
from src.database.data_quality import validate_data_quality
from src.database.models import (
    AlertModel,
    ModelMetricModel,
    Product,
    Review,
    ReviewTopic,
    SentimentResultModel,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("load_database")

TupleCounts = Tuple[int, int, int, int]


def load_products_and_reviews(session: Session, reviews_file: Path) -> TupleCounts:

    """Load products, reviews, sentiment results, and topics from reviews_attributed.csv."""
    if not reviews_file.is_file():
        logger.warning("Reviews file not found at %s. Skipping reviews loading.", reviews_file)
        return (0, 0, 0, 0)

    df = pd.read_csv(reviews_file)
    logger.info("Processing %d reviews from %s", len(df), reviews_file.name)

    # 1. Upsert Products Dimension
    valid_products = df[df["product_id"].notna() & (df["product_id"] != "") & (df["product_id"].astype(str).str.lower() != "nan")]
    product_records = valid_products[["product_id", "product_name", "category"]].drop_duplicates(subset=["product_id"])
    products_loaded = 0
    for _, row in product_records.iterrows():
        pid = str(row["product_id"]).strip()
        if not pid or pid.lower() in {"nan", "none", "unknown"}:
            continue
        pname = str(row["product_name"]).strip() if pd.notna(row["product_name"]) else "unknown"
        pcat = str(row["category"]).strip() if pd.notna(row["category"]) else "unknown"

        existing = session.get(Product, pid)
        if not existing:
            session.add(Product(product_id=pid, product_name=pname, category=pcat))
            products_loaded += 1
    session.flush()

    # 2. Upsert Reviews, Sentiment, and Topics
    existing_rev_ids = set(session.scalars(select(Review.review_id)).all())
    reviews_loaded = 0
    sentiment_loaded = 0
    topics_loaded = 0

    for idx, row in df.iterrows():
        rid = str(row["review_id"]).strip()
        if rid in existing_rev_ids:
            continue  # Idempotent skip

        # Date parsing
        r_date = None
        if "review_date" in row and pd.notna(row["review_date"]):
            try:
                r_date = pd.to_datetime(row["review_date"]).date()
            except Exception:
                r_date = None

        rating_val = float(row["rating"]) if ("rating" in row and pd.notna(row["rating"])) else None
        
        pid_val = None
        if "product_id" in row and pd.notna(row["product_id"]):
            raw_pid = str(row["product_id"]).strip()
            if raw_pid and raw_pid.lower() not in {"nan", "none", "unknown", ""}:
                pid_val = raw_pid

        rev = Review(
            review_id=rid,
            review_text=str(row.get("review_text", "")),
            cleaned_text=str(row.get("cleaned_text", "")),
            rating=rating_val,
            review_date=r_date,
            product_id=pid_val,
            campaign=str(row["campaign"]) if ("campaign" in row and pd.notna(row["campaign"])) else None,
            source=str(row["source"]) if ("source" in row and pd.notna(row["source"])) else None,
            pii_detected=bool(row.get("pii_detected", False)),
            pii_types=str(row["pii_types"]) if ("pii_types" in row and pd.notna(row["pii_types"])) else None,
        )
        session.add(rev)
        reviews_loaded += 1

        # Sentiment Result
        if "sentiment" in row and pd.notna(row["sentiment"]):
            sent_res = SentimentResultModel(
                review_id=rid,
                sentiment=str(row["sentiment"]),
                sentiment_score=float(row.get("sentiment_score", 0.0)),
                confidence=float(row.get("confidence", 0.0)),
                model_name=str(row.get("model_name", "VADER-Baseline")),
                model_version=str(row.get("model_version", "3.3.2")),
            )
            session.add(sent_res)
            sentiment_loaded += 1

        # Topics
        primary_top = str(row["primary_topic"]).strip() if ("primary_topic" in row and pd.notna(row["primary_topic"])) else None
        topic_str = str(row["topics"]) if ("topics" in row and pd.notna(row["topics"])) else ""

        # Parse confidence dict if available
        conf_dict = {}
        if "topic_confidence" in row and pd.notna(row["topic_confidence"]):
            try:
                conf_dict = json.loads(str(row["topic_confidence"]))
            except Exception:
                conf_dict = {}

        if topic_str and topic_str.lower() not in {"nan", "none"}:
            for t in topic_str.split(","):
                t_clean = t.strip()
                if t_clean:
                    is_prim = (t_clean == primary_top)
                    t_conf = float(conf_dict.get(t_clean, 1.0))
                    rt = ReviewTopic(
                        review_id=rid,
                        topic=t_clean,
                        topic_confidence=t_conf,
                        is_primary=is_prim,
                    )
                    session.add(rt)
                    topics_loaded += 1

        if reviews_loaded % 1000 == 0:
            session.flush()

    session.flush()
    return (products_loaded, reviews_loaded, sentiment_loaded, topics_loaded)


def load_alerts(session: Session, alerts_file: Path) -> int:
    """Load operational alerts into the alerts table."""
    if not alerts_file.is_file():
        logger.warning("Alerts file not found at %s. Skipping alerts loading.", alerts_file)
        return 0

    df = pd.read_csv(alerts_file)
    logger.info("Processing %d alerts from %s", len(df), alerts_file.name)
    alerts_loaded = 0

    for _, row in df.iterrows():
        aid = str(row["alert_id"]).strip()
        existing = session.get(AlertModel, aid)
        if existing:
            continue

        created_dt = None
        if "created_at" in row and pd.notna(row["created_at"]):
            try:
                created_dt = pd.to_datetime(row["created_at"])
            except Exception:
                created_dt = None

        alert = AlertModel(
            alert_id=aid,
            alert_type=str(row.get("alert_type", "UNKNOWN")),
            severity=str(row.get("severity", "MEDIUM")),
            product=str(row.get("product", "all")),
            topic=str(row.get("topic", "all")),
            metric=str(row.get("metric", "")),
            previous_value=float(row.get("previous_value", 0.0)),
            current_value=float(row.get("current_value", 0.0)),
            percentage_change=float(row.get("percentage_change", 0.0)),
            message=str(row.get("message", "")),
            created_at=created_dt,
            status=str(row.get("status", "ACTIVE")),
        )
        session.add(alert)
        alerts_loaded += 1

    session.flush()
    return alerts_loaded


def load_model_metrics(session: Session, metrics_file: Path) -> int:
    """Load evaluation benchmark metrics into model_metrics table."""
    if not metrics_file.is_file():
        logger.warning("Metrics file not found at %s. Skipping metrics loading.", metrics_file)
        return 0

    df = pd.read_csv(metrics_file)
    logger.info("Processing %d model metrics from %s", len(df), metrics_file.name)
    metrics_loaded = 0

    for _, row in df.iterrows():
        eval_dt = None
        if "evaluation_timestamp" in row and pd.notna(row["evaluation_timestamp"]):
            try:
                eval_dt = pd.to_datetime(row["evaluation_timestamp"])
            except Exception:
                eval_dt = None

        m = ModelMetricModel(
            evaluation_type=str(row.get("evaluation_type", "")),
            category=str(row.get("category", "")),
            metric_name=str(row.get("metric_name", "")),
            metric_value=float(row.get("metric_value", 0.0)),
            validation_sample_size=int(row.get("validation_sample_size", 0)),
            evaluation_timestamp=eval_dt,
        )
        session.add(m)
        metrics_loaded += 1

    session.flush()
    return metrics_loaded


def run_etl(database_url: Optional[str] = None) -> None:
    """Execute complete database ETL."""
    raw_url = database_url or settings.DATABASE_URL
    db_url = normalize_database_url(raw_url)
    masked_url = mask_database_url(db_url)
    logger.info("Connecting to database: %s", masked_url)

    connect_args = {}
    if "postgres" in db_url:
        connect_args["connect_timeout"] = 5
    elif db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    try:
        custom_engine = create_engine(db_url, pool_pre_ping=True, connect_args=connect_args)
        # Test connection
        with custom_engine.connect() as conn:
            pass
    except Exception as e:
        logger.error(
            "Could not connect to database (%s): %s\n"
            "Please ensure database service is active or configure DATABASE_URL in .env.",
            masked_url,
            e,
        )
        sys.exit(1)

    data_dir = PROJECT_ROOT / "data" / "processed"
    reviews_file = data_dir / "reviews_attributed.csv"
    alerts_file = data_dir / "alerts.csv"
    metrics_file = data_dir / "model_metrics.csv"
    quality_report_path = data_dir / "data_quality_report.json"

    # Run Data Quality Validation Gate
    if reviews_file.is_file():
        logger.info("Executing Data Quality Validation Gate on %s...", reviews_file.name)
        report = validate_data_quality(
            df_or_path=reviews_file,
            output_report_path=quality_report_path,
        )
        if report["quality_status"] == "FAILED":
            logger.error(
                "Data Quality Gate FAILED. Ingestion aborted. Details: %s",
                report["invalid_values"],
            )
            sys.exit(1)
        elif report["quality_status"] == "WARNING":
            logger.warning("Data Quality Gate PASSED with WARNING: %s", report["limitations"])
        else:
            logger.info("Data Quality Gate PASSED successfully.")

    # Create tables if not present
    Base.metadata.create_all(bind=custom_engine)
    logger.info("Verified all database table schemas and indexes.")

    with Session(bind=custom_engine) as session:
        try:
            prods, revs, sents, tops = load_products_and_reviews(session, reviews_file)
            alrts = load_alerts(session, alerts_file)
            mtrcs = load_model_metrics(session, metrics_file)

            session.commit()

            logger.info("=" * 65)
            logger.info("CustomerVoice AI - Database Load Summary:")
            logger.info("=" * 65)
            logger.info("  Products Dimension Loaded:      %d", prods)
            logger.info("  Reviews Fact Table Loaded:      %d", revs)
            logger.info("  Sentiment Results Loaded:       %d", sents)
            logger.info("  Topics Bridge Table Loaded:     %d", tops)
            logger.info("  Operational Alerts Loaded:      %d", alrts)
            logger.info("  Model Metrics Loaded:           %d", mtrcs)
            logger.info("=" * 65)
            logger.info("ETL pipeline successfully committed.")

        except Exception as e:
            session.rollback()
            logger.error("ETL pipeline failed during execution: %s", e)
            raise




def main():
    parser = argparse.ArgumentParser(
        description="Load CustomerVoice AI processed data into PostgreSQL."
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Optional database connection URL override (defaults to DATABASE_URL in .env)",
    )
    args = parser.parse_args()
    run_etl(database_url=args.db_url)


if __name__ == "__main__":
    main()
