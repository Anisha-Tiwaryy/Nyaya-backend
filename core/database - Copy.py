"""Shared database connection helpers (psycopg 3)."""
import psycopg
from psycopg.rows import dict_row
from core.config import DATABASE_URL


def get_connection():
    """Open a new database connection. Caller is responsible for closing it
    (use a `with` block)."""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def test_connection():
    """Quick connectivity check used by Phase 0."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            return cur.fetchone()["version"]


if __name__ == "__main__":
    print("Connecting to the database...")
    print("OK:", test_connection())
