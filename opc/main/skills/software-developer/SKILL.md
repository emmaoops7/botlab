---
name: software-developer
description: Senior software development skill. Use for implementing features, fixing bugs, refactoring, code review, repository inspection, architecture, APIs, database changes, dependency changes, migrations, performance, security-sensitive code changes, and production-ready engineering with tests and validation evidence.
---

# Software Developer

Deliver small, reviewable, tested changes.

## Inputs

- Objective, acceptance criteria, user path, design states if UI-related
- Repository context, bug reproduction, constraints, and risk level

## Outputs

- Minimal code change
- Implementation notes
- Changed files
- Validation evidence
- Risks and rollback notes

## Workflow

1. Inspect repo structure and existing conventions.
2. Reproduce bug or verify current behavior when relevant.
3. Define the smallest reversible change.
4. Edit surgically; separate refactor from behavior change.
5. Run the narrowest meaningful validation, then broader checks if risk requires.
6. Report changed files, validation output, risks, and rollback.

## Handoff

Hand off to testing/release with:
- Objective and acceptance covered
- Changed files/modules
- Behavior changed
- Tests/checks run and results
- Known gaps, risks, rollback

## Done evidence

Done only when changed files and validation evidence are present. If validation cannot run, state why and provide the best available evidence.

## Bug fix loop

```text
reproduce -> isolate -> minimal fix -> verify same check passes -> regression guard
```

## Final summary skeleton

```markdown
Objective:
Acceptance:
User path:
Changed files:
Validation evidence:
Risks:
Rollback or Release plan:
Monitoring/Feedback:
```
