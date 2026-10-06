"""Unit tests for Phase 10: PostgreSQL Database Analytics Layer."""

from datetime import date, datetime, timezone
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from src.database.connection import Base
from src.database.models import (
    AlertModel,
    ModelMetricModel,
    Product,
    Review,
    ReviewTopic,
    SentimentResultModel,
)


@pytest.fixture
def in_memory_db():
    """Fixture providing an isolated in-memory SQLite database for schema testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    with Session(bind=engine) as session:
        yield session
    Base.metadata.drop_all(bind=engine)


def test_tables_created(in_memory_db: Session):
    """Verify that all 6 required analytical tables exist in schema."""
    engine = in_memory_db.get_bind()
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    expected_tables = {
        "products",
        "reviews",
        "sentiment_results",
        "topics",
        "alerts",
        "model_metrics",
    }
    assert expected_tables.issubset(table_names)


def test_required_indexes_exist(in_memory_db: Session):
    """Verify indexes on review_date, product_id, sentiment, and topic."""
    engine = in_memory_db.get_bind()
    inspector = inspect(engine)

    # 1. Indexes on reviews table (review_date, product_id)
    review_indexes = {idx["name"] for idx in inspector.get_indexes("reviews")}
    assert "ix_reviews_review_date" in review_indexes
    assert "ix_reviews_product_id" in review_indexes

    # 2. Indexes on sentiment_results table (sentiment)
    sentiment_indexes = {idx["name"] for idx in inspector.get_indexes("sentiment_results")}
    assert "ix_sentiment_results_sentiment" in sentiment_indexes

    # 3. Indexes on topics table (topic)
    topic_indexes = {idx["name"] for idx in inspector.get_indexes("topics")}
    assert "ix_topics_topic" in topic_indexes


def test_insert_review_with_relationships(in_memory_db: Session):
    """Verify end-to-end relational insert across Product, Review, Sentiment, and Topics."""
    # 1. Add product
    product = Product(
        product_id="PROD_101",
        product_name="Kindle Oasis",
        category="E-Readers",
    )
    in_memory_db.add(product)
    in_memory_db.commit()

    # 2. Add review
    review = Review(
        review_id="REV_999",
        review_text="Terrific screen contrast and battery life!",
        cleaned_text="Terrific screen contrast and battery life!",
        rating=5.0,
        review_date=date(2023, 10, 1),
        product_id="PROD_101",
        campaign="Fall_Launch",
        source="Website",
    )
    in_memory_db.add(review)
    in_memory_db.commit()

    # 3. Add sentiment result
    sentiment = SentimentResultModel(
        review_id="REV_999",
        sentiment="positive",
        sentiment_score=0.85,
        confidence=0.85,
        model_name="VADER-Baseline",
        model_version="3.3.2",
    )
    in_memory_db.add(sentiment)

    # 4. Add topic
    topic = ReviewTopic(
        review_id="REV_999",
        topic="battery",
        topic_confidence=0.85,
        is_primary=True,
    )
    in_memory_db.add(topic)
    in_memory_db.commit()

    # Query back and verify navigation
    queried_rev = in_memory_db.get(Review, "REV_999")
    assert queried_rev is not None
    assert queried_rev.product.product_name == "Kindle Oasis"
    assert queried_rev.sentiment_result.sentiment == "positive"
    assert len(queried_rev.topics) == 1
    assert queried_rev.topics[0].topic == "battery"


def test_insert_alert(in_memory_db: Session):
    """Verify alert persistence in alerts table."""
    alert = AlertModel(
        alert_id="ALT_12345678",
        alert_type="NEGATIVE_SENTIMENT_SURGE",
        severity="HIGH",
        product="Kindle",
        topic="battery",
        metric="negative_sentiment_pct",
        previous_value=15.0,
        current_value=45.0,
        percentage_change=200.0,
        message="Critical negative sentiment surge detected.",
        created_at=datetime.now(timezone.utc),
        status="ACTIVE",
    )
    in_memory_db.add(alert)
    in_memory_db.commit()

    queried_alert = in_memory_db.get(AlertModel, "ALT_12345678")
    assert queried_alert is not None
    assert queried_alert.severity == "HIGH"
    assert queried_alert.status == "ACTIVE"


def test_insert_model_metrics(in_memory_db: Session):
    """Verify model metrics insertion."""
    metric = ModelMetricModel(
        evaluation_type="sentiment",
        category="overall",
        metric_name="accuracy",
        metric_value=0.875,
        validation_sample_size=100,
        evaluation_timestamp=datetime.now(timezone.utc),
    )
    in_memory_db.add(metric)
    in_memory_db.commit()

    saved = in_memory_db.query(ModelMetricModel).filter_by(metric_name="accuracy").first()
    assert saved is not None
    assert saved.metric_value == 0.875
