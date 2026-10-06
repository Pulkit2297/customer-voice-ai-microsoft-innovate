# Supabase PostgreSQL Analytics Layer Architecture & Setup

## 1. Overview & Production Target

**CustomerVoice AI** leverages a normalized, relational analytical storage layer targeted for **Supabase PostgreSQL** in production. The system uses **SQLAlchemy** as the ORM, **Alembic** for schema migrations, and the **psycopg2** driver for high-performance PostgreSQL interaction.

- **Production Database**: Supabase PostgreSQL
- **ORM & Session Management**: SQLAlchemy 2.0+
- **Database Driver**: `psycopg2-binary` (connection strings normalized as `postgresql+psycopg2://...`)
- **Schema Evolution**: Alembic migrations
- **Local Testing**: SQLite in-memory fixtures (strictly isolated to test environments)

> [!IMPORTANT]
> The application never hardcodes database credentials. All connection parameters are resolved dynamically via the `DATABASE_URL` environment variable.

---

## 2. Schema Architecture & Entity Relationships

The schema implements a star schema optimized for fast analytical aggregations, Power BI ingestion, and operational alerting.

```
              ┌───────────────────────────┐
              │         products          │ (Dimension)
              ├───────────────────────────┤
              │ product_id (PK) [IDX]     │
              │ product_name              │
              │ category [IDX]            │
              │ created_at                │
              └─────────────┬─────────────┘
                            │ 1
                            │
                            │ N
              ┌─────────────▼─────────────┐
              │          reviews          │ (Fact Table)
              ├───────────────────────────┤
              │ review_id (PK) [IDX]      │
              │ review_text               │
              │ cleaned_text              │
              │ rating                    │
              │ review_date [IDX]         │◄─── Indexed for Time-Series Trends
              │ product_id (FK) [IDX]     │◄─── Indexed for Product Slicing
              │ campaign [IDX]            │
              │ source                    │
              │ pii_detected              │
              │ pii_types                 │
              │ created_at                │
              └───────┬───────────┬───────┘
                      │ 1         │ 1
                      │           │
                      │ 1         │ N
     ┌────────────────▼──────┐   ┌▼─────────────────────────┐
     │   sentiment_results   │   │          topics          │ (Bridge Table)
     ├───────────────────────┤   ├──────────────────────────┤
     │ id (PK)               │   │ id (PK)                  │
     │ review_id (FK) [IDX]  │   │ review_id (FK) [IDX]     │
     │ sentiment [IDX]       │   │ topic [IDX]              │◄─── Indexed for Topics
     │ sentiment_score       │   │ topic_confidence         │
     │ confidence            │   │ is_primary               │
     │ model_name            │   │ created_at               │
     │ model_version         │   └──────────────────────────┘
     │ created_at            │
     └───────────────────────┘

┌───────────────────────────┐     ┌───────────────────────────┐
│          alerts           │     │       model_metrics       │
├───────────────────────────┤     ├───────────────────────────┤
│ alert_id (PK) [IDX]       │     │ id (PK)                   │
│ alert_type [IDX]          │     │ evaluation_type [IDX]     │
│ severity [IDX]            │     │ category [IDX]            │
│ product                   │     │ metric_name [IDX]         │
│ topic [IDX]               │     │ metric_value              │
│ metric                    │     │ validation_sample_size    │
│ previous_value            │     │ evaluation_timestamp      │
│ current_value             │     └───────────────────────────┘
│ percentage_change         │
│ message                   │
│ created_at                │
│ status [IDX]              │
└───────────────────────────┘
```

---

## 3. Query Index Strategy

Explicit B-Tree indexes are enforced on the highest-cardinality analytical slice-and-dice dimensions:

| Table | Index Name | Indexed Columns | Query Purpose |
| :--- | :--- | :--- | :--- |
| `reviews` | `ix_reviews_review_date` | `review_date` | Accelerates chronological aggregations, WoW/MoM trends, and date filtering |
| `reviews` | `ix_reviews_product_id` | `product_id` | Accelerates joins between product dimension and feedback facts |
| `sentiment_results` | `ix_sentiment_results_sentiment` | `sentiment` | Accelerates filtering by positive, neutral, and negative classes |
| `topics` | `ix_topics_topic` | `topic` | Enables low-latency filtering on multi-label product topics |
| `topics` | `ix_topics_review_topic` | `review_id, topic` | Composite unique index enforcing idempotency per review topic |

---

## 4. Supabase Setup Guide

### 4.1 Obtaining Connection Parameters from Supabase Dashboard
1. Log in to the [Supabase Dashboard](https://supabase.com/dashboard) and select your project.
2. Navigate to **Project Settings** (gear icon) &rarr; **Database**.
3. Under the **Connection Parameters** section, locate the following fields:
   - **Host**:
     - *Connection Pooler (Recommended)*: `aws-0-[region].pooler.supabase.com`
     - *Direct Connection*: `db.[project-ref].supabase.co`
   - **Database**: `postgres` (default database name)
   - **User**:
     - *Connection Pooler*: `postgres.[project-ref]`
     - *Direct Connection*: `postgres`
   - **Password**: Your database password configured during Supabase project creation.
   - **Port**:
     - *Connection Pooler*: `6543` (Transaction mode)
     - *Direct Connection*: `5432` (Session mode)
   - **SSL Mode**: `sslmode=require` (**MANDATORY** for secure cloud connectivity)

### 4.2 Configuring `.env`
Set `DATABASE_URL` in your `.env` file using the `postgresql+psycopg2://` driver prefix:

```env
# Production Supabase Connection URL (Pooler)
DATABASE_URL=postgresql+psycopg2://postgres.[project-ref]:[YOUR_PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require

# Direct Connection Alternative:
# DATABASE_URL=postgresql+psycopg2://postgres:[YOUR_PASSWORD]@db.[project-ref].supabase.co:5432/postgres?sslmode=require
```

> [!NOTE]
> If a standard `postgresql://` or `postgres://` URL is provided, the CustomerVoice AI engine automatically normalizes it to `postgresql+psycopg2://` at runtime to ensure driver compatibility.

---

## 5. Database Verification Script

To verify your connection to Supabase without printing sensitive credentials, execute:

```powershell
python scripts/check_database.py
```

This script:
1. Masks credentials in console logs (e.g. `postgresql+psycopg2://postgres:***@db...`).
2. Tests active database connectivity with `SELECT version()`.
3. Verifies existence of all 6 analytical tables (`reviews`, `products`, `sentiment_results`, `topics`, `alerts`, `model_metrics`).
4. Verifies presence of key indexes (`review_date`, `product_id`, `sentiment`, `topic`).
5. Prints dialect, version, and schema status, exiting with code 0 on success or code 1 with troubleshooting steps on failure.

---

## 6. Running Schema Migrations (Alembic)

Alembic manages schema evolution. The configuration is declared in `alembic.ini` pointing to `src/database/migrations/`:

```powershell
# Upgrade Supabase database to latest schema revision
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Generate a new autogenerated revision
alembic revision --autogenerate -m "add_new_feature_table"
```

---

## 7. Ingesting Processed Data into Supabase

To populate Supabase PostgreSQL with cleaned, attributed reviews, topics, sentiment scores, alerts, and model evaluation metrics:

```powershell
python scripts/load_database.py
```

### Optional Database URL Override:
```powershell
python scripts/load_database.py --db-url "postgresql+psycopg2://postgres:[password]@db.[project-ref].supabase.co:5432/postgres?sslmode=require"
```

---

## 8. Connecting Power BI to Supabase PostgreSQL

1. Open **Power BI Desktop**.
2. Select **Get Data** &rarr; **PostgreSQL Database**.
3. In the Server dialog:
   - **Server**: `db.[project-ref].supabase.co:5432` (or pooler endpoint)
   - **Database**: `postgres`
4. Select Data Connectivity mode:
   - **Import**: Recommended for high-speed local caching, complex DAX measures, and offline reporting.
   - **DirectQuery**: Recommended for real-time operational KPI card feeds.
5. In the authentication prompt:
   - Select **Database** tab.
   - Enter User name: `postgres` (or `postgres.[project-ref]` if using pooler)
   - Enter Password: Your Supabase database password.
   - Ensure Encrypted connection is checked (SSL).
6. In the Navigator, select the 6 core tables:
   - `products`, `reviews`, `sentiment_results`, `topics`, `alerts`, `model_metrics`.
7. Power BI will automatically establish relationships between `reviews.product_id` &rarr; `products.product_id` and `reviews.review_id` &rarr; `sentiment_results.review_id`.
