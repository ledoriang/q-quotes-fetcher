#!/usr/bin/env python3
"""Thin entry point so `uv run src/get_passages.py` still works."""
import sys

from qquotes.cli import main

if __name__ == "__main__":
    sys.exit(main())