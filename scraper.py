#!/usr/bin/env python3
"""Main scraper: reads queries.txt, calls DataForSEO API, stores results in PostgreSQL."""

import argparse
import sys
import time

from dotenv import load_dotenv

load_dotenv()

from api_client import fetch_keyword
from db import init_db, save_response, mark_query_error, get_connection


def load_queries(path: str = "queries.txt") -> list[str]:
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]


def already_done(keyword: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT status FROM queries WHERE keyword = %s", (keyword,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row is not None and row[0] == "done"


def run(queries_file: str = "queries.txt", skip_done: bool = True, delay: float = 2.0):
    init_db()
    queries = load_queries(queries_file)
    total = len(queries)
    print(f"Loaded {total} queries from {queries_file}\n")

    done = 0
    skipped = 0
    errors = 0

    for i, keyword in enumerate(queries, 1):
        if skip_done and already_done(keyword):
            print(f"[{i}/{total}] SKIP (already done): {keyword}")
            skipped += 1
            continue

        print(f"[{i}/{total}] Fetching: {keyword}")
        try:
            response = fetch_keyword(keyword)

            # Check for API-level errors
            status_code = response.get("status_code", 0)
            if status_code != 20000:
                msg = response.get("status_message", "unknown error")
                print(f"  API error {status_code}: {msg}")
                mark_query_error(keyword, f"{status_code}: {msg}")
                errors += 1
                continue

            task = (response.get("tasks") or [{}])[0]
            task_status = task.get("status_code", 0)
            if task_status != 20000:
                msg = task.get("status_message", "unknown")
                print(f"  Task error {task_status}: {msg}")
                mark_query_error(keyword, f"task {task_status}: {msg}")
                errors += 1
                continue

            save_response(keyword, response)
            done += 1
            cost = task.get("cost", 0)
            t = task.get("time", "?")
            print(f"  OK – cost: ${cost}, time: {t}")

        except Exception as exc:
            print(f"  ERROR: {exc}")
            mark_query_error(keyword, str(exc))
            errors += 1

        # Rate-limit between requests
        if i < total:
            time.sleep(delay)

    print(f"\nFinished: {done} done, {skipped} skipped, {errors} errors (of {total} total)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape DataForSEO LLM results for queries")
    parser.add_argument(
        "-f", "--file", default="queries.txt", help="Path to queries file (default: queries.txt)"
    )
    parser.add_argument(
        "--no-skip", action="store_true", help="Re-fetch queries that were already completed"
    )
    parser.add_argument(
        "--delay", type=float, default=2.0,
        help="Delay in seconds between API requests (default: 2.0)",
    )
    args = parser.parse_args()
    run(queries_file=args.file, skip_done=not args.no_skip, delay=args.delay)
