# resume-skill-gap

Resume-to-posting skill-gap analysis: a Claude skill and a Python service.

## Repo layout
```
skill/                  # the Claude skill
  resume-skill-gap/     # uploadable folder (name matches SKILL.md frontmatter)
    SKILL.md
  tests/                # sample resumes, postings, expected outputs
  dist/                 # built zip (generated; don't edit by hand)
service/                # Python backend
docs/                   # design notes
README.md               # covers both skill and service
```

## Repo-wide rules
- Never include real resumes, names, or contact info anywhere in the repo; test data must be fictional.
- Never instruct Claude (or code) to bypass logins or scrape sites.
- No company names in any user-facing output — reference postings by number and role title only.

## Skill rules
- Nothing personal or role-specific in SKILL.md.
- Categories must work outside tech: tools/software, technical skills, certifications/licenses, domain knowledge, soft skills.
- Plain instructions only: no scripts and no package installs.
- Unreachable links are listed for the user to paste.
- Folder name must match the `name` in SKILL.md frontmatter.
- `description` stays under 200 characters and says when to use the skill.
- Instructions are short imperative steps, not essays.

## Service rules
- Tech-only scope: SWE, AI Engineer, Forward Deployed Engineer, and similar technical roles.
- Deterministic steps in code — AI is used only where judgement is needed (skill extraction, classification), not for control flow.
- AI output is always schema-validated and grounded in posting text.
- AI is never called in tests; use fixtures and recorded responses.

## Scoring (don't change without updating README)
required 1.0, unspecified 0.75, preferred 0.5, summed across distinct postings.

## When changing SKILL.md
1. Run all three test cases in `skill/tests/` (engineer, nurse, marketer) and compare against expected outputs.
2. Check that no gap is invented (every skill traces to posting text).
3. Update README if inputs, output format, or scoring changed.
4. Rebuild the zip: `cd skill && zip -r dist/resume-skill-gap.zip resume-skill-gap`
5. Add a line to CHANGELOG.md.
