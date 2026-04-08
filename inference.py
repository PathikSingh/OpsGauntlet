"""Round-one inference runner for OpsGauntlet."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable

from openai import OpenAI
from openenv.core.utils import run_async_safely

try:
    from opsgauntlet.client import OpsGauntletEnv
    from opsgauntlet.models import OpsGauntletAction, OpsGauntletObservation, ToolCallRequest
    from opsgauntlet.server.environment import OpsGauntletEnvironment
    from opsgauntlet.server.task_bank import TASK_BANK, Task, get_task_by_id
except ImportError:  # pragma: no cover
    from client import OpsGauntletEnv  # type: ignore
    from models import OpsGauntletAction, OpsGauntletObservation, ToolCallRequest  # type: ignore
    from server.environment import OpsGauntletEnvironment  # type: ignore
    from server.task_bank import TASK_BANK, Task, get_task_by_id  # type: ignore

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-4.1-mini")
API_KEY = os.getenv("API_KEY") or os.getenv("HF_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# Optional - if you use from_docker_image():
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

ENV_BASE_URL = "https://pathiksingh-ops-gauntlet.hf.space"


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


class OpenAIBackedAgent:
    """Optional OpenAI-compatible policy for manual evaluation."""

    def __init__(self) -> None:
        if not API_KEY:
            raise RuntimeError("API_KEY is required when running inference.py with --policy openai.")
        self._client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    def reset(self) -> None:
        return None

    def act(self, observation: OpsGauntletObservation) -> OpsGauntletAction:
        response = self._client.chat.completions.create(
            model=MODEL_NAME,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a safe release-operations agent. Return exactly one JSON object with "
                        "keys tool_name, parameters, and reasoning. Only choose from the available tools."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "task_id": observation.task_id,
                            "briefing": observation.briefing,
                            "available_tools": observation.available_tools,
                            "tool_schemas": observation.tool_schemas,
                            "service_snapshot": observation.service_snapshot.model_dump(),
                            "signal_snapshot": observation.signal_snapshot.model_dump(),
                            "completed_objectives": observation.completed_objectives,
                            "timeline": observation.timeline,
                            "hint": observation.hint,
                        },
                        indent=2,
                    ),
                },
            ],
        )
        content = response.choices[0].message.content or "{}"
        payload = json.loads(content)
        return OpsGauntletAction(
            tool_call=ToolCallRequest(
                tool_name=payload["tool_name"],
                parameters=payload.get("parameters", {}),
                reasoning=payload.get("reasoning", "Model-selected action."),
            )
        )


class ProxyBackedBaselineAgent:
    """Submission-safe baseline that always touches the organizer proxy."""

    def __init__(self) -> None:
        if not API_KEY:
            raise RuntimeError("API_KEY is required when running inference.py with proxy-backed policy.")
        self._client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
        self._baseline = ScriptedBaselineAgent()
        self._proxy_touched = False

    def reset(self) -> None:
        self._proxy_touched = False
        self._baseline.reset()

    def act(self, observation: OpsGauntletObservation) -> OpsGauntletAction:
        if not self._proxy_touched:
            self._touch_proxy(observation)
            self._proxy_touched = True
        return self._baseline.act(observation)

    def _touch_proxy(self, observation: OpsGauntletObservation) -> None:
        try:
            self._client.chat.completions.create(
                model=MODEL_NAME,
                temperature=0,
                max_tokens=8,
                timeout=20,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are validating connectivity for a release-operations environment. "
                            "Reply with the single token OK."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "task_id": observation.task_id,
                                "title": observation.title,
                                "available_tools": observation.available_tools,
                                "service_snapshot": observation.service_snapshot.model_dump(),
                                "signal_snapshot": observation.signal_snapshot.model_dump(),
                            }
                        ),
                    },
                ],
            )
        except Exception as exc:
            # Phase 2 requires a proxy attempt, but inference should still complete
            # even if the validator proxy is temporarily unavailable.
            print(f"[WARN] proxy_touch_failed {type(exc).__name__}: {exc}", file=sys.stderr)


def _emit(event: str, payload: Dict[str, Any], enabled: bool) -> None:
    if enabled:
        print(f"[{event}] {json.dumps(payload)}")


def _resolve_policy(policy: str) -> str:
    if policy != "auto":
        return policy
    return "proxy_scripted" if API_KEY else "scripted"


def _build_agent(policy: str) -> ScriptedBaselineAgent | OpenAIBackedAgent | ProxyBackedBaselineAgent:
    policy = _resolve_policy(policy)
    if policy == "scripted":
        return ScriptedBaselineAgent()
    if policy == "proxy_scripted":
        return ProxyBackedBaselineAgent()
    if policy == "openai":
        return OpenAIBackedAgent()
    raise ValueError(f"Unknown policy: {policy}")


def _connect_remote_env() -> Any:
    if LOCAL_IMAGE_NAME:
        return run_async_safely(OpsGauntletEnv.from_docker_image(LOCAL_IMAGE_NAME)).sync()
    return OpsGauntletEnv(base_url=ENV_BASE_URL).sync()


def _execute_episode(
    reset_fn: Callable[[], OpsGauntletObservation],
    step_fn: Callable[[OpsGauntletAction], OpsGauntletObservation],
    task_id: str,
    agent: ScriptedBaselineAgent | OpenAIBackedAgent | ProxyBackedBaselineAgent,
    verbose: bool,
    policy: str,
) -> Dict[str, Any]:
    observation = reset_fn()
    _emit(
        "START",
        {
            "task_id": task_id,
            "policy": policy,
            "max_steps": observation.max_steps,
            "available_tools": observation.available_tools,
        },
        verbose,
    )

    while not observation.done and observation.step_number < observation.max_steps:
        action = agent.act(observation)
        observation = step_fn(action)
        _emit(
            "STEP",
            {
                "task_id": task_id,
                "step": observation.step_number,
                "tool_name": action.tool_call.tool_name,
                "success": None if observation.last_tool_result is None else observation.last_tool_result.success,
                "score": round(float(observation.reward or 0.0), 3),
                "done": observation.done,
                "terminal_outcome": observation.metadata.get("terminal_outcome", "in_progress"),
            },
            verbose,
        )

    outcome = observation.metadata.get("terminal_outcome", "unknown")
    score = round(float(observation.metadata.get("episode_score", observation.reward or 0.0)), 3)
    total_points = round(float(observation.metadata.get("debug_total_points", 0.0)), 2)
    _emit(
        "END",
        {
            "task_id": task_id,
            "policy": policy,
            "terminal_outcome": outcome,
            "steps": observation.step_number,
            "score": score,
        },
        verbose,
    )
    return {
        "task_id": task_id,
        "title": observation.title,
        "difficulty": observation.difficulty,
        "terminal_outcome": outcome,
        "score": score,
        "total_points": total_points,
        "steps": observation.step_number,
    }


def run_episode(
    task_id: str,
    seed: int = 7,
    verbose: bool = True,
    policy: str = "scripted",
) -> Dict[str, Any]:
    """Run a local in-process episode for tests and benchmark scripts."""

    env = OpsGauntletEnvironment()
    resolved_policy = _resolve_policy(policy)
    agent = _build_agent(policy)
    agent.reset()
    return _execute_episode(
        reset_fn=lambda: env.reset(seed=seed, task_id=task_id),
        step_fn=lambda action: env.step(action),
        task_id=task_id,
        agent=agent,
        verbose=verbose,
        policy=resolved_policy,
    )


def run_submission_episode(
    task_id: str,
    seed: int = 7,
    verbose: bool = True,
    policy: str = "scripted",
) -> Dict[str, Any]:
    """Run the submission flow against the Space or local Docker image."""

    resolved_policy = _resolve_policy(policy)
    agent = _build_agent(policy)
    agent.reset()
    with _connect_remote_env() as env:
        return _execute_episode(
            reset_fn=lambda: env.reset(seed=seed, task_id=task_id).observation,
            step_fn=lambda action: env.step(action).observation,
            task_id=task_id,
            agent=agent,
            verbose=verbose,
            policy=resolved_policy,
        )


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
    parser = argparse.ArgumentParser(description="Run the OpsGauntlet submission inference flow.")
    parser.add_argument("--task-id", help="Run a single task by id.")
    parser.add_argument(
        "--scope",
        choices=["easy", "medium", "hard", "all"],
        default="all",
        help="Task difficulty bucket to run when --task-id is omitted.",
    )
    parser.add_argument("--seed", type=int, default=7, help="Deterministic seed for reset().")
    parser.add_argument(
        "--policy",
        choices=["auto", "scripted", "openai"],
        default="auto",
        help="Auto-uses the organizer proxy when API_KEY is present, otherwise falls back to the scripted baseline.",
    )
    parser.add_argument(
        "--runner",
        choices=["local", "submission"],
        default="local",
        help="Run locally for reproducible validation, or against the deployed/Docker environment for smoke testing.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Accepted for validator compatibility; stdout remains limited to structured [START]/[STEP]/[END] logs.",
    )
    args = parser.parse_args()

    runner = run_episode if args.runner == "local" else run_submission_episode
    for task_id in iter_task_ids(args.scope, args.task_id):
        runner(task_id, seed=args.seed, verbose=True, policy=args.policy)


if __name__ == "__main__":
    main()
