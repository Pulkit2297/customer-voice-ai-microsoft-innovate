"""SQLAlchemy ORM models for CustomerVoice AI analytical layer.

Defines schemas and relational models for:
- products
- reviews
- sentiment_results
- topics
- alerts
- model_metrics

Includes explicit indexing on commonly queried analytical dimensions:
review_date, product_id, sentiment, and topic.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from src.database.connection import Base


class Product(Base):
    """Product entity dimension table."""

    __tablename__ = "products"

    product_id = Column(String(100), primary_key=True, index=True)
    product_name = Column(String(255), nullable=False, default="unknown")
    category = Column(String(100), nullable=False, default="unknown", index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    reviews = relationship("Review", back_populates="product", cascade="all, delete-orphan")


class Review(Base):
    """Customer review transactional fact table."""

    __tablename__ = "reviews"

    review_id = Column(String(100), primary_key=True, index=True)
    review_text = Column(Text, nullable=False)
    cleaned_text = Column(Text, nullable=False)
    rating = Column(Float, nullable=True)
    review_date = Column(Date, nullable=True, index=True)  # Indexed for temporal queries
    product_id = Column(
        String(100),
        ForeignKey("products.product_id", ondelete="SET NULL"),
        nullable=True,
        index=True,  # Indexed for product queries
    )
    campaign = Column(String(100), nullable=True, index=True)
    source = Column(String(100), nullable=True)
    pii_detected = Column(Boolean, default=False)
    pii_types = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    product = relationship("Product", back_populates="reviews")
    sentiment_result = relationship(
        "SentimentResultModel",
        back_populates="review",
        uselist=False,
        cascade="all, delete-orphan",
    )
    topics = relationship(
        "ReviewTopic",
        back_populates="review",
        cascade="all, delete-orphan",
    )


class SentimentResultModel(Base):
    """Sentiment classification results associated with reviews."""

    __tablename__ = "sentiment_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(
        String(100),
        ForeignKey("reviews.review_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    sentiment = Column(String(20), nullable=False, index=True)  # Indexed for sentiment filtering
    sentiment_score = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    review = relationship("Review", back_populates="sentiment_result")


class ReviewTopic(Base):
    """Multi-label topic assignments bridge table."""

    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(
        String(100),
        ForeignKey("reviews.review_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic = Column(String(100), nullable=False, index=True)  # Indexed for topic slicing
    topic_confidence = Column(Float, nullable=False, default=1.0)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    review = relationship("Review", back_populates="topics")

    __table_args__ = (
        Index("ix_topics_review_topic", "review_id", "topic", unique=True),
    )


class AlertModel(Base):
    """Operational complaint and metric alerts table."""

    __tablename__ = "alerts"

    alert_id = Column(String(100), primary_key=True, index=True)
    alert_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    product = Column(String(100), nullable=False)
    topic = Column(String(100), nullable=False, index=True)  # Indexed
    metric = Column(String(100), nullable=False)
    previous_value = Column(Float, nullable=False)
    current_value = Column(Float, nullable=False)
    percentage_change = Column(Float, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    status = Column(String(50), nullable=False, default="ACTIVE", index=True)


class ModelMetricModel(Base):
    """Model evaluation and benchmarking performance metrics."""

    __tablename__ = "model_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    evaluation_type = Column(String(50), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    validation_sample_size = Column(Integer, nullable=False)
    evaluation_timestamp = Column(DateTime(timezone=True), nullable=False)
