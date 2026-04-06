"""Mock operational tools for the OpsGauntlet environment."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

try:
    from ..models import ToolResult
except ImportError:  # pragma: no cover
    from models import ToolResult  # type: ignore
from .task_bank import Task


class ToolRegistry:
    """Registry of simulated operational tools."""

    TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
        "inspect_release_status": {
            "description": "Inspect current production, previous, and candidate release state.",
            "required_params": [],
            "optional_params": [],
        },
        "inspect_service_metrics": {
            "description": "Inspect production telemetry before remediation.",
            "required_params": [],
            "optional_params": [],
        },
        "inspect_ci_failure": {
            "description": "Inspect the reason the current CI run or candidate release is failing.",
            "required_params": [],
            "optional_params": [],
        },
        "pause_auto_rollout": {
            "description": "Pause further rollout expansion to contain blast radius.",
            "required_params": ["reason"],
            "optional_params": [],
        },
        "create_incident_ticket": {
            "description": "Open an incident or release ticket for coordinated response.",
            "required_params": ["title", "severity"],
            "optional_params": ["owner"],
        },
        "update_incident_ticket": {
            "description": "Update the incident ticket with status and summary.",
            "required_params": ["incident_id", "status", "summary"],
            "optional_params": [],
        },
        "create_hotfix_branch": {
            "description": "Create a hotfix branch for fix-forward work.",
            "required_params": ["branch_name"],
            "optional_params": [],
        },
        "apply_hotfix": {
            "description": "Apply a named patch to the hotfix branch.",
            "required_params": ["branch_name", "patch_id"],
            "optional_params": ["notes"],
        },
        "trigger_ci": {
            "description": "Trigger CI for the hotfix branch.",
            "required_params": ["branch_name"],
            "optional_params": [],
        },
        "check_ci_status": {
            "description": "Check the latest CI run result.",
            "required_params": ["run_id"],
            "optional_params": [],
        },
        "deploy_canary": {
            "description": "Deploy the fixed candidate to a canary slice.",
            "required_params": ["run_id"],
            "optional_params": [],
        },
        "promote_canary": {
            "description": "Promote a healthy canary to production.",
            "required_params": ["deployment_id"],
            "optional_params": [],
        },
        "rollback_release": {
            "description": "Rollback production to the previous known-good release.",
            "required_params": ["target_version"],
            "optional_params": ["reason"],
        },
        "verify_recovery": {
            "description": "Verify that production health has stabilized after remediation.",
            "required_params": [],
            "optional_params": ["checkpoint"],
        },
        "notify_slack": {
            "description": "Send an internal operational update to Slack.",
            "required_params": ["channel", "message"],
            "optional_params": [],
        },
        "update_status_page": {
            "description": "Update the public status page during a customer-facing incident.",
            "required_params": ["status", "message"],
            "optional_params": [],
        },
        "schedule_postmortem": {
            "description": "Schedule the incident postmortem after recovery.",
            "required_params": ["incident_id", "owner"],
            "optional_params": ["date"],
        },
    }

    def execute(self, tool_name: str, params: Dict[str, Any], world: Dict[str, Any], task: Task) -> ToolResult:
        handler = getattr(self, f"_{tool_name}", None)
        if handler is None:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                summary="Unknown tool.",
                error=f"Unknown tool: {tool_name}",
                tags=["unknown_tool"],
            )
        return handler(params, world, task)

    def schemas_for(self, tool_names: list[str]) -> Dict[str, Dict[str, Any]]:
        return {name: deepcopy(self.TOOL_SCHEMAS[name]) for name in tool_names}

    def _inspect_release_status(self, params: Dict[str, Any], world: Dict[str, Any], task: Task) -> ToolResult:
        world["flags"]["inspected_release"] = True
        return ToolResult(
            tool_name="inspect_release_status",
            success=True,
            summary="Fetched release topology and active rollout state.",
            output={
                "production_version": world["production_version"],
                "previous_version": world["previous_version"],
                "candidate_version": world["candidate_version"],
                "incident_status": world["incident_status"],
            },
            tags=["diagnostic"],
        )

    def _inspect_service_metrics(self, params: Dict[str, Any], world: Dict[str, Any], task: Task) -> ToolResult:
        world["flags"]["inspected_metrics"] = True
        return ToolResult(
            tool_name="inspect_service_metrics",
            success=True,
            summary="Fetched live telemetry for the impacted service.",
            output={
                "error_rate_pct": world["error_rate_pct"],
                "latency_ms": world["latency_ms"],
                "alerts": list(world["alerts"]),
                "impacted_surface": world["impacted_surface"],
            },
            tags=["diagnostic"],
        )

    def _inspect_ci_failure(self, params: Dict[str, Any], world: Dict[str, Any], task: Task) -> ToolResult:
        reason = world.get("ci_failure_reason")
        if not reason:
            return ToolResult(
                tool_name="inspect_ci_failure",
                success=False,
                summary="There is no actionable CI failure to inspect right now.",
                error="No CI failure is currently active.",
                tags=["precondition_failed"],
            )
        world["flags"]["inspected_ci"] = True
        return ToolResult(
            tool_name="inspect_ci_failure",
            success=True,
            summary="Fetched CI failure details for the candidate release.",
            output={
                "failure_reason": reason,
                "failing_check": world.get("failing_check", "unknown"),
            },
            tags=["diagnostic"],
        )

    def _pause_auto_rollout(self, params: Dict[str, Any], world: Dict[str, Any], task: Task) -> ToolResult:
        reason = params.get("reason")
        if not reason:
            return self._missing("pause_auto_rollout", "reason is required")
        if world.get("auto_rollout_paused"):
            return ToolResult(
                tool_name="pause_auto_rollout",
                success=False,
                summary="Automatic rollout is already paused.",
                error="Rollout is already paused.",
                tags=["redundant"],
            )
        world["auto_rollout_paused"] = True
        return ToolResult(
            tool_name="pause_auto_rollout",
            success=True,
            summary="Paused automatic rollout expansion.",
            output={"auto_rollout_paused": True},
            tags=["containment"],
        )

    def _create_incident_ticket(self, params: Dict[str, Any], world: Dict[str, Any], task: Task) -> ToolResult:
        title = params.get("title")
        severity = params.get("severity")
        if not title or not severity:
            return self._missing("create_incident_ticket", "title and severity are required")
        if world.get("incident_id"):
            return ToolResult(
                tool_name="create_incident_ticket",
                success=False,
                summary="Incident ticket already exists.",
                error="Incident ticket already exists.",
                tags=["redundant"],
            )
        incident_id = f"INC-{world['sequence']}"
        world["sequence"] += 1
        world["incident_id"] = incident_id
        world["ticket_status"] = "open"
        return ToolResult(
            tool_name="create_incident_ticket",
            success=True,
            summary=f"Created incident ticket {incident_id}.",
            output={"incident_id": incident_id, "severity": severity},
            tags=["ticketing"],
        )

    def _update_incident_ticket(self, params: Dict[str, Any], world: Dict[str, Any], task: Task) -> ToolResult:
        incident_id = params.get("incident_id")
        status = params.get("status")
        summary = params.get("summary")
        if not incident_id or not status or not summary:
            return self._missing("update_incident_ticket", "incident_id, status, and summary are required")
        if incident_id != world.get("incident_id"):
            return ToolResult(
                tool_name="update_incident_ticket",
                success=False,
                summary="Incident ID did not match the active incident.",
                error="Incident not found.",
                tags=["precondition_failed"],
            )
        if status in {"resolved", "closed"} and not world.get("service_recovered"):
            return ToolResult(
                tool_name="update_incident_ticket",
                success=False,
                summary="Cannot resolve the incident before production is healthy.",
                error="Recover the service before closing the incident.",
                tags=["unsafe_action"],
            )
        world["ticket_status"] = status
        return ToolResult(
            tool_name="update_incident_ticket",
            success=True,
            summary=f"Incident ticket moved to {status}.",
            output={"incident_id": incident_id, "status": status},
            tags=["ticketing"],
        )

    def _create_hotfix_branch(self, params: Dict[str, Any], world: Dict[str, Any], task: Task) -> ToolResult:
        branch_name = params.get("branch_name")
        if not branch_name:
            return self._missing("create_hotfix_branch", "branch_name is required")
        world["hotfix_branch"] = branch_name
        return ToolResult(
            tool_name="create_hotfix_branch",
            success=True,
            summary=f"Created hotfix branch {branch_name}.",
            output={"branch_name": branch_name},
            tags=["remediation"],
        )

    def _apply_hotfix(self, params: Dict[str, Any], world: Dict[str, Any], task: Task) -> ToolResult:
        branch_name = params.get("branch_name")
        patch_id = params.get("patch_id")
        if not branch_name or not patch_id:
            return self._missing("apply_hotfix", "branch_name and patch_id are required")
        if branch_name != world.get("hotfix_branch"):
            return ToolResult(
                tool_name="apply_hotfix",
                success=False,
                summary="Hotfix branch does not exist yet.",
                error="Create the hotfix branch before applying a patch.",
                tags=["precondition_failed"],
            )
        world["applied_patch_id"] = patch_id
        world["patch_correct"] = patch_id == task.required_patch_id
        return ToolResult(
            tool_name="apply_hotfix",
            success=True,
            summary=f"Applied patch {patch_id} on {branch_name}.",
            output={"branch_name": branch_name, "patch_id": patch_id, "patch_correct": world["patch_correct"]},
            tags=["remediation"],
        )

    def _trigger_ci(self, params: Dict[str, Any], world: Dict[str, Any], task: Task) -> ToolResult:
        branch_name = params.get("branch_name")
        if not branch_name:
            return self._missing("trigger_ci", "branch_name is required")
        if branch_name != world.get("hotfix_branch"):
            return ToolResult(
                tool_name="trigger_ci",
                success=False,
                summary="No matching hotfix branch found for CI.",
                error="Create the branch and apply the patch first.",
                tags=["precondition_failed"],
            )
        run_id = f"run-{world['sequence']}"
        world["sequence"] += 1
        world["latest_ci_run_id"] = run_id
        will_pass = bool(world.get("patch_correct"))
        world["ci_runs"][run_id] = {"status": "running", "will_pass": will_pass}
        world["ci_status"] = "running"
        return ToolResult(
            tool_name="trigger_ci",
            success=True,
            summary=f"Triggered CI run {run_id}.",
            output={"run_id": run_id, "status": "running"},
            tags=["ci"],
        )

    def _check_ci_status(self, params: Dict[str, Any], world: Dict[str, Any], task: Task) -> ToolResult:
        run_id = params.get("run_id")
        if not run_id:
            return self._missing("check_ci_status", "run_id is required")
        run = world["ci_runs"].get(run_id)
        if run is None:
            return ToolResult(
                tool_name="check_ci_status",
                success=False,
                summary="Unknown CI run.",
                error="run_id does not exist.",
                tags=["precondition_failed"],
            )
        run["status"] = "passed" if run["will_pass"] else "failed"
        world["ci_status"] = run["status"]
        if run["status"] == "passed":
            world["ci_failure_reason"] = None
            world["failing_check"] = None
            summary = f"CI run {run_id} passed."
        else:
            summary = f"CI run {run_id} failed."
        return ToolResult(
            tool_name="check_ci_status",
            success=True,
            summary=summary,
            output={"run_id": run_id, "status": run["status"]},
            tags=["ci"],
        )

    def _deploy_canary(self, params: Dict[str, Any], world: Dict[str, Any], task: Task) -> ToolResult:
        run_id = params.get("run_id")
        if not run_id:
            return self._missing("deploy_canary", "run_id is required")
        run = world["ci_runs"].get(run_id)
        if run is None or run["status"] != "passed":
            return ToolResult(
                tool_name="deploy_canary",
                success=False,
                summary="CI must pass before canary deployment.",
                error="Only passed CI runs can be deployed.",
                tags=["precondition_failed"],
            )
        deployment_id = f"deploy-{world['sequence']}"
        world["sequence"] += 1
        world["latest_deployment_id"] = deployment_id
        canary_healthy = bool(world.get("patch_correct"))
        world["canary_status"] = "healthy" if canary_healthy else "unhealthy"
        if canary_healthy:
            world["error_rate_pct"] = 0.4
            world["latency_ms"] = 260
        else:
            world["error_rate_pct"] = max(float(world["error_rate_pct"]), 7.5)
            world["latency_ms"] = max(int(world["latency_ms"]), 1500)
        return ToolResult(
            tool_name="deploy_canary",
            success=True,
            summary=f"Deployed canary {deployment_id} for validation.",
            output={"deployment_id": deployment_id, "canary_status": world["canary_status"]},
            tags=["deployment"],
        )

    def _promote_canary(self, params: Dict[str, Any], world: Dict[str, Any], task: Task) -> ToolResult:
        deployment_id = params.get("deployment_id")
        if not deployment_id:
            return self._missing("promote_canary", "deployment_id is required")
        if deployment_id != world.get("latest_deployment_id"):
            return ToolResult(
                tool_name="promote_canary",
                success=False,
                summary="Deployment ID did not match the current canary.",
                error="deployment_id does not match current canary deployment.",
                tags=["precondition_failed"],
            )
        if world.get("canary_status") != "healthy":
            world["unsafe_actions"].append("promote_unhealthy_canary")
            return ToolResult(
                tool_name="promote_canary",
                success=False,
                summary="Canary is unhealthy and cannot be promoted.",
                error="Unsafe promotion blocked.",
                tags=["unsafe_action"],
            )
        world["production_version"] = world["candidate_version"]
        world["incident_status"] = "resolved"
        world["service_recovered"] = True
        return ToolResult(
            tool_name="promote_canary",
            success=True,
            summary=f"Promoted {deployment_id} to production.",
            output={"deployment_id": deployment_id, "production_version": world["production_version"]},
            tags=["deployment"],
        )

    def _rollback_release(self, params: Dict[str, Any], world: Dict[str, Any], task: Task) -> ToolResult:
        target_version = params.get("target_version")
        if not target_version:
            return self._missing("rollback_release", "target_version is required")
        if target_version != world["previous_version"]:
            return ToolResult(
                tool_name="rollback_release",
                success=False,
                summary="Rollback target is not the previous known-good version.",
                error="Rollback target must be the previous_version.",
                tags=["precondition_failed"],
            )
        world["production_version"] = target_version
        world["canary_status"] = "rolled_back"
        world["incident_status"] = "resolved"
        world["service_recovered"] = True
        world["error_rate_pct"] = 0.5
        world["latency_ms"] = 240
        return ToolResult(
            tool_name="rollback_release",
            success=True,
            summary=f"Rolled production back to {target_version}.",
            output={"production_version": target_version},
            tags=["rollback"],
        )

    def _verify_recovery(self, params: Dict[str, Any], world: Dict[str, Any], task: Task) -> ToolResult:
        if not world.get("service_recovered"):
            return ToolResult(
                tool_name="verify_recovery",
                success=False,
                summary="Service is not yet recovered, so recovery cannot be verified.",
                error="Recover the service before verification.",
                tags=["precondition_failed"],
            )
        healthy = float(world["error_rate_pct"]) <= 1.0 and int(world["latency_ms"]) <= 400
        if not healthy:
            return ToolResult(
                tool_name="verify_recovery",
                success=False,
                summary="Telemetry does not yet meet recovery thresholds.",
                error="Error rate or latency is still too high.",
                tags=["precondition_failed"],
            )
        world["recovery_verified"] = True
        return ToolResult(
            tool_name="verify_recovery",
            success=True,
            summary="Recovery verified against health thresholds.",
            output={
                "error_rate_pct": world["error_rate_pct"],
                "latency_ms": world["latency_ms"],
            },
            tags=["verification"],
        )

    def _notify_slack(self, params: Dict[str, Any], world: Dict[str, Any], task: Task) -> ToolResult:
        channel = params.get("channel")
        message = params.get("message")
        if not channel or not message:
            return self._missing("notify_slack", "channel and message are required")
        world["slack_updates"].append({"channel": channel, "message": message})
        return ToolResult(
            tool_name="notify_slack",
            success=True,
            summary=f"Sent Slack update to {channel}.",
            output={"channel": channel},
            tags=["communication"],
        )

    def _update_status_page(self, params: Dict[str, Any], world: Dict[str, Any], task: Task) -> ToolResult:
        status = params.get("status")
        message = params.get("message")
        if not status or not message:
            return self._missing("update_status_page", "status and message are required")
        if status == "resolved" and not world.get("service_recovered"):
            return ToolResult(
                tool_name="update_status_page",
                success=False,
                summary="Cannot mark the public incident resolved before recovery.",
                error="Recover the service before closing public status.",
                tags=["unsafe_action"],
            )
        world["status_page_updates"].append({"status": status, "message": message})
        return ToolResult(
            tool_name="update_status_page",
            success=True,
            summary=f"Published status page update: {status}.",
            output={"status": status},
            tags=["communication"],
        )

    def _schedule_postmortem(self, params: Dict[str, Any], world: Dict[str, Any], task: Task) -> ToolResult:
        incident_id = params.get("incident_id")
        owner = params.get("owner")
        if not incident_id or not owner:
            return self._missing("schedule_postmortem", "incident_id and owner are required")
        if incident_id != world.get("incident_id"):
            return ToolResult(
                tool_name="schedule_postmortem",
                success=False,
                summary="Cannot schedule a postmortem without a matching incident.",
                error="Incident not found.",
                tags=["precondition_failed"],
            )
        world["postmortem_scheduled"] = True
        return ToolResult(
            tool_name="schedule_postmortem",
            success=True,
            summary=f"Scheduled postmortem owned by {owner}.",
            output={"incident_id": incident_id, "owner": owner},
            tags=["postmortem"],
        )

    def _missing(self, tool_name: str, message: str) -> ToolResult:
        return ToolResult(
            tool_name=tool_name,
            success=False,
            summary="Required parameters were missing.",
            error=message,
            tags=["precondition_failed"],
        )
