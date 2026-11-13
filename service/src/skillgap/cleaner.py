"""HTML cleaner: extract main content text, strip boilerplate."""

from __future__ import annotations

import trafilatura  # type: ignore[import-untyped]
from bs4 import BeautifulSoup


def _strip_boilerplate(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["nav", "footer", "header", "script", "style", "noscript"]):
        tag.decompose()
    return soup


def _fallback_clean(html: str) -> str:
    return _strip_boilerplate(html).get_text(separator="\n", strip=True)


def clean(html: str) -> str:
    """Extract main content from HTML, stripping boilerplate.

    Uses trafilatura as the primary extractor; falls back to
    BeautifulSoup tag-stripping if trafilatura returns nothing.
    """
    stripped = str(_strip_boilerplate(html))
    result: str | None = trafilatura.extract(stripped)
    if result and result.strip():
        return result
    return _fallback_clean(html)
