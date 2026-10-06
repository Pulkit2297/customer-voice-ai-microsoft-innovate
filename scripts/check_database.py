"""Database connectivity and schema validation script for CustomerVoice AI.

Verifies database accessibility, credentials, schema tables, and indexes
without exposing sensitive credentials in logs or console output.

Usage:
    python scripts/check_database.py [--db-url <URL>]

Exit codes:
    0: Connection successful
    1: Connection or configuration failed
"""

import argparse
import logging
from pathlib import Path
import sys
from typing import Dict, List, Set

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import settings
from src.database.connection import mask_database_url, normalize_database_url

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("check_database")

# Required tables for CustomerVoice AI analytical layer
REQUIRED_TABLES: List[str] = [
    "reviews",
    "products",
    "sentiment_results",
    "topics",
    "alerts",
    "model_metrics",
]

# Required indexes across tables: mapping from table name to set of column names indexed
REQUIRED_INDEX_COLUMNS: Dict[str, List[str]] = {
    "reviews": ["review_date", "product_id"],
    "sentiment_results": ["sentiment"],
    "topics": ["topic"],
}


def check_connectivity(db_url: str) -> bool:
    """Test database connectivity, inspect schema tables, and verify indexes.

    Args:
        db_url: The database connection URL.

    Returns:
        True if connection succeeded and required checks passed, False otherwise.
    """
    normalized_url = normalize_database_url(db_url)
    masked_url = mask_database_url(normalized_url)

    print("=" * 70)
    print("CustomerVoice AI - Database Connectivity & Health Check")
    print("=" * 70)
    print(f"Target Database: {masked_url}")

    connect_args = {}
    if "postgres" in normalized_url:
        connect_args["connect_timeout"] = 5
    elif "sqlite" in normalized_url:
        connect_args["check_same_thread"] = False

    try:
        engine = create_engine(
            normalized_url,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
    except Exception as e:
        print("\n[ERROR] Failed to initialize database engine.")
        print(f"Details: {str(e)}")
        _print_troubleshooting()
        return False

    # 1. Test basic connectivity and retrieve version
    try:
        with engine.connect() as conn:
            dialect_name = engine.dialect.name
            version_query = "SELECT version();" if dialect_name != "sqlite" else "SELECT sqlite_version();"
            version_result = conn.execute(text(version_query)).scalar()
            print(f"Connection Status: [CONNECTED]")
            print(f"Database Dialect:  {dialect_name.upper()}")
            print(f"Engine Version:    {version_result}")
    except SQLAlchemyError as exc:
        print("\n[FAILED] Unable to connect to target database.")
        print(f"Error Message: {str(exc.__cause__ or exc)}")
        _print_troubleshooting()
        return False
    except Exception as exc:
        print(f"\n[FAILED] Unexpected connection failure: {str(exc)}")
        _print_troubleshooting()
        return False

    # 2. Inspect tables
    print("\nVerifying Analytical Schema Tables:")
    inspector = inspect(engine)
    existing_tables: Set[str] = set(inspector.get_table_names())

    missing_tables = []
    for tbl in REQUIRED_TABLES:
        if tbl in existing_tables:
            print(f"  [OK] Table '{tbl}' exists.")
        else:
            print(f"  [MISSING] Table '{tbl}' was NOT found.")
            missing_tables.append(tbl)

    # 3. Inspect indexes
    print("\nVerifying Key Analytical Indexes:")
    missing_indexes = []
    for table_name, indexed_cols in REQUIRED_INDEX_COLUMNS.items():
        if table_name not in existing_tables:
            continue
        table_indexes = inspector.get_indexes(table_name)
        existing_idx_cols: Set[str] = set()
        for idx in table_indexes:
            for col in idx.get("column_names", []):
                if col:
                    existing_idx_cols.add(col)

        for col in indexed_cols:
            if col in existing_idx_cols:
                print(f"  [OK] Index on '{table_name}.{col}' exists.")
            else:
                print(f"  [MISSING] Index on '{table_name}.{col}' was NOT found.")
                missing_indexes.append(f"{table_name}.{col}")

    print("-" * 70)
    if missing_tables:
        print(f"[WARNING] {len(missing_tables)} required tables are missing.")
        print("To initialize or migrate the schema, run:")
        print("  alembic upgrade head")
        print("or run:")
        print("  python scripts/load_database.py")
        return False

    if missing_indexes:
        print(f"[WARNING] {len(missing_indexes)} expected indexes are missing: {', '.join(missing_indexes)}")

    print("[SUCCESS] All connectivity, schema, and index checks passed successfully.")
    print("=" * 70)
    return True


def _print_troubleshooting() -> None:
    """Print troubleshooting instructions for Supabase PostgreSQL connections."""
    print("-" * 70)
    print("Supabase PostgreSQL Troubleshooting Guidance:")
    print("1. Project Status:")
    print("   Verify in the Supabase Dashboard that your project is ACTIVE (not paused).")
    print("2. Environment Variable Configuration:")
    print("   Ensure DATABASE_URL is set in .env using the psycopg2 driver format:")
    print("   DATABASE_URL=postgresql+psycopg2://postgres.[ref]:[pass]@[host]:6543/postgres?sslmode=require")
    print("3. Port & Connection Mode Selection:")
    print("   - For Connection Pooling (transaction mode): Port 6543, user 'postgres.[project-ref]'")
    print("   - For Direct Connection (session mode): Port 5432, user 'postgres'")
    print("4. SSL Mode Requirement:")
    print("   Supabase requires SSL. Ensure '?sslmode=require' is appended to the connection string.")
    print("5. Password & Special Characters:")
    print("   If your database password contains special characters (e.g., @, #, %), URL-encode them.")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify database connectivity and analytical schema status."
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Database connection URL override (defaults to DATABASE_URL in settings/.env)",
    )
    args = parser.parse_args()

    db_url = args.db_url or settings.DATABASE_URL
    success = check_connectivity(db_url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
