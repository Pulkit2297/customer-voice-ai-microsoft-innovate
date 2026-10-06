"""Initial analytics schema with products, reviews, sentiment, topics, alerts, and metrics.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-27 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. products table
    op.create_table(
        "products",
        sa.Column("product_id", sa.String(length=100), primary_key=True),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_products_product_id", "products", ["product_id"])
    op.create_index("ix_products_category", "products", ["category"])

    # 2. reviews table
    op.create_table(
        "reviews",
        sa.Column("review_id", sa.String(length=100), primary_key=True),
        sa.Column("review_text", sa.Text(), nullable=False),
        sa.Column("cleaned_text", sa.Text(), nullable=False),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("review_date", sa.Date(), nullable=True),
        sa.Column("product_id", sa.String(length=100), nullable=True),
        sa.Column("campaign", sa.String(length=100), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("pii_detected", sa.Boolean(), nullable=True, default=False),
        sa.Column("pii_types", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.product_id"], ondelete="SET NULL"),
    )
    op.create_index("ix_reviews_review_id", "reviews", ["review_id"])
    op.create_index("ix_reviews_review_date", "reviews", ["review_date"])  # Required Index
    op.create_index("ix_reviews_product_id", "reviews", ["product_id"])    # Required Index
    op.create_index("ix_reviews_campaign", "reviews", ["campaign"])

    # 3. sentiment_results table
    op.create_table(
        "sentiment_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("review_id", sa.String(length=100), nullable=False),
        sa.Column("sentiment", sa.String(length=20), nullable=False),
        sa.Column("sentiment_score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.review_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_sentiment_results_review_id", "sentiment_results", ["review_id"], unique=True)
    op.create_index("ix_sentiment_results_sentiment", "sentiment_results", ["sentiment"])  # Required Index

    # 4. topics table
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("review_id", sa.String(length=100), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("topic_confidence", sa.Float(), nullable=False, default=1.0),
        sa.Column("is_primary", sa.Boolean(), nullable=True, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.review_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_topics_review_id", "topics", ["review_id"])
    op.create_index("ix_topics_topic", "topics", ["topic"])  # Required Index
    op.create_index("ix_topics_review_topic", "topics", ["review_id", "topic"], unique=True)

    # 5. alerts table
    op.create_table(
        "alerts",
        sa.Column("alert_id", sa.String(length=100), primary_key=True),
        sa.Column("alert_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("product", sa.String(length=100), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("metric", sa.String(length=100), nullable=False),
        sa.Column("previous_value", sa.Float(), nullable=False),
        sa.Column("current_value", sa.Float(), nullable=False),
        sa.Column("percentage_change", sa.Float(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, default="ACTIVE"),
    )
    op.create_index("ix_alerts_alert_id", "alerts", ["alert_id"])
    op.create_index("ix_alerts_alert_type", "alerts", ["alert_type"])
    op.create_index("ix_alerts_severity", "alerts", ["severity"])
    op.create_index("ix_alerts_topic", "alerts", ["topic"])
    op.create_index("ix_alerts_status", "alerts", ["status"])

    # 6. model_metrics table
    op.create_table(
        "model_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("evaluation_type", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("metric_name", sa.String(length=100), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("validation_sample_size", sa.Integer(), nullable=False),
        sa.Column("evaluation_timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_model_metrics_eval_type", "model_metrics", ["evaluation_type"])
    op.create_index("ix_model_metrics_category", "model_metrics", ["category"])
    op.create_index("ix_model_metrics_name", "model_metrics", ["metric_name"])


def downgrade() -> None:
    op.drop_table("model_metrics")
    op.drop_table("alerts")
    op.drop_table("topics")
    op.drop_table("sentiment_results")
    op.drop_table("reviews")
    op.drop_table("products")
