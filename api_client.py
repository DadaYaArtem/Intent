"""DataForSEO API client for LLM Scraper endpoint."""

import os
import time

import requests

API_URL = "https://api.dataforseo.com/v3/ai_optimization/chat_gpt/llm_scraper/live/advanced"

LANGUAGE_CODE = "en"
LOCATION_CODE = 2840  # United States


def get_credentials():
    login = os.environ.get("DATAFORSEO_LOGIN")
    password = os.environ.get("DATAFORSEO_PASSWORD")
    if not login or not password:
        raise RuntimeError(
            "Set DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD environment variables "
            "(or in .env file)."
        )
    return login, password


def fetch_keyword(keyword: str, retries: int = 3) -> dict:
    """Call the DataForSEO LLM scraper for a single keyword.

    Returns the parsed JSON response dict.
    Retries on network errors with exponential backoff.
    """
    login, password = get_credentials()

    payload = [
        {
            "language_code": LANGUAGE_CODE,
            "location_code": LOCATION_CODE,
            "keyword": keyword,
            "force_web_search": True,
        }
    ]

    last_exc = None
    for attempt in range(retries):
        try:
            resp = requests.post(
                API_URL,
                json=payload,
                auth=(login, password),
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"  Retry {attempt + 1}/{retries} after {wait}s – {exc}")
                time.sleep(wait)

    raise RuntimeError(f"API request failed after {retries} attempts: {last_exc}")
