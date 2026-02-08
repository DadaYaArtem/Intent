#!/usr/bin/env python3
"""CLI viewer for DataForSEO scraper results stored in PostgreSQL."""

import argparse
import json
import sys

from dotenv import load_dotenv

load_dotenv()

from db import (
    init_db,
    list_queries,
    get_search_results,
    get_sources,
    get_full_response,
    get_markdown,
)


def cmd_list(args):
    """List all queries and their statuses."""
    rows = list_queries()
    if not rows:
        print("No queries in the database yet. Run scraper.py first.")
        return

    print(f"{'#':<4} {'Status':<10} {'Cost':>7} {'Time':>14}  Keyword")
    print("-" * 90)
    for r in rows:
        cost = f"${r['api_cost']:.4f}" if r["api_cost"] else "-"
        t = r["api_time"] or "-"
        print(f"{r['id']:<4} {r['status']:<10} {cost:>7} {t:>14}  {r['keyword']}")


def cmd_search_results(args):
    """Show search_results for a specific query keyword."""
    rows = get_search_results(args.keyword)
    if not rows:
        print(f"No search results found for keyword: '{args.keyword}'")
        return

    print(f"\nSearch Results for: '{args.keyword}'")
    print(f"Total: {len(rows)}\n")
    for i, r in enumerate(rows, 1):
        print(f"  [{i}] {r['title']}")
        print(f"      Domain: {r['domain']}")
        print(f"      URL:    {r['url']}")
        if r["description"]:
            desc = r["description"][:200]
            if len(r["description"]) > 200:
                desc += "..."
            print(f"      Desc:   {desc}")
        print()


def cmd_sources(args):
    """Show sources for a specific query keyword."""
    rows = get_sources(args.keyword)
    if not rows:
        print(f"No sources found for keyword: '{args.keyword}'")
        return

    print(f"\nSources for: '{args.keyword}'")
    print(f"Total: {len(rows)}\n")
    for i, r in enumerate(rows, 1):
        print(f"  [{i}] {r['title']}")
        print(f"      Source: {r['source_name']} ({r['domain']})")
        print(f"      URL:    {r['url']}")
        if r["publication_date"]:
            print(f"      Date:   {r['publication_date']}")
        print()


def cmd_markdown(args):
    """Show the ChatGPT markdown response for a keyword."""
    md = get_markdown(args.keyword)
    if not md:
        print(f"No markdown found for keyword: '{args.keyword}'")
        return
    print(f"\n--- Markdown for: '{args.keyword}' ---\n")
    print(md)


def cmd_json(args):
    """Dump the full raw JSON response for a keyword."""
    data = get_full_response(args.keyword)
    if not data:
        print(f"No response found for keyword: '{args.keyword}'")
        return
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        description="View DataForSEO scraper results from the database"
    )
    sub = parser.add_subparsers(dest="command")

    # list
    sub.add_parser("list", help="List all queries and statuses")

    # search-results
    p_sr = sub.add_parser("search-results", help="Show search_results for a keyword")
    p_sr.add_argument("keyword", help="The query keyword to look up")

    # sources
    p_src = sub.add_parser("sources", help="Show sources for a keyword")
    p_src.add_argument("keyword", help="The query keyword to look up")

    # markdown
    p_md = sub.add_parser("markdown", help="Show ChatGPT markdown response")
    p_md.add_argument("keyword", help="The query keyword to look up")

    # json
    p_json = sub.add_parser("json", help="Dump full raw JSON response")
    p_json.add_argument("keyword", help="The query keyword to look up")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    init_db()

    commands = {
        "list": cmd_list,
        "search-results": cmd_search_results,
        "sources": cmd_sources,
        "markdown": cmd_markdown,
        "json": cmd_json,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
