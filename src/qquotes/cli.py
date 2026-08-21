"""Command-line orchestration for fetching and printing quotes."""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import textwrap
import time
import urllib.error

from . import feeds, wikiquote
from .config import (
    DEFAULT_CONFIG_PATH,
    REQUEST_DELAY,
    Config,
    METRIC_LABELS,
)
from .history import load_history, quote_key, record_history, reset_history


class Renderer:
    """Wraps and indents output so text stays clear of the terminal edges."""

    def __init__(self, margin_left: int, margin_right: int) -> None:
        self.pad = " " * max(0, margin_left)
        self.width = max(40, shutil.get_terminal_size((80, 20)).columns - margin_left - margin_right)

    def emit(self, text: str = "") -> None:
        for para in text.split("\n"):
            lines = textwrap.fill(para, width=self.width) if para.strip() else ""
            for wrapped in (lines.split("\n") if lines else [""]):
                print(f"{self.pad}{wrapped}")

    def separator(self, char: str = "=") -> None:
        print(f"{self.pad}{char * self.width}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch a curated batch of quotes for reflection.")
    parser.add_argument("--count", type=int, default=None, help="Number of quotes to print (default from config)")
    parser.add_argument("--authors", help="Comma-separated Wikiquote author list (overrides config)")
    parser.add_argument(
        "--langs", default="",
        help="Comma-separated CJK languages to include and translate: ja,zh",
    )
    parser.add_argument("--no-other-sources", action="store_true",
                        help="Only use Wikiquote (English + requested langs)")
    parser.add_argument("--history", default=None, help="Path to repeat-prevention history file")
    parser.add_argument("--config", default=None, help="Path to config.toml (default: repo config.toml)")
    parser.add_argument("--reset-history", action="store_true", help="Clear the history file and start fresh")
    args = parser.parse_args(argv)

    cfg = Config.load(args.config)
    count = max(1, args.count if args.count is not None else cfg.count)
    history_path = args.history or cfg.history_path
    view = Renderer(cfg.format.margin_left, cfg.format.margin_right)
    lang_codes = [l.strip() for l in args.langs.split(",") if l.strip()]
    en_authors = [a.strip() for a in args.authors.split(",")] if args.authors else cfg.en_authors

    if args.reset_history:
        reset_history(history_path)
        print(f"  [..] history cleared: {history_path}", file=sys.stderr)

    exclude = set(load_history(history_path))
    pool: list[dict] = []

    def add(text: str, author: str, source: str) -> None:
        key = quote_key(text)
        if key not in exclude:
            exclude.add(key)
            pool.append({"text": text, "author": author, "source": source})

    def add_capped(candidates: list[tuple[str, str]], source: str, cap: int) -> int:
        random.shuffle(candidates)
        added = 0
        for text, author in candidates:
            if added >= cap:
                break
            if quote_key(text) in exclude:
                continue
            add(text, author, source)
            added += 1
        return added

    # --- Reserved slots: 2 from the daily Stoic feed, then 1 from each
    # verifiable API (zenquotes.io, type.fit). Quotas shrink to fit --count.
    guaranteed: list[dict] = []
    if not args.no_other_sources:
        stoic_want = min(2, count)
        zq_want = min(1, count - stoic_want)
        tf_want = min(1, count - stoic_want - zq_want)

        base = len(pool)
        add_capped(feeds.fetch_stoic_quotes(), "stoic-quotes.com", stoic_want)
        guaranteed += pool[base:]
        print(f"  [ok] Stoic API: {len(pool) - base}/{stoic_want} reserved", file=sys.stderr)

        base = len(pool)
        add_capped(feeds.fetch_zenquotes(10), "zenquotes.io", zq_want)
        guaranteed += pool[base:]
        print(f"  [ok] zenquotes.io: {len(pool) - base}/{zq_want} reserved", file=sys.stderr)

        base = len(pool)
        add_capped(feeds.fetch_typefit(), "type.fit", tf_want)
        guaranteed += pool[base:]
        print(f"  [ok] type.fit: {len(pool) - base}/{tf_want} reserved", file=sys.stderr)

        pool = pool[len(guaranteed):]  # keep pool for wikiquote fill only

    # --- English Wikiquote ---
    selected = random.sample(en_authors, min(6, len(en_authors)))
    for author in selected:
        try:
            quotes = wikiquote.fetch_wikiquote_quotes(author, delay=REQUEST_DELAY)
        except (urllib.error.HTTPError, urllib.error.URLError, OSError, KeyError, json.JSONDecodeError):
            quotes = []
        if quotes:
            add_capped(list(zip(quotes, [author] * len(quotes))), "Wikiquote (EN)", cap=3)
            print(f"  [ok] EN {author}: {len(quotes)} quotes", file=sys.stderr)
        else:
            print(f"  [--] EN {author}: no quotes", file=sys.stderr)
        time.sleep(REQUEST_DELAY)

    # --- CJK Wikiquote + translation ---
    for lang in lang_codes:
        authors = [(t, info) for t, info in cfg.asian_authors.items() if info[0] == lang]
        random.shuffle(authors)
        for native, (code, english) in authors[:4]:
            try:
                raw = wikiquote.fetch_wikiquote_quotes(native, lang=code, delay=REQUEST_DELAY)
            except (urllib.error.HTTPError, urllib.error.URLError, OSError, KeyError, json.JSONDecodeError):
                raw = []
            if not raw:
                print(f"  [--] {english} ({code}): no quotes", file=sys.stderr)
                time.sleep(REQUEST_DELAY)
                continue
            translated = []
            for _q in random.sample(raw, min(3, len(raw))):
                tr = wikiquote.translate(_q, code)
                if tr and len(tr) >= 15:
                    translated.append((tr, english))
                time.sleep(0.5)
            add_capped(translated, METRIC_LABELS.get(code, "Wikiquote (trans.)"), cap=1)
            print(f"  [ok] {english} ({code}): {len(raw)} raw, {len(translated)} translated", file=sys.stderr)
            time.sleep(REQUEST_DELAY)

    random.shuffle(pool)
    final = list(guaranteed) + pool[: max(0, count - len(guaranteed))]
    if len(final) < count:
        print(
            f"  [..] only {len(final)} fresh quotes available "
            f"(history has {len(exclude)} entries); reduce --count or reset --history",
            file=sys.stderr,
        )

    # ------------------------------------------------------------------
    view.emit()
    view.separator("=")
    view.emit(" 📖 INTENTIONAL PASSAGES & THOUGHTS")
    view.separator("=")

    if final:
        for i, item in enumerate(final, start=1):
            view.emit()
            view.emit(f"{i}. “{item['text']}”")
            view.emit()
            view.emit(f"     — {item['author']} [{item['source']}]")
            view.separator("-")
        record_history(history_path, [(i["text"], i["author"]) for i in final])
        return 0

    fallback = feeds.fetch_stoic_api()
    if fallback:
        text, author = fallback
        view.emit()
        view.emit(f"“{text}”")
        view.emit()
        view.emit(f"   — {author} [Stoic API]")
        view.separator("-")
        return 0

    print("\nCould not fetch any quotes. Check your network connection.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())