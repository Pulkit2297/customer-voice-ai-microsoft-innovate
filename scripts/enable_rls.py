"""Enable Row Level Security (RLS) on all public tables in Supabase PostgreSQL.

Resolves Supabase automated security check 'rls_disabled_in_public'.
Superuser/backend connections (postgres role, Python, Power BI) bypass RLS,
while public PostgREST API access is properly restricted.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.database.connection import engine

TABLES = [
    "reviews",
    "sentiment_results",
    "topics",
    "products",
    "alerts",
    "model_metrics",
]

def enable_rls():
    with engine.connect() as conn:
        for table in TABLES:
            query = f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY;'
            conn.execute(text(query))
            print(f"Enabled Row Level Security on public.{table}")
        conn.commit()
    print("Successfully enabled RLS on all 6 tables.")

if __name__ == "__main__":
    enable_rls()
