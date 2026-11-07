# resume-skill-gap

A public Claude skill that compares a user's resume against job postings and ranks the skills they're missing. Meant for anyone, in any field, on any Claude plan.

## Repo layout
```
skill/                  # the Claude skill
  resume-skill-gap/     # uploadable folder (name matches SKILL.md frontmatter)
    SKILL.md
  tests/                # sample resumes, postings, expected outputs
  dist/                 # built zip (generated; don't edit by hand)
service/                # Python backend (planned)
docs/                   # design notes
README.md               # covers both skill and service
```

## Rules for the skill
- Nothing personal or role-specific in SKILL.md. Never include real resumes, names, or contact info anywhere in the repo; test data must be fictional.
- Categories must work outside tech: tools/software, technical skills, certifications/licenses, domain knowledge, soft skills.
- Plain instructions only: no scripts and no package installs.
- Never instruct Claude to bypass logins or scrape sites; unreachable links are listed for the user to paste.
- Folder name must match the `name` in SKILL.md frontmatter.
- `description` stays under 200 characters and says when to use the skill.

## Scoring (don't change without updating README)
required 1.0, unspecified 0.75, preferred 0.5, summed across distinct postings.

## When changing SKILL.md
1. Run all three test cases in `skill/tests/` (engineer, nurse, marketer) and compare against expected outputs.
2. Check that no gap is invented (every skill traces to posting text).
3. Update README if inputs, output format, or scoring changed.
4. Rebuild the zip: `cd skill && zip -r dist/resume-skill-gap.zip resume-skill-gap`
5. Add a line to CHANGELOG.md.

## Style
- Instructions in SKILL.md are short imperative steps, not essays.
