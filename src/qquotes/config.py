"""Configuration loading and shared constants."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

USER_AGENT = "QQuotesFetcher/1.0 (local personal script)"
REQUEST_DELAY = 0.6  # seconds between wiki API calls to avoid 429s
MAX_RETRIES = 3

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config.toml"
DEFAULT_HISTORY_PATH = REPO_ROOT / "data" / "history.jsonl"

DEFAULT_EN_AUTHORS = [
    "Seneca the Younger",
    "Epictetus",
    "Marcus Aurelius",
    "Friedrich Nietzsche",
    "Carl Jung",
    "Leo Tolstoy",
    "Fyodor Dostoevsky",
    "Arthur Schopenhauer",
    "Albert Camus",
    "Viktor Frankl",
    "Hermann Hesse",
    "Alan Watts",
]

# Native page titles -> (wiki language code, English display name).
DEFAULT_ASIAN_AUTHORS: dict[str, tuple[str, str]] = {
    "老子": ("zh", "Laozi"),
    "莊子": ("zh", "Zhuangzi"),
    "孔子": ("zh", "Confucius"),
    "孟子": ("zh", "Mencius"),
    "夏目漱石": ("ja", "Natsume Sōseki"),
    "太宰治": ("ja", "Osamu Dazai"),
    "坂口安吾": ("ja", "Ango Sakaguchi"),
    "樋口一葉": ("ja", "Higuchi Ichiyō"),
    "宮沢賢治": ("ja", "Kenji Miyazawa"),
    "岡本太郎": ("ja", "Tarō Okamoto"),
}

METRIC_LABELS = {"ja": "Wikiquote (JA, trans.)", "zh": "Wikiquote (ZH, trans.)"}


@dataclass
class Format:
    margin_left: int = 4
    margin_right: int = 4


@dataclass
class Config:
    count: int = 10
    history_path: Path = DEFAULT_HISTORY_PATH
    en_authors: list[str] = field(default_factory=list)
    asian_authors: dict[str, tuple[str, str]] = field(default_factory=dict)
    format: Format = field(default_factory=Format)

    @classmethod
    def load(cls, path: Path | str | None = None) -> "Config":
        path = Path(path) if path else DEFAULT_CONFIG_PATH
        if not path.is_file():
            return cls()
        with open(path, "rb") as fh:
            data = tomllib.load(fh)

        quotes = data.get("quotes", {})
        history = Path(quotes.get("history", DEFAULT_HISTORY_PATH))
        history = history if history.is_absolute() else REPO_ROOT / history

        fmt = data.get("format", {})

        en = data.get("authors", {}).get("en", {})
        en_names = en.get("names", []) or DEFAULT_EN_AUTHORS

        asian_raw = data.get("authors", {}).get("asian", {})
        asian = {}
        for title, info in asian_raw.items():
            lang = info.get("lang")
            name = info.get("name", title)
            if lang:
                asian[title] = (lang, name)

        return cls(
            count=int(quotes.get("count", 10)),
            history_path=history,
            en_authors=[str(n) for n in en_names],
            asian_authors=asian or DEFAULT_ASIAN_AUTHORS,
            format=Format(
                margin_left=int(fmt.get("margin_left", 4)),
                margin_right=int(fmt.get("margin_right", 4)),
            ),
        )