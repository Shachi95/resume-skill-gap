"""Posting parser: orchestrates clean -> split -> Posting model."""

from __future__ import annotations

import hashlib

from skillgap.cleaner import clean
from skillgap.models import Posting
from skillgap.splitter import split_sections


def _url_to_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:12]


def _extract_title(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            if stripped.lower().startswith("role:"):
                return stripped[5:].strip()
            return stripped
    return "Unknown"


def parse_posting(*, url: str, html: str) -> Posting:
    """Parse raw HTML into a Posting model.

    Cleans the HTML to plain text, splits into labeled sections,
    and extracts a title from the first non-empty line.
    """
    text = clean(html)
    sections = split_sections(text)
    title = _extract_title(text)
    return Posting(
        id=_url_to_id(url),
        title=title,
        url=url,
        text=text,
        sections=sections,
    )
