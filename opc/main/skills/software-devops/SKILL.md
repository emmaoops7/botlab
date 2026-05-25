---
name: software-devops
description: DevOps and production operations skill. Use for deployment, CI/CD pipelines, build failures, runtime configuration, infrastructure, containers, logs, monitoring, alerting, observability, scaling, reliability, incident response, rollback execution, environment diagnosis, and production readiness.
---

# Software DevOps

Keep systems deployable, observable, and recoverable.

## Inputs

- Service/repo/environment, deploy target, runtime symptoms, CI/CD logs, release plan, rollback constraints
- Risk level and approval constraints for destructive or exposure-changing actions

## Outputs

- Environment diagnosis
- CI/CD fix or deployment plan
- Production readiness checklist
- Observability plan
- Incident triage
- Rollback procedure

## Workflow

1. Identify environment, version, scope, and user impact.
2. Inspect logs, health checks, metrics, CI/CD output, or config.
3. Mitigate first for incidents, then diagnose and fix.
4. Prepare deploy and rollback before changing production.
5. Verify with smoke tests, logs, health checks, metrics, or alerts.
6. Hand off monitoring and follow-up.

## Handoff

Hand off with:
- Status and affected services
- Commands/actions taken
- Evidence of deploy/recovery
- Monitoring and alert links or checks
- Rollback command/steps
- Follow-up risks

## Done evidence

Done when the system state is verified by logs, health checks, metrics, CI/CD result, or smoke test, and rollback/monitoring are documented.

## Production readiness checks

- Reproducible build
- Config/secrets separated
- Health checks
- Useful logs
- Metrics for traffic, errors, latency, saturation
- Alerts with owners/thresholds
- Rollback documented
- Migrations staged or reversible
