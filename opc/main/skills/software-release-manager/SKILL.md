---
name: software-release-manager
description: Release management skill for software launches. Use for release planning, go/no-go decisions, versioning, changelogs, release notes, phased rollout, hotfix coordination, stakeholder communication, rollback plans, launch readiness, production verification, and post-release review.
---

# Software Release Manager

Coordinate readiness, risk, communication, rollout, and rollback.

## Inputs

- Scope, changed files/features, acceptance results, test evidence, risks, deploy constraints
- Stakeholders, users affected, and timing

## Outputs

- Release checklist
- Go/no-go decision
- Rollout plan
- Rollback plan
- Release notes/changelog
- Post-release review

## Workflow

1. Confirm scope and user impact.
2. Check product, design, development, testing, observability, support, and rollback readiness.
3. Decide go/no-go using evidence.
4. Define rollout, verification, communication, and rollback triggers.
5. Capture post-release metrics, incidents, and follow-ups.

## Handoff

Hand off to DevOps/Operations with:
- Release scope and version
- Validation evidence
- Rollout stages
- Rollback trigger and steps
- Smoke checks and monitoring
- Communication/support notes

## Done evidence

Done when go/no-go is explicit, release/rollback plan exists, validation evidence is referenced, and post-release monitoring/feedback is assigned.

## Release skeleton

```markdown
Objective:
Acceptance:
Changed files:
Validation evidence:
Risks:
Release plan:
Rollback:
Monitoring/Feedback:
```
