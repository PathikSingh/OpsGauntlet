"""Baseline scripted agent for OpsGauntlet."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable

from opsgauntlet.models import OpsGauntletAction, OpsGauntletObservation, ToolCallRequest
from opsgauntlet.server.environment import OpsGauntletEnvironment
from opsgauntlet.server.task_bank import TASK_BANK, Task, get_task_by_id


@dataclass
class AgentMemory:
    """Episode-local handles learned from tool outputs."""

    incident_id: str | None = None
    branch_name: str | None = None
    run_id: str | None = None
    deployment_id: str | None = None
    patch_applied: bool = False
    history: list[str] = field(default_factory=list)


class ScriptedBaselineAgent:
    """A deterministic baseline policy that demonstrates safe task completion."""

    def __init__(self) -> None:
        self.memory = AgentMemory()

    def reset(self) -> None:
        self.memory = AgentMemory()

    def act(self, observation: OpsGauntletObservation) -> OpsGauntletAction:
        task = get_task_by_id(observation.task_id)
        self._capture_outputs(observation)

        call = (
            self._maybe_diagnose(observation, task)
            or self._maybe_contain(observation)
            or self._maybe_open_ticket(observation)
            or self._maybe_remediate(observation, task)
            or self._maybe_verify(observation)
            or self._maybe_public_comms(observation)
            or self._maybe_close_ticket(observation)
            or self._maybe_schedule_postmortem(observation, task)
            or self._maybe_internal_comms(observation)
        )
        if call is None:
            call = ToolCallRequest(
                tool_name=observation.available_tools[0],
                parameters={},
                reasoning="Fallback action because no higher-priority policy rule matched.",
            )
        self.memory.history.append(call.tool_name)
        return OpsGauntletAction(tool_call=call)

    def _capture_outputs(self, observation: OpsGauntletObservation) -> None:
        result = observation.last_tool_result
        if result is None:
            return
        output = result.output
        self.memory.incident_id = output.get("incident_id", self.memory.incident_id)
        self.memory.branch_name = output.get("branch_name", self.memory.branch_name)
        self.memory.run_id = output.get("run_id", self.memory.run_id)
        self.memory.deployment_id = output.get("deployment_id", self.memory.deployment_id)
        if "patch_id" in output:
            self.memory.patch_applied = True

    def _maybe_diagnose(self, observation: OpsGauntletObservation, task: Task) -> ToolCallRequest | None:
        completed = set(observation.completed_objectives)
        if (
            "inspect_release_status" in task.must_use_diagnostics
            and "diagnosed_release_state" not in completed
            and "inspect_release_status" in observation.available_tools
        ):
            return ToolCallRequest(
                tool_name="inspect_release_status",
                parameters={},
                reasoning="Check the active release state before choosing rollback or fix-forward.",
            )
        if (
            "inspect_service_metrics" in task.must_use_diagnostics
            and "diagnosed_service_metrics" not in completed
            and "inspect_service_metrics" in observation.available_tools
        ):
            return ToolCallRequest(
                tool_name="inspect_service_metrics",
                parameters={},
                reasoning="Confirm live production health before making a remediation decision.",
            )
        if (
            "inspect_ci_failure" in task.must_use_diagnostics
            and "diagnosed_ci_failure" not in completed
            and "inspect_ci_failure" in observation.available_tools
        ):
            return ToolCallRequest(
                tool_name="inspect_ci_failure",
                parameters={},
                reasoning="Read the CI failure details so the hotfix targets the actual regression.",
            )
        return None

    def _maybe_contain(self, observation: OpsGauntletObservation) -> ToolCallRequest | None:
        if "pause_auto_rollout" not in observation.available_tools:
            return None
        if observation.metadata.get("auto_rollout_paused"):
            return None
        if observation.service_snapshot.incident_status == "resolved":
            return None
        return ToolCallRequest(
            tool_name="pause_auto_rollout",
            parameters={"reason": "Contain blast radius before deeper remediation."},
            reasoning="Pause rollout expansion first to avoid widening customer impact.",
        )

    def _maybe_open_ticket(self, observation: OpsGauntletObservation) -> ToolCallRequest | None:
        if "create_incident_ticket" not in observation.available_tools:
            return None
        if self.memory.incident_id or observation.service_snapshot.ticket_status != "not_created":
            return None
        severity = "sev1" if observation.service_snapshot.incident_status in {"sev1", "major_outage"} else "sev2"
        title = f"{observation.signal_snapshot.impacted_surface} incident"
        return ToolCallRequest(
            tool_name="create_incident_ticket",
            parameters={"title": title, "severity": severity, "owner": "release-bot"},
            reasoning="Open formal incident tracking before continuing operational work.",
        )

    def _maybe_remediate(self, observation: OpsGauntletObservation, task: Task) -> ToolCallRequest | None:
        if task.strategy == "rollback":
            if observation.service_snapshot.incident_status != "resolved" and "rollback_release" in observation.available_tools:
                return ToolCallRequest(
                    tool_name="rollback_release",
                    parameters={
                        "target_version": observation.service_snapshot.previous_version,
                        "reason": "Rollback to the last known-good version for fastest recovery.",
                    },
                    reasoning="Rollback is the safest remediation path for this scenario.",
                )
            return None

        if "create_hotfix_branch" in observation.available_tools and self.memory.branch_name is None:
            branch_name = f"hotfix/{observation.task_id}"
            return ToolCallRequest(
                tool_name="create_hotfix_branch",
                parameters={"branch_name": branch_name},
                reasoning="Create an isolated branch for the fix-forward patch.",
            )

        if (
            "apply_hotfix" in observation.available_tools
            and observation.signal_snapshot.ci_status == "not_started"
            and not self.memory.patch_applied
        ):
            return ToolCallRequest(
                tool_name="apply_hotfix",
                parameters={
                    "branch_name": self.memory.branch_name,
                    "patch_id": task.required_patch_id,
                    "notes": "Apply the task-specific remediation patch.",
                },
                reasoning="Apply the exact patch required by the diagnosed failure.",
            )

        if "trigger_ci" in observation.available_tools and self.memory.run_id is None:
            return ToolCallRequest(
                tool_name="trigger_ci",
                parameters={"branch_name": self.memory.branch_name},
                reasoning="Run CI on the patched branch before any deployment.",
            )

        if "check_ci_status" in observation.available_tools and self.memory.run_id and observation.signal_snapshot.ci_status == "running":
            return ToolCallRequest(
                tool_name="check_ci_status",
                parameters={"run_id": self.memory.run_id},
                reasoning="Wait for CI completion before proceeding to deployment.",
            )

        if "deploy_canary" in observation.available_tools and self.memory.run_id and self.memory.deployment_id is None and observation.signal_snapshot.ci_status == "passed":
            return ToolCallRequest(
                tool_name="deploy_canary",
                parameters={"run_id": self.memory.run_id},
                reasoning="Validate the patch with a canary deployment before full promotion.",
            )

        if (
            "promote_canary" in observation.available_tools
            and self.memory.deployment_id
            and observation.service_snapshot.canary_status == "healthy"
            and observation.service_snapshot.incident_status != "resolved"
        ):
            return ToolCallRequest(
                tool_name="promote_canary",
                parameters={"deployment_id": self.memory.deployment_id},
                reasoning="Promote the healthy canary because the fix-forward path has been validated.",
            )
        return None

    def _maybe_verify(self, observation: OpsGauntletObservation) -> ToolCallRequest | None:
        if "verify_recovery" not in observation.available_tools:
            return None
        if observation.metadata.get("recovery_verified"):
            return None
        if observation.service_snapshot.incident_status != "resolved":
            return None
        return ToolCallRequest(
            tool_name="verify_recovery",
            parameters={"checkpoint": "post-remediation"},
            reasoning="Confirm that error rate and latency have actually stabilized after remediation.",
        )

    def _maybe_public_comms(self, observation: OpsGauntletObservation) -> ToolCallRequest | None:
        if "update_status_page" not in observation.available_tools:
            return None
        if "status_page_closed" in observation.completed_objectives:
            return None
        if observation.service_snapshot.incident_status != "resolved":
            return None
        return ToolCallRequest(
            tool_name="update_status_page",
            parameters={
                "status": "resolved",
                "message": "Mitigation completed and customer impact is resolved.",
            },
            reasoning="Close public communications after service recovery is confirmed.",
        )

    def _maybe_close_ticket(self, observation: OpsGauntletObservation) -> ToolCallRequest | None:
        if "update_incident_ticket" not in observation.available_tools:
            return None
        if observation.service_snapshot.ticket_status in {"resolved", "closed"}:
            return None
        if observation.service_snapshot.incident_status != "resolved":
            return None
        if not self.memory.incident_id:
            return None
        return ToolCallRequest(
            tool_name="update_incident_ticket",
            parameters={
                "incident_id": self.memory.incident_id,
                "status": "resolved",
                "summary": "Service recovered and operational follow-up is complete.",
            },
            reasoning="Resolve the incident ticket only after the environment shows service recovery.",
        )

    def _maybe_schedule_postmortem(self, observation: OpsGauntletObservation, task: Task) -> ToolCallRequest | None:
        if not task.requires_postmortem:
            return None
        if "schedule_postmortem" not in observation.available_tools:
            return None
        if "postmortem_scheduled" in observation.completed_objectives:
            return None
        if observation.service_snapshot.incident_status != "resolved":
            return None
        if not self.memory.incident_id:
            return None
        return ToolCallRequest(
            tool_name="schedule_postmortem",
            parameters={
                "incident_id": self.memory.incident_id,
                "owner": "incident-commander",
                "date": "2026-04-10",
            },
            reasoning="Schedule the postmortem once the incident is stabilized and documented.",
        )

    def _maybe_internal_comms(self, observation: OpsGauntletObservation) -> ToolCallRequest | None:
        if "notify_slack" not in observation.available_tools:
            return None
        if "internal_comms_sent" in observation.completed_objectives:
            return None
        if observation.service_snapshot.incident_status != "resolved":
            return None
        return ToolCallRequest(
            tool_name="notify_slack",
            parameters={
                "channel": f"#{observation.signal_snapshot.impacted_surface.split('-')[0]}",
                "message": "Service has recovered and follow-up actions are in progress.",
            },
            reasoning="Send the internal resolution summary after the operational path is complete.",
        )


def run_episode(task_id: str, seed: int = 7, verbose: bool = True) -> Dict[str, Any]:
    """Run the baseline policy against a single task and return the outcome."""

    env = OpsGauntletEnvironment()
    agent = ScriptedBaselineAgent()
    agent.reset()

    observation = env.reset(seed=seed, task_id=task_id)
    total_reward = 0.0

    if verbose:
        print(f"\n=== {observation.title} ({task_id}) ===")
        print(observation.briefing)

    while not observation.done and observation.step_number < observation.max_steps:
        action = agent.act(observation)
        observation = env.step(action)
        total_reward += observation.reward or 0.0
        if verbose:
            result = observation.last_tool_result
            print(f"[{observation.step_number}] {action.tool_call.tool_name}")
            print(f"  reward: {observation.reward}")
            if result is not None:
                print(f"  success: {result.success}")
                print(f"  summary: {result.summary}")
            print(f"  objectives: {', '.join(observation.completed_objectives) or 'none'}")

    outcome = observation.metadata.get("terminal_outcome", "unknown")
    if verbose:
        print(f"Terminal outcome: {outcome}")
        print(f"Total reward: {round(total_reward, 2)}")

    return {
        "task_id": task_id,
        "title": observation.title,
        "difficulty": observation.difficulty,
        "terminal_outcome": outcome,
        "total_reward": round(total_reward, 2),
        "steps": observation.step_number,
    }


def iter_task_ids(scope: str, task_id: str | None) -> Iterable[str]:
    if task_id:
        yield task_id
        return
    if scope == "all":
        for task in TASK_BANK:
            yield task.task_id
        return
    for task in TASK_BANK:
        if task.difficulty == scope:
            yield task.task_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the OpsGauntlet scripted baseline.")
    parser.add_argument("--task-id", help="Run a single task by id.")
    parser.add_argument(
        "--scope",
        choices=["easy", "medium", "hard", "all"],
        default="all",
        help="Task difficulty bucket to run when --task-id is omitted.",
    )
    parser.add_argument("--seed", type=int, default=7, help="Deterministic seed for reset().")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-step logs.")
    args = parser.parse_args()

    outcomes = [run_episode(task_id, seed=args.seed, verbose=not args.quiet) for task_id in iter_task_ids(args.scope, args.task_id)]
    successes = sum(1 for item in outcomes if item["terminal_outcome"] == "success")
    print(f"\nSolved {successes}/{len(outcomes)} task(s).")
    for item in outcomes:
        print(
            f"- {item['task_id']}: {item['terminal_outcome']} "
            f"(difficulty={item['difficulty']}, steps={item['steps']}, reward={item['total_reward']})"
        )


if __name__ == "__main__":
    main()
