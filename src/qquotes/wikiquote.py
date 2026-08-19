"""Wikiquote fetching and parsing (English + Japanese/Chinese with translation)."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from .config import MAX_RETRIES, USER_AGENT
from .history import quote_key

WIKILINK = re.compile(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]")
CJK = re.compile(r"[\u4e00-\u9fff]")

# Lines matching these markers are editorial commentary or source citations.
META_MARKERS = re.compile(
    r"attribution|no printed source|not from any known translation|"
    r"paraphras|arose on the internet|books\.google|screenplay|"
    r"wikiquote|reference|citation needed|as translated by|translated as|"
    r"in his essay|in his book|quoted by|interviewed on|audio lecture|"
    r"epigraph\b|http|misquoted|grammatically corrected|sometimes quoted|"
    r"motto of|parerga|§|translated\b|\bvol\.?\s*\d|\binterview\b|hays translation|"
    r"\btrans\.\b|,\s*ch\.?\s*\d|"
    r"essay on\s+[\"“'‘]|\([^)]*translation\)|"
    r"\(\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+"
    r"(18|19|20)\d{2}\s*\)",
    re.IGNORECASE,
)
SOURCE_PREFIX = re.compile(
    r"^(vol(um|\.)?\s*\d|chapter|ch\.\s*\d|part\s*\d|§|book\s*\d|epigraph)", re.IGNORECASE
)
PAREN_YEAR = re.compile(r"\(\s*(18|19|20)\d{2}")


def clean_markup(text: str) -> str:
    """Strip wikitext markup from a line, keeping the readable text."""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("'''", "").replace("''", "")
    text = WIKILINK.sub(r"\1", text)
    text = text.replace("&nbsp;", " ").replace("&quot;", '"').replace("&#39;", "'")
    return re.sub(r"\s+", " ", text).strip()


def fetch_wikiquote_quotes(title: str, lang: str = "en", delay: float = 0.6) -> list[str]:
    """Fetch a page's wikitext from a Wikiquote edition and parse quote lines."""
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "titles": title,
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "redirects": 1,
            "format": "json",
        }
    )
    host = "en.wikiquote.org" if lang == "en" else f"{lang}.wikiquote.org"
    url = f"https://{host}/w/api.php?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    data = None
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < MAX_RETRIES - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise
    if data is None:
        return []
    pages = data["query"]["pages"]
    page = list(pages.values())[0]
    if "-1" in str(page.get("pageid", "")):
        return []
    wikitext = page["revisions"][0]["slots"]["main"]["*"]
    if lang == "en":
        return parse_en_quotes(wikitext, author=title)
    return parse_cjk_quotes(wikitext)


def parse_en_quotes(wikitext: str, author: str = "") -> list[str]:
    """Extract plausible English quote lines from a Wikiquote page."""
    surname = author.strip().split()[-1] if author.strip() else ""
    quotes = []
    seen = set()
    for raw in wikitext.split("\n"):
        line = raw.strip()
        if not line.startswith("*"):
            continue
        if "{{" in line or "[[File:" in line or META_MARKERS.search(line):
            continue
        content = clean_markup(line.lstrip("*").strip())
        if not content:
            continue
        if surname and re.search(rf"\b{re.escape(surname)}\b", content, re.IGNORECASE):
            continue  # "Quotes about X" sections discuss the author; skip those
        if len(content) < 30 or len(content) > 400:
            continue
        if '"' not in content and "“" not in content:
            continue
        if re.search(r"\b(18|19|20)\d{2}\s*$", content):  # trailing citation year
            continue
        if SOURCE_PREFIX.match(content) or PAREN_YEAR.search(content):
            continue
        # A quoted span with almost nothing around it is a title/citation.
        outside = re.sub(r'["“][^"”]*["”]', "", content)
        outside = re.sub(r"[^\w]", "", outside)
        if len(content) < 100 and len(outside) < 15:
            continue
        # Skip passages that are mostly non-English (e.g. Greek fragments).
        latin = re.findall(r"[A-Za-z0-9 ]", content)
        if len(latin) / len(content) < 0.75:
            continue
        key = quote_key(content)
        if key in seen:
            continue
        seen.add(key)
        quotes.append(content)
    return quotes


def parse_cjk_quotes(wikitext: str) -> list[str]:
    """Extract good-looking CJK quote lines from ja/zh Wikiquote pages."""
    quotes = []
    seen = set()
    for raw in wikitext.split("\n"):
        line = raw.strip()
        if not line.startswith("*"):
            continue
        if line.startswith("*:") or "{{" in line or "[[File:" in line:
            continue
        if "<small>" in line or "<ref" in line.lower():
            continue
        content = clean_markup(re.sub(r"<br\s*/?>", " ", line.lstrip("*").strip()))
        if not content:
            continue
        if len(CJK.findall(content)) < 4:
            continue
        if len(content) < 8 or len(content) > 80:
            continue  # short aphorisms translate far better than long prose
        if "（" in content or "(" in content:  # citation / footnote parens
            continue
        if re.search(r"\d{2,}\s*年", content):  # year citation
            continue
        key = quote_key(content)
        if key in seen:
            continue
        seen.add(key)
        quotes.append(content)
    return quotes


def translate(text: str, src: str) -> str | None:
    """Translate to English via the free MyMemory API."""
    params = urllib.parse.urlencode({"q": text[:500], "langpair": f"{src}|en"})
    url = f"https://api.mymemory.translated.net/get?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
        if data.get("responseStatus") != 200:
            return None
        out = data["responseData"]["translatedText"]
        if not out or out.upper().startswith("MYMEMORY"):
            return None
        return out.strip()
    except Exception:
        return None