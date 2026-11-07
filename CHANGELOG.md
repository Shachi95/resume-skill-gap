# Changelog

## 2.0.0 — 2026-11-06

- Split gaps into **wording gaps** (skills you have but your resume doesn't say) and **true gaps** (skills to learn).
- Wording gaps include a suggested resume bullet rewrite; hard rule never to fabricate skills.
- True gaps include posting evidence quotes and a concrete next step (certification, project, or resume strategy).
- New **Experience & Seniority Check** section compares each posting's requirements against the resume.
- Small-sample warning when fewer than 5 postings are analyzed.
- Company names removed from all output — postings referenced by number and role title only.
- Updated all test cases and sample HTML outputs.

## 1.1.0 — 2026-11-06

- Output is now an HTML artifact instead of plain markdown tables.
- Visual improvements: color-coded priority pills, horizontal strength bars, numbered priority cards, posting chips.
- Theme-aware (light and dark), responsive layout.
- Short text summary printed in chat before the artifact.

## 1.0.0 — 2026-11-06

- Initial release.
- SKILL.md with five-step workflow: collect inputs, extract resume skills, extract posting skills, match and score, produce output.
- Scoring: required 1.0, unspecified 0.75, preferred 0.5, summed across distinct postings.
- Industry-agnostic categories: Tools/Software, Technical Skills, Certifications/Licenses, Domain Knowledge, Soft Skills.
- Three test cases: software engineer, registered nurse, marketing manager.
