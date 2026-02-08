"""Database schema and operations for DataForSEO results."""

import json
import os

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://dfuser:dfpass123@localhost:5432/dataforseo"
)


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS queries (
            id SERIAL PRIMARY KEY,
            keyword TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS responses (
            id SERIAL PRIMARY KEY,
            query_id INTEGER NOT NULL REFERENCES queries(id) ON DELETE CASCADE,
            full_response JSONB NOT NULL,
            model TEXT,
            check_url TEXT,
            markdown TEXT,
            api_cost NUMERIC(10, 4),
            api_time TEXT,
            datetime TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS search_results (
            id SERIAL PRIMARY KEY,
            response_id INTEGER NOT NULL REFERENCES responses(id) ON DELETE CASCADE,
            url TEXT,
            domain TEXT,
            title TEXT,
            description TEXT,
            breadcrumb TEXT
        );

        CREATE TABLE IF NOT EXISTS sources (
            id SERIAL PRIMARY KEY,
            response_id INTEGER NOT NULL REFERENCES responses(id) ON DELETE CASCADE,
            url TEXT,
            domain TEXT,
            title TEXT,
            source_name TEXT,
            publication_date TEXT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Database initialized.")


def save_response(keyword: str, raw_response: dict):
    """Save a full API response and extract search_results/sources."""
    conn = get_connection()
    cur = conn.cursor()

    # Upsert query
    cur.execute(
        "INSERT INTO queries (keyword, status) VALUES (%s, 'done') "
        "ON CONFLICT (keyword) DO UPDATE SET status='done', updated_at=NOW() "
        "RETURNING id",
        (keyword,),
    )
    query_id = cur.fetchone()[0]

    # Delete old data for this query (re-run safe)
    cur.execute(
        "DELETE FROM responses WHERE query_id = %s", (query_id,)
    )

    # Extract result-level fields
    task = raw_response.get("tasks", [{}])[0]
    result = (task.get("result") or [{}])[0]

    cur.execute(
        "INSERT INTO responses (query_id, full_response, model, check_url, markdown, api_cost, api_time, datetime) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (
            query_id,
            json.dumps(raw_response),
            result.get("model"),
            result.get("check_url"),
            result.get("markdown"),
            task.get("cost"),
            task.get("time"),
            result.get("datetime"),
        ),
    )
    response_id = cur.fetchone()[0]

    # Save search_results
    for sr in result.get("search_results") or []:
        cur.execute(
            "INSERT INTO search_results (response_id, url, domain, title, description, breadcrumb) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                response_id,
                sr.get("url"),
                sr.get("domain"),
                sr.get("title"),
                sr.get("description"),
                sr.get("breadcrumb"),
            ),
        )

    # Save sources
    for src in result.get("sources") or []:
        cur.execute(
            "INSERT INTO sources (response_id, url, domain, title, source_name, publication_date) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                response_id,
                src.get("url"),
                src.get("domain"),
                src.get("title"),
                src.get("source_name"),
                src.get("publication_date"),
            ),
        )

    conn.commit()
    cur.close()
    conn.close()


def mark_query_error(keyword: str, error_msg: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO queries (keyword, status) VALUES (%s, %s) "
        "ON CONFLICT (keyword) DO UPDATE SET status=%s, updated_at=NOW()",
        (keyword, f"error: {error_msg[:200]}", f"error: {error_msg[:200]}"),
    )
    conn.commit()
    cur.close()
    conn.close()


# ── Query helpers for the viewer ──────────────────────────────────────


def list_queries():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT q.id, q.keyword, q.status, q.updated_at, "
        "       r.model, r.api_cost, r.api_time "
        "FROM queries q "
        "LEFT JOIN responses r ON r.query_id = q.id "
        "ORDER BY q.id"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_search_results(keyword: str):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT sr.* FROM search_results sr "
        "JOIN responses r ON r.id = sr.response_id "
        "JOIN queries q ON q.id = r.query_id "
        "WHERE q.keyword = %s "
        "ORDER BY sr.id",
        (keyword,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_sources(keyword: str):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT s.* FROM sources s "
        "JOIN responses r ON r.id = s.response_id "
        "JOIN queries q ON q.id = r.query_id "
        "WHERE q.keyword = %s "
        "ORDER BY s.id",
        (keyword,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_full_response(keyword: str):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT r.full_response FROM responses r "
        "JOIN queries q ON q.id = r.query_id "
        "WHERE q.keyword = %s",
        (keyword,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["full_response"] if row else None


def get_markdown(keyword: str):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT r.markdown FROM responses r "
        "JOIN queries q ON q.id = r.query_id "
        "WHERE q.keyword = %s",
        (keyword,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["markdown"] if row else None
