# q-quotes-fetcher

Fetch a curated batch of quotes from multiple sources for human intake (reading / reflection).
Shown quotes are recorded locally so daily runs keep serving fresh material.

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
```

## Usage

```sh
# 10 quotes from default authors (count from config.toml)
uv run get-passages

# Customize count
uv run get-passages --count 20

# Include Japanese and Chinese thinkers (machine-translated to English)
uv run get-passages --langs ja,zh --count 12

# Only Wikiquote (no zenquotes.io / type.fit feeds)
uv run get-passages --no-other-sources

# Start the repeat-prevention history from scratch
uv run get-passages --reset-history
```

Equivalent invocation forms: `uv run python src/get_passages.py ...` or
`uv run python -m qquotes.cli ...`.

## Windows: double-click to read

For a desktop experience on Windows (no console windows, no prompts):

1. Install [uv](https://docs.astral.sh/uv/) and run `uv sync` once in this repo.
2. Make a desktop shortcut to **`scripts\get-quotes.vbs`** (or the `.bat` fallback).
   Double-clicking pops a scrollable window with the day's quotes; Enter or the
   Close button dismisses it. To change the batch size, languages, or source
   set, edit the `Count` / `Langs` / `NoOtherSources` values at the top of
   `get-quotes.vbs` or the `param()` block in `scripts\show-quotes.ps1`.

Note: if your policy blocks `.vbs` files, use `scripts\get-quotes.bat` instead
(it flashes a console window briefly, then shows the same GUI).

## Configuration

Manage authors, the default count, and history path in `config.toml` at the repo
root (see the file for the schema). Everything is overridable via CLI flags
(`get-passages --help`).

```toml
[quotes]
count = 12

[authors.en]
names = ["Seneca the Younger", "Epictetus", ...]

[authors.asian]
"老子" = { lang = "zh", name = "Laozi" }
```

## Sources

| Source | Content | Output language |
| --- | --- | --- |
| Wikiquote (`en.wikiquote.org`) | Parsed wikitext quotes from a configurable bank | English |
| Wikiquote (`ja` / `zh` editions) | Eastern aphorisms, translated via MyMemory | → English |
| stoic-quotes.com | Daily Stoic feed (always contributes 2 quotes) | English |
| zenquotes.io | Random quotes API, no key (1 quote) | English |
| type.fit `/api/quotes` | Static quote dataset (1 quote) | English |

Each batch reserves 2 quotes from the Stoic feed and 1 from each of
zenquotes.io and type.fit (best-effort: only fresh, unshown quotes are used),
then fills the rest of `--count` from the Wikiquote bank.

## Repeat prevention

Every printed quote is fingerprinted (normalized lowercase text) and appended to
`data/history.jsonl` inside the repo (override with `--history PATH`).
The `data/` directory is gitignored. Selection skips anything already shown, so
consecutive daily runs avoid repeats.

## Layout

```
src/qquotes/
  cli.py        # orchestration + printing
  config.py     # config.toml loading + constants
  history.py    # repeat-prevention fingerprint store
  wikiquote.py  # Wikiquote fetch/parse + MyMemory translation
  feeds.py      # zenquotes / type.fit / stoic fallback
```

Requests are throttled and retried with backoff on HTTP 429 to respect
Wikiquote's rate limits. All output is English.