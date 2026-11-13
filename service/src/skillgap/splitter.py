"""Section splitter: regex-first approach for job posting text."""

from __future__ import annotations

import re

_HEADING_RE = re.compile(
    r"^("
    r"requirements|qualifications|minimum qualifications"
    r"|preferred|preferred qualifications|nice to have"
    r"|responsibilities|what you.ll do|key responsibilities"
    r"|about the role|about this role|description"
    r"|who you are|what we.re looking for"
    r")\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

_HEADING_ALIASES: dict[str, str] = {
    "qualifications": "requirements",
    "minimum qualifications": "requirements",
    "preferred qualifications": "preferred",
    "nice to have": "preferred",
    "what you'll do": "responsibilities",
    "what you’ll do": "responsibilities",  # noqa: RUF001
    "key responsibilities": "responsibilities",
    "about the role": "description",
    "about this role": "description",
    "who you are": "requirements",
    "what we're looking for": "requirements",
    "what we’re looking for": "requirements",  # noqa: RUF001
}


def split_sections(text: str) -> dict[str, str]:
    """Split posting text into labeled sections.

    Returns a dict with lowercase keys like "requirements", "preferred",
    "responsibilities". Uses regex to detect standard headings.
    """
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return {}

    sections: dict[str, str] = {}
    for i, match in enumerate(matches):
        heading_raw = match.group(1).strip().lower()
        heading = _HEADING_ALIASES.get(heading_raw, heading_raw)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            if heading in sections:
                sections[heading] += "\n" + body
            else:
                sections[heading] = body

    return sections
