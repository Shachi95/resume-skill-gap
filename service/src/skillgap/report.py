"""JSON and HTML report generation from ranked gaps."""

from __future__ import annotations

import json
from collections.abc import Sequence
from html import escape

from skillgap.models import RankedGap

_CSS = """\
:root {
  color-scheme: light dark;
  --bg: #faf9f7;
  --fg: #1f1e1d;
  --muted: #6b6a66;
  --card: #ffffff;
  --border: #e3e0da;
  --accent: #c2410c;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1c1b19;
    --fg: #ecebe8;
    --muted: #a09e98;
    --card: #262522;
    --border: #3a3935;
    --accent: #fb923c;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 2rem 1rem;
  background: var(--bg);
  color: var(--fg);
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  line-height: 1.5;
}
main { max-width: 52rem; margin: 0 auto; }
h1 { font-size: 1.6rem; margin: 0 0 0.25rem; }
p.sub { color: var(--muted); margin: 0 0 1.5rem; }
ol.gaps { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.75rem; }
li.gap {
  display: grid;
  grid-template-columns: 2.5rem 1fr auto;
  gap: 0.75rem;
  align-items: center;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 0.6rem;
  padding: 0.75rem 1rem;
}
.rank { color: var(--accent); font-weight: 700; font-size: 1.1rem; }
.skill { font-weight: 600; }
.meta { color: var(--muted); font-size: 0.85rem; }
.score { font-weight: 700; font-variant-numeric: tabular-nums; }
@media (max-width: 36rem) {
  li.gap { grid-template-columns: 2rem 1fr; }
  .score { grid-column: 2; }
}
"""


def generate_json_report(ranked: Sequence[RankedGap]) -> str:
    """Serialize ranked gaps to a JSON array string."""
    return json.dumps([r.model_dump(mode="json") for r in ranked], indent=2, ensure_ascii=False)


def _item(r: RankedGap) -> str:
    g = r.gap
    category = escape(g.category.value.replace("_", " "))
    return (
        '    <li class="gap">\n'
        f'      <span class="rank">{r.rank}</span>\n'
        "      <div>\n"
        f'        <div class="skill">{escape(g.skill)}</div>\n'
        f'        <div class="meta">{category} &middot; '
        f"{g.required_count} required &middot; {g.preferred_count} preferred &middot; "
        f"{g.posting_count} postings</div>\n"
        "      </div>\n"
        f'      <span class="score">{g.score:g}</span>\n'
        "    </li>"
    )


def generate_html_report(ranked: Sequence[RankedGap]) -> str:
    """Render ranked gaps as a standalone, theme-aware HTML document."""
    if ranked:
        body = '  <ol class="gaps">\n' + "\n".join(_item(r) for r in ranked) + "\n  </ol>"
    else:
        body = "  <p>No skill gaps found.</p>"
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "  <title>Skill gap report</title>\n"
        f"  <style>\n{_CSS}  </style>\n"
        "</head>\n"
        "<body>\n"
        "<main>\n"
        "  <h1>Skill gap report</h1>\n"
        '  <p class="sub">Skills in the postings that are missing from your resume, '
        "highest score first.</p>\n"
        f"{body}\n"
        "</main>\n"
        "</body>\n"
        "</html>\n"
    )
