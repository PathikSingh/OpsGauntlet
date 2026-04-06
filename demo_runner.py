"""Simple CLI demo runner for OpsGauntlet."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from opsgauntlet.models import OpsGauntletAction, ToolCallRequest
from opsgauntlet.server.environment import OpsGauntletEnvironment


@dataclass(frozen=True)
class DemoStep:
    tool_name: str
    parameters: dict
    reasoning: str


DEMO_PLANS: dict[str, list[DemoStep]] = {
    "public_payments_incident": [
        DemoStep("inspect_release_status", {}, "Start by checking which release is active and what can be rolled back."),
        DemoStep("inspect_service_metrics", {}, "Confirm the incident severity from live telemetry."),
        DemoStep("create_incident_ticket", {"title": "Payments outage", "severity": "sev1"}, "Open formal incident tracking before executing changes."),
        DemoStep("rollback_release", {"target_version": "2026.04.1"}, "Fastest safe remediation is rollback to the previous known-good version."),
        DemoStep("update_status_page", {"status": "resolved", "message": "Payments recovered after rollback to previous stable release."}, "Close public comms only after service recovery."),
        DemoStep("update_incident_ticket", {"incident_id": "INC-1", "status": "resolved", "summary": "Rollback restored payments traffic."}, "Reflect the technical resolution in the ticket."),
        DemoStep("notify_slack", {"channel": "#payments", "message": "Payments incident resolved after rollback to 2026.04.1."}, "Send the internal resolution update."),
    ],
    "checkout_fix_forward_major": [
        DemoStep("inspect_release_status", {}, "Map the active release and candidate before making changes."),
        DemoStep("inspect_service_metrics", {}, "Confirm customer impact and incident severity."),
        DemoStep("inspect_ci_failure", {}, "Read the failing signal before choosing a patch."),
        DemoStep("pause_auto_rollout", {"reason": "Freeze blast radius while hotfix is prepared."}, "Contain the incident before remediation."),
        DemoStep("create_incident_ticket", {"title": "Checkout sev1 incident", "severity": "sev1"}, "Open a tracked incident."),
        DemoStep("create_hotfix_branch", {"branch_name": "hotfix/checkout-timeout-guard"}, "Prepare a branch for the fix-forward path."),
        DemoStep("apply_hotfix", {"branch_name": "hotfix/checkout-timeout-guard", "patch_id": "fix-checkout-retry-loop"}, "Apply the patch that matches the diagnosed CI failure."),
        DemoStep("trigger_ci", {"branch_name": "hotfix/checkout-timeout-guard"}, "Run CI against the hotfix branch."),
        DemoStep("check_ci_status", {"run_id": "run-2"}, "Ensure the hotfix passes validation."),
        DemoStep("deploy_canary", {"run_id": "run-2"}, "Roll out safely using canary deployment."),
        DemoStep("promote_canary", {"deployment_id": "deploy-3"}, "Promote only after the canary is healthy."),
        DemoStep("verify_recovery", {}, "Verify service health before closing the incident."),
        DemoStep("update_status_page", {"status": "resolved", "message": "Checkout recovered after fix-forward patch and canary promotion."}, "Close public communication after verification."),
        DemoStep("update_incident_ticket", {"incident_id": "INC-1", "status": "resolved", "summary": "Fix-forward patch restored checkout reliability."}, "Close internal incident tracking."),
        DemoStep("notify_slack", {"channel": "#incident-review", "message": "Checkout incident resolved after containment, patch, and canary promotion."}, "Update internal stakeholders."),
        DemoStep("schedule_postmortem", {"incident_id": "INC-1", "owner": "release-ops"}, "Complete the final operational hygiene step."),
    ],
}


def run_demo(task_id: str) -> None:
    if task_id not in DEMO_PLANS:
        raise SystemExit(f"Unknown demo task: {task_id}. Available: {', '.join(sorted(DEMO_PLANS))}")

    env = OpsGauntletEnvironment()
    observation = env.reset(task_id=task_id)

    print(f"\n=== {observation.title} ({observation.task_id}) ===")
    print(observation.briefing)
    print(f"Available tools: {', '.join(observation.available_tools)}")
    print()

    for index, demo_step in enumerate(DEMO_PLANS[task_id], start=1):
        result = env.step(
            OpsGauntletAction(
                tool_call=ToolCallRequest(
                    tool_name=demo_step.tool_name,
                    parameters=demo_step.parameters,
                    reasoning=demo_step.reasoning,
                )
            )
        )
        tool_result = result.last_tool_result
        print(f"[{index}] {demo_step.tool_name}")
        print(f"  reasoning: {demo_step.reasoning}")
        print(f"  reward: {result.reward}")
        print(f"  success: {tool_result.success if tool_result else 'n/a'}")
        if tool_result:
            print(f"  summary: {tool_result.summary}")
        print(f"  objectives: {', '.join(result.completed_objectives) or 'none'}")
        print(f"  service: status={result.service_snapshot.incident_status}, canary={result.service_snapshot.canary_status}, ticket={result.service_snapshot.ticket_status}")
        print(f"  telemetry: error_rate={result.signal_snapshot.error_rate_pct} latency={result.signal_snapshot.latency_ms}")
        print()
        if result.done:
            print(f"Terminal outcome: {result.metadata.get('terminal_outcome')}")
            break


def main(args: Iterable[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run a scripted demo for OpsGauntlet.")
    parser.add_argument(
        "task_id",
        nargs="?",
        default="public_payments_incident",
        help=f"Task to demo. Available: {', '.join(sorted(DEMO_PLANS))}",
    )
    parsed = parser.parse_args(list(args) if args is not None else None)
    run_demo(parsed.task_id)


if __name__ == "__main__":
    main()
