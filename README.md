# resume-skill-gap

A Claude skill that compares your resume against job postings and ranks the skills you're missing. Works for any industry — engineering, nursing, marketing, finance, or anything else.

## What it does

Give it your resume and one or more job postings. It extracts skills from both, separates "wording gaps" (skills you have but your resume doesn't say) from "true gaps" (skills you need to learn), and builds an HTML artifact with ranked tables, suggested resume rewrites, concrete next steps, experience-level checks, and visual strength bars. It also prints a quick text summary in chat so you get the headline immediately.

## Install

1. Download `resume-skill-gap.zip` from the [latest release](../../releases/latest) (or clone this repo).
2. Unzip it. You'll get a folder called `resume-skill-gap/` containing `SKILL.md`.
3. In Claude Code, go to **Customize > Skills** and upload the `resume-skill-gap/` folder.
4. Done. Use it by asking Claude to analyze your resume against job postings.

## Example prompt

```
Analyze my resume against these job postings:

Resume: [attach PDF or paste text]

Job postings:
https://careers.example.com/jobs/12345
https://apply.anothercompany.com/role/67890

---
Data Analyst — Acme Corp
Requirements:
- 3+ years experience with SQL and Python
- Experience with Tableau or Power BI
- Strong statistical analysis skills
Preferred:
- Experience with dbt or Airflow
- Familiarity with AWS or GCP
---
```

## Example output

You get two things:

**1. A quick text summary in chat:**

> Analyzed 3 postings (0 couldn't be opened). Top gaps: Tableau (required by 2/3), dbt (2/3). Strongest skills: SQL (3/3), Python (3/3), Statistical Analysis (2/3).

**2. An HTML artifact page with:**

- **Header** — posting count, numbered role chips (no company names), small-sample warning if < 5 postings.
- **Wording Gaps** — skills your resume demonstrates but doesn't name. Each row shows the posting keyword, a quote from your resume, and a suggested bullet rewrite. These are instant wins you can fix today.
- **True Gaps** — skills you need to learn, ranked by weighted score with color-coded pills (red = Required, amber = Preferred, grey = Unspecified). Each row includes evidence from the posting and a concrete next step (certification, project, or resume strategy). Top 15 shown.
- **Partial Matches** — what's asked vs. what your resume has, with gap explanation.
- **Experience & Seniority Check** — per-posting comparison of required experience vs. yours, with green/amber/red status.
- **Priority Gap cards** — the top 3–5 true gaps as numbered cards, each with a one-line rationale.
- **Strongest Skills bars** — horizontal bars showing how many postings match each of your skills.
- **Soft Skills** — tracked separately in a compact box.
- **Unopened Links** — status box listing any links that couldn't be read.

The page supports light and dark themes, works on mobile, and has no external dependencies beyond Google Fonts. Company names are never shown in the output.

## Limitations

- **Login-only links** (LinkedIn, Workday behind auth, some Greenhouse boards) cannot be opened. The skill lists them and asks you to paste the text.
- **Very long postings** may be truncated when read via browser tools. Core requirements and qualifications are prioritized.
- **Synonym normalization** covers common aliases but isn't exhaustive. If a skill appears under an unusual name, it may not merge automatically.
- **No scripts or automation** — this is a plain-text skill file. It runs as Claude instructions, not as code.

## License

MIT
