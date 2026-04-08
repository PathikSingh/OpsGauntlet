"""Scenario definitions for the OpsGauntlet environment."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List


ALL_TOOLS = [
    "inspect_release_status",
    "inspect_service_metrics",
    "inspect_ci_failure",
    "pause_auto_rollout",
    "create_incident_ticket",
    "update_incident_ticket",
    "create_hotfix_branch",
    "apply_hotfix",
    "trigger_ci",
    "check_ci_status",
    "deploy_canary",
    "promote_canary",
    "rollback_release",
    "verify_recovery",
    "notify_slack",
    "update_status_page",
    "schedule_postmortem",
]


@dataclass(frozen=True)
class Task:
    task_id: str
    title: str
    difficulty: str
    briefing: str
    strategy: str
    max_steps: int
    score_basis: float
    hint: str
    available_tools: List[str]
    customer_facing: bool
    requires_ticket: bool
    requires_status_page: bool
    requires_slack: bool
    requires_postmortem: bool
    rollback_allowed: bool
    requires_rollout_pause: bool
    requires_recovery_verification: bool
    must_use_diagnostics: List[str]
    required_patch_id: str | None
    initial_world: Dict[str, object] = field(default_factory=dict)


TASK_BANK: List[Task] = [
    Task(
        task_id="rollback_alpha",
        title="Rollback a broken canary release",
        difficulty="easy",
        briefing=(
            "Version 2026.04.1 is producing 8.4% API errors after a canary rollout. "
            "Restore service quickly and notify the engineering channel."
        ),
        strategy="rollback",
        max_steps=6,
        score_basis=20.0,
        hint="Inspect release state and production metrics before rolling back.",
        available_tools=[
            "inspect_release_status",
            "inspect_service_metrics",
            "rollback_release",
            "notify_slack",
        ],
        customer_facing=False,
        requires_ticket=False,
        requires_status_page=False,
        requires_slack=True,
        requires_postmortem=False,
        rollback_allowed=True,
        requires_rollout_pause=False,
        requires_recovery_verification=False,
        must_use_diagnostics=["inspect_release_status", "inspect_service_metrics"],
        required_patch_id=None,
        initial_world={
            "production_version": "2026.04.0",
            "previous_version": "2026.03.9",
            "candidate_version": "2026.04.1",
            "incident_status": "degraded",
            "impacted_surface": "checkout-api",
            "error_rate_pct": 8.4,
            "latency_ms": 1860,
            "alerts": ["api_5xx_spike", "checkout_latency"],
        },
    ),
    Task(
        task_id="hotfix_ci_beta",
        title="Fix-forward a blocked release",
        difficulty="easy",
        briefing=(
            "Release 2026.04.2 is blocked by a CI failure in the auth packaging step. "
            "Patch the issue, pass CI, deploy safely, and confirm in Slack."
        ),
        strategy="fix_forward",
        max_steps=8,
        score_basis=25.0,
        hint="Read the CI failure before selecting a patch.",
        available_tools=[
            "inspect_ci_failure",
            "create_hotfix_branch",
            "apply_hotfix",
            "trigger_ci",
            "check_ci_status",
            "deploy_canary",
            "promote_canary",
            "notify_slack",
        ],
        customer_facing=False,
        requires_ticket=False,
        requires_status_page=False,
        requires_slack=True,
        requires_postmortem=False,
        rollback_allowed=False,
        requires_rollout_pause=False,
        requires_recovery_verification=False,
        must_use_diagnostics=["inspect_ci_failure"],
        required_patch_id="pin-auth-wheel",
        initial_world={
            "production_version": "2026.04.1",
            "previous_version": "2026.04.0",
            "candidate_version": "2026.04.2",
            "incident_status": "release_blocked",
            "impacted_surface": "auth-service",
            "error_rate_pct": 0.2,
            "latency_ms": 245,
            "alerts": ["ci_auth_packaging_failed"],
            "ci_failure_reason": "Missing wheel pin for auth dependency",
            "failing_check": "auth-build",
        },
    ),
    Task(
        task_id="public_payments_incident",
        title="Recover a customer-facing payments incident",
        difficulty="medium",
        briefing=(
            "A new payments release is causing transaction failures for customers. "
            "Recover service, track the incident properly, and close public comms."
        ),
        strategy="rollback",
        max_steps=10,
        score_basis=28.0,
        hint="Because customers are impacted, incident tracking and status-page closure matter.",
        available_tools=[
            "inspect_release_status",
            "inspect_service_metrics",
            "create_incident_ticket",
            "update_incident_ticket",
            "rollback_release",
            "notify_slack",
            "update_status_page",
        ],
        customer_facing=True,
        requires_ticket=True,
        requires_status_page=True,
        requires_slack=True,
        requires_postmortem=False,
        rollback_allowed=True,
        requires_rollout_pause=False,
        requires_recovery_verification=False,
        must_use_diagnostics=["inspect_release_status", "inspect_service_metrics"],
        required_patch_id=None,
        initial_world={
            "production_version": "2026.04.2",
            "previous_version": "2026.04.1",
            "candidate_version": "2026.04.3",
            "incident_status": "major_outage",
            "impacted_surface": "payments-api",
            "error_rate_pct": 17.9,
            "latency_ms": 2420,
            "alerts": ["payments_timeout", "payments_5xx", "checkout_drop"],
        },
    ),
    Task(
        task_id="auth_fix_forward",
        title="Fix-forward a security-sensitive auth release",
        difficulty="medium",
        briefing=(
            "Version 2026.04.4 introduced login failures, but rolling back would reintroduce "
            "a known auth vulnerability. Diagnose, patch, deploy safely, and communicate cleanly."
        ),
        strategy="fix_forward",
        max_steps=15,
        score_basis=35.0,
        hint="Rollback restores traffic but does not satisfy the security requirement.",
        available_tools=ALL_TOOLS,
        customer_facing=True,
        requires_ticket=True,
        requires_status_page=True,
        requires_slack=True,
        requires_postmortem=False,
        rollback_allowed=False,
        requires_rollout_pause=True,
        requires_recovery_verification=True,
        must_use_diagnostics=[
            "inspect_release_status",
            "inspect_service_metrics",
            "inspect_ci_failure",
        ],
        required_patch_id="fix-auth-token-refresh",
        initial_world={
            "production_version": "2026.04.3",
            "previous_version": "2026.04.2",
            "candidate_version": "2026.04.4",
            "incident_status": "partial_outage",
            "impacted_surface": "login-api",
            "error_rate_pct": 6.8,
            "latency_ms": 1310,
            "alerts": ["login_failures", "refresh_token_errors"],
            "ci_failure_reason": "Regression test for token refresh is failing",
            "failing_check": "auth-regression-suite",
        },
    ),
    Task(
        task_id="schema_migration_fix",
        title="Repair a release blocked by schema migration failure",
        difficulty="medium",
        briefing=(
            "The reporting release candidate cannot pass CI because a migration references "
            "the wrong column name. Fix the patch chain and complete deployment."
        ),
        strategy="fix_forward",
        max_steps=9,
        score_basis=25.0,
        hint="This is not a customer incident, so focus on diagnosis, CI, and safe rollout.",
        available_tools=[
            "inspect_ci_failure",
            "create_hotfix_branch",
            "apply_hotfix",
            "trigger_ci",
            "check_ci_status",
            "deploy_canary",
            "promote_canary",
            "verify_recovery",
            "notify_slack",
        ],
        customer_facing=False,
        requires_ticket=False,
        requires_status_page=False,
        requires_slack=True,
        requires_postmortem=False,
        rollback_allowed=False,
        requires_rollout_pause=False,
        requires_recovery_verification=True,
        must_use_diagnostics=["inspect_ci_failure"],
        required_patch_id="repair-schema-column",
        initial_world={
            "production_version": "2026.04.4",
            "previous_version": "2026.04.3",
            "candidate_version": "2026.04.5",
            "incident_status": "release_blocked",
            "impacted_surface": "reporting-worker",
            "error_rate_pct": 0.1,
            "latency_ms": 220,
            "alerts": ["ci_schema_migration_failed"],
            "ci_failure_reason": "Migration uses dropped column report_slug",
            "failing_check": "db-migration-check",
        },
    ),
    Task(
        task_id="customer_timeline_hard",
        title="Run a full incident lifecycle with postmortem hygiene",
        difficulty="hard",
        briefing=(
            "A customer-facing analytics deployment has degraded dashboards and triggered a "
            "severity-1 incident. Stabilize service, keep internal and public records accurate, "
            "and schedule a postmortem."
        ),
        strategy="rollback",
        max_steps=12,
        score_basis=38.0,
        hint="The service must be restored, ticket resolved, public status closed, and postmortem scheduled.",
        available_tools=ALL_TOOLS,
        customer_facing=True,
        requires_ticket=True,
        requires_status_page=True,
        requires_slack=True,
        requires_postmortem=True,
        rollback_allowed=True,
        requires_rollout_pause=True,
        requires_recovery_verification=True,
        must_use_diagnostics=["inspect_release_status", "inspect_service_metrics"],
        required_patch_id=None,
        initial_world={
            "production_version": "2026.04.5",
            "previous_version": "2026.04.4",
            "candidate_version": "2026.04.6",
            "incident_status": "sev1",
            "impacted_surface": "analytics-api",
            "error_rate_pct": 12.2,
            "latency_ms": 2140,
            "alerts": ["analytics_timeout", "dashboard_500s", "export_failures"],
        },
    ),
    Task(
        task_id="checkout_fix_forward_major",
        title="Contain and fix-forward a checkout incident",
        difficulty="hard",
        briefing=(
            "Checkout latency and 5xx rates spiked after release 2026.04.7. "
            "Pause the rollout, diagnose safely, patch forward, verify recovery, "
            "and close the incident with complete comms."
        ),
        strategy="fix_forward",
        max_steps=16,
        score_basis=40.0,
        hint="This scenario rewards containment before remediation and recovery verification before closure.",
        available_tools=ALL_TOOLS,
        customer_facing=True,
        requires_ticket=True,
        requires_status_page=True,
        requires_slack=True,
        requires_postmortem=True,
        rollback_allowed=False,
        requires_rollout_pause=True,
        requires_recovery_verification=True,
        must_use_diagnostics=[
            "inspect_release_status",
            "inspect_service_metrics",
            "inspect_ci_failure",
        ],
        required_patch_id="fix-checkout-retry-loop",
        initial_world={
            "production_version": "2026.04.6",
            "previous_version": "2026.04.5",
            "candidate_version": "2026.04.7",
            "incident_status": "sev1",
            "impacted_surface": "checkout-api",
            "error_rate_pct": 10.1,
            "latency_ms": 1960,
            "alerts": ["checkout_5xx", "checkout_latency", "payment_drop"],
            "ci_failure_reason": "Retry loop patch is missing a checkout timeout guard",
            "failing_check": "checkout-regression-suite",
        },
    ),
    Task(
        task_id="orders_pause_and_rollback",
        title="Pause rollout and rollback an orders release",
        difficulty="medium",
        briefing=(
            "The orders service is degrading while a new regional rollout is still expanding. "
            "Contain the blast radius, rollback, verify recovery, and communicate the resolution."
        ),
        strategy="rollback",
        max_steps=9,
        score_basis=28.0,
        hint="Stopping rollout expansion before rollback demonstrates better operational judgment.",
        available_tools=[
            "inspect_release_status",
            "inspect_service_metrics",
            "pause_auto_rollout",
            "rollback_release",
            "verify_recovery",
            "notify_slack",
        ],
        customer_facing=False,
        requires_ticket=False,
        requires_status_page=False,
        requires_slack=True,
        requires_postmortem=False,
        rollback_allowed=True,
        requires_rollout_pause=True,
        requires_recovery_verification=True,
        must_use_diagnostics=["inspect_release_status", "inspect_service_metrics"],
        required_patch_id=None,
        initial_world={
            "production_version": "2026.04.7",
            "previous_version": "2026.04.6",
            "candidate_version": "2026.04.8",
            "incident_status": "degraded",
            "impacted_surface": "orders-api",
            "error_rate_pct": 7.3,
            "latency_ms": 1480,
            "alerts": ["orders_queue_backup", "orders_latency"],
        },
    ),
    Task(
        task_id="database_rollback_simple",
        title="Rollback a database-impacting release",
        difficulty="easy",
        briefing=(
            "Release 2026.04.9 is corrupting database writes on the user service. "
            "Error rate is 5.1%. Roll back and notify the team."
        ),
        strategy="rollback",
        max_steps=6,
        score_basis=20.0,
        hint="Inspect first, then rollback, then notify.",
        available_tools=[
            "inspect_release_status",
            "inspect_service_metrics",
            "rollback_release",
            "notify_slack",
        ],
        customer_facing=False,
        requires_ticket=False,
        requires_status_page=False,
        requires_slack=True,
        requires_postmortem=False,
        rollback_allowed=True,
        requires_rollout_pause=False,
        requires_recovery_verification=False,
        must_use_diagnostics=["inspect_release_status", "inspect_service_metrics"],
        required_patch_id=None,
        initial_world={
            "production_version": "2026.04.8",
            "previous_version": "2026.04.7",
            "candidate_version": "2026.04.9",
            "incident_status": "degraded",
            "impacted_surface": "user-service",
            "error_rate_pct": 5.1,
            "latency_ms": 1200,
            "alerts": ["db_write_errors", "user_service_degraded"],
        },
    ),
    Task(
        task_id="api_gateway_fix_forward",
        title="Fix-forward a broken API gateway release",
        difficulty="medium",
        briefing=(
            "The API gateway candidate is failing CI due to a missing rate-limit "
            "config. Patch it, pass CI, deploy safely, verify recovery, and notify the team."
        ),
        strategy="fix_forward",
        max_steps=10,
        score_basis=28.0,
        hint="Read the CI failure before picking a patch.",
        available_tools=[
            "inspect_ci_failure",
            "create_hotfix_branch",
            "apply_hotfix",
            "trigger_ci",
            "check_ci_status",
            "deploy_canary",
            "promote_canary",
            "verify_recovery",
            "notify_slack",
        ],
        customer_facing=False,
        requires_ticket=False,
        requires_status_page=False,
        requires_slack=True,
        requires_postmortem=False,
        rollback_allowed=False,
        requires_rollout_pause=False,
        requires_recovery_verification=True,
        must_use_diagnostics=["inspect_ci_failure"],
        required_patch_id="add-ratelimit-config",
        initial_world={
            "production_version": "2026.04.9",
            "previous_version": "2026.04.8",
            "candidate_version": "2026.04.10",
            "incident_status": "release_blocked",
            "impacted_surface": "api-gateway",
            "error_rate_pct": 0.3,
            "latency_ms": 300,
            "alerts": ["ci_ratelimit_config_missing"],
            "ci_failure_reason": "Missing rate-limit config in gateway manifest",
            "failing_check": "gateway-config-check",
        },
    ),
    Task(
        task_id="notification_service_sev2",
        title="Handle a sev2 notification service incident",
        difficulty="medium",
        briefing=(
            "Push notification delivery is failing for 9% of requests after a "
            "new release. Track the incident, roll back, and close communications cleanly."
        ),
        strategy="rollback",
        max_steps=10,
        score_basis=28.0,
        hint="Create the ticket before rolling back so you have an incident ID for updates.",
        available_tools=[
            "inspect_release_status",
            "inspect_service_metrics",
            "create_incident_ticket",
            "update_incident_ticket",
            "rollback_release",
            "notify_slack",
            "update_status_page",
        ],
        customer_facing=True,
        requires_ticket=True,
        requires_status_page=True,
        requires_slack=True,
        requires_postmortem=False,
        rollback_allowed=True,
        requires_rollout_pause=False,
        requires_recovery_verification=False,
        must_use_diagnostics=["inspect_release_status", "inspect_service_metrics"],
        required_patch_id=None,
        initial_world={
            "production_version": "2026.04.10",
            "previous_version": "2026.04.9",
            "candidate_version": "2026.04.11",
            "incident_status": "partial_outage",
            "impacted_surface": "notification-service",
            "error_rate_pct": 9.2,
            "latency_ms": 1750,
            "alerts": ["push_delivery_failures", "notification_queue_backup"],
        },
    ),
    Task(
        task_id="ml_pipeline_hard",
        title="Recover a broken ML inference pipeline with full incident lifecycle",
        difficulty="hard",
        briefing=(
            "The ML inference service returned garbage predictions after a model "
            "deployment. A sev1 incident is declared. Stabilize it, track it completely, "
            "and ensure postmortem hygiene."
        ),
        strategy="rollback",
        max_steps=14,
        score_basis=40.0,
        hint=(
            "Pause rollout first to contain the bad model. Full lifecycle means ticket "
            "opened and closed, status page opened and closed, slack sent, postmortem scheduled."
        ),
        available_tools=ALL_TOOLS,
        customer_facing=True,
        requires_ticket=True,
        requires_status_page=True,
        requires_slack=True,
        requires_postmortem=True,
        rollback_allowed=True,
        requires_rollout_pause=True,
        requires_recovery_verification=True,
        must_use_diagnostics=["inspect_release_status", "inspect_service_metrics"],
        required_patch_id=None,
        initial_world={
            "production_version": "2026.04.11",
            "previous_version": "2026.04.10",
            "candidate_version": "2026.04.12",
            "incident_status": "sev1",
            "impacted_surface": "ml-inference-api",
            "error_rate_pct": 15.5,
            "latency_ms": 2800,
            "alerts": ["ml_prediction_errors", "inference_latency_spike", "customer_reports"],
        },
    ),
]


def get_random_task(seed: int | None = None) -> Task:
    rng = random.Random(seed)
    return rng.choice(TASK_BANK)


def get_task_by_id(task_id: str) -> Task:
    for task in TASK_BANK:
        if task.task_id == task_id:
            return task
    raise KeyError(f"Unknown task_id: {task_id}")
