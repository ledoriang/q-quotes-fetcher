"""Additional English quote feeds (zenquotes.io, type.fit, stoic fallback)."""
from __future__ import annotations

import json
import urllib.request

from .config import USER_AGENT


def _get_json(url: str, timeout: float):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_zenquotes(count: int) -> list[tuple[str, str]]:
    """Random quotes from zenquotes.io (no key required)."""
    try:
        data = _get_json(f"https://zenquotes.io/api/random/{int(count)}", timeout=10)
        return [(item.get("q"), item.get("a")) for item in data if item.get("q")]
    except Exception:
        return []


def fetch_typefit() -> list[tuple[str, str]]:
    """Full static quote dataset from type.fit; cached in memory per run."""
    try:
        data = _get_json("https://type.fit/api/quotes", timeout=10)
        return [(item.get("text"), item.get("author")) for item in data if item.get("text")]
    except Exception:
        return []


def fetch_stoic_quotes(count: int = 10) -> list[tuple[str, str]]:
    """Random Stoic quotes from the stoic-quotes.com feed (the 'daily stoic' API)."""
    try:
        data = _get_json(f"https://stoic-quotes.com/api/quotes", timeout=10)
        return [(item.get("text"), item.get("author")) for item in data if item.get("text")]
    except Exception:
        return []


def fetch_stoic_api() -> tuple[str, str] | None:
    """Last-resort fallback from a stoic-quotes endpoint."""
    try:
        data = _get_json("https://stoic-quotes.com/api/quote", timeout=5)
        return (data.get("text"), data.get("author"))
    except Exception:
        return None