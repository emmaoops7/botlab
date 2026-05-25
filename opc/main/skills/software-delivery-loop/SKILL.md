---
name: software-delivery-loop
description: Master coordinator for software development work. Use by default for build features, fix bugs, refactor, test, deploy, release, rollback, production incidents, user feedback turned into product work, or any end-to-end software delivery task needing phase gates across operations, product, design, development, testing, release, and DevOps.
---

# Software Delivery Loop

Use this as the control plane for software work. Coordinate the smallest safe path from request to evidence-backed completion.

## Default rule

For development-class tasks, run phase gates unless the task is clearly trivial. Do not say complete without evidence.

Required delivery gates:
- Objective
- Acceptance
- User path
- Design states
- Changed files
- Validation evidence
- Risks
- Release/Rollback
- Monitoring/Feedback

Use `scripts/delivery_gate.py <summary.md>` to check final delivery summaries before declaring done.

## Role routing

| Need | Skill |
|---|---|
| User feedback, support signal, launch/onboarding, funnel | `software-operations` |
| Requirements, PRD, scope, acceptance criteria | `software-product-manager` |
| User flow, UI states, copy, accessibility, handoff | `software-designer` |
| Implementation, architecture, refactor, bug fix, code review | `software-developer` |
| Test plan, bug reproduction, regression, quality gate | `software-tester` |
| Release plan, go/no-go, changelog, rollback, post-release review | `software-release-manager` |
| CI/CD, deployment, infra, config, observability, incidents | `software-devops` |

If one role dominates, use that role skill. If work crosses roles, this skill owns sequencing and handoffs.

## Phase gates

| Gate | Minimum output |
|---|---|
| Objective | one-sentence goal and affected users |
| Acceptance | observable pass/fail criteria |
| User path | happy path and critical edge path |
| Design states | default, loading, empty, error, permission/disabled, success as relevant |
| Changed files | files/modules changed or planned |
| Validation evidence | commands, tests, screenshots, logs, or inspection results |
| Risks | known gaps, side effects, data/security/perf risk |
| Release/Rollback | release plan or rollback path |
| Monitoring/Feedback | smoke checks, metrics/logs, support/user feedback loop |

For planning-only tasks, mark unavailable gates as `N/A` with a reason.

## Inputs

- User request or incident/feedback signal
- Repository, product, environment, or release context
- Constraints: time, risk, stack, permissions, compliance

## Outputs

- Routed lifecycle plan, or completed delivery summary
- Required role handoffs
- Evidence-backed final status

## Handoff

Each phase hands off a compact artifact:
- Operations -> Product: signal, audience, pain, evidence, impact
- Product -> Design: PRD, scope, user stories, acceptance
- Design -> Development: flow, states, copy, accessibility, edge cases
- Development -> Testing: changed files, implementation notes, test targets
- Testing -> Release: pass/fail evidence, known risks
- Release -> DevOps: release notes, deploy/rollback plan
- DevOps -> Operations/Product: metrics, incidents, feedback, next iteration

## Done evidence

A task is done only when the summary includes the required gates and supporting evidence. For code changes, include changed files and validation output. For releases, include rollback and monitoring. For unresolved work, state the blocker and next decision.

## References

Load only when needed:
- `references/prd-template.md`
- `references/design-path-check.md`
- `references/test-matrix.md`
- `references/release-checklist.md`
- `references/devops-observability.md`
