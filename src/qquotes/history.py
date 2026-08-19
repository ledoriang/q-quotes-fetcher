"""Repeat-prevention history stored as a JSONL fingerprint file."""
from __future__ import annotations

import os
import re
from pathlib import Path

_HISTORY_RE = re.compile(r"[^a-z0-9]")


def quote_key(text: str) -> str:
    """Normalized fingerprint used to detect repeats."""
    return _HISTORY_RE.sub("", text.lower())


def load_history(path: str | Path) -> set[str]:
    keys: set[str] = set()
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        keys.add(line)
        except OSError:
            pass
    return keys


def record_history(path: str | Path, quotes: list[tuple[str, str]]) -> None:
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            for text, author in quotes:
                fh.write(f"{quote_key(text)}\t{author.replace(chr(10), ' ')}\n")
    except OSError:
        pass


def reset_history(path: str | Path) -> None:
    if os.path.exists(path):
        os.remove(path)