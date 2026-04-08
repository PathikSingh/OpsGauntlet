"""Main OpsGauntlet environment implementation."""

from __future__ import annotations

from copy import deepcopy
from random import Random
from typing import Any, Dict, Optional
from uuid import uuid4

from openenv.core import Environment, State

try:
    from ..models import (
        OpsGauntletAction,
        OpsGauntletObservation,
        ServiceSnapshot,
        SignalSnapshot,
        ToolResult,
    )
except ImportError:  # pragma: no cover
    from models import (  # type: ignore
        OpsGauntletAction,
        OpsGauntletObservation,
        ServiceSnapshot,
        SignalSnapshot,
        ToolResult,
    )

from .grader import Grader
from .task_bank import Task, get_random_task
from .tool_registry import ToolRegistry

STRICT_SCORE_EPSILON = 0.001


def clamp_strict_score(value: float) -> float:
    """Keep surfaced task scores strictly inside the open unit interval."""

    return round(max(STRICT_SCORE_EPSILON, min(value, 1.0 - STRICT_SCORE_EPSILON)), 3)


class OpsGauntletEnvironment(
    Environment[OpsGauntletAction, OpsGauntletObservation, State]
):
    """OpenEnv environment for release engineering and incident response."""

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self) -> None:
        super().__init__()
        self._rng = Random()
        self._registry = ToolRegistry()
        self._grader = Grader()
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._task: Optional[Task] = None
        self._world: Dict[str, Any] = {}
        self._completed_objectives: list[str] = []
        self._last_tool_result: Optional[ToolResult] = None
        self._raw_total_reward: float = 0.0

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        task_id: Optional[str] = None,
        **kwargs: Any,
    ) -> OpsGauntletObservation:
        if seed is not None:
            self._rng.seed(seed)
        self._task = get_random_task(seed=self._rng.randint(0, 10_000_000)) if task_id is None else None
        if task_id is not None:
            from .task_bank import get_task_by_id

            self._task = get_task_by_id(task_id)
        assert self._task is not None

        self._state = State(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            task_id=self._task.task_id,
            title=self._task.title,
        )
        self._completed_objectives = []
        self._last_tool_result = None
        self._raw_total_reward = 0.0
        self._world = self._build_world(self._task)

        return self._make_observation(reward=clamp_strict_score(0.0), done=False)

    def step(
        self,
        action: OpsGauntletAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> OpsGauntletObservation:
        if self._task is None:
            raise RuntimeError("Environment must be reset before step().")

        self._state.step_count += 1
        before = deepcopy(self._world)
        tool_call = action.tool_call

        if tool_call.tool_name not in self._task.available_tools:
            result = ToolResult(
                tool_name=tool_call.tool_name,
                success=False,
                summary="Tool is not available in this scenario.",
                error=f"{tool_call.tool_name} is not enabled for task {self._task.task_id}.",
                tags=["precondition_failed"],
            )
        else:
            result = self._registry.execute(
                tool_call.tool_name,
                tool_call.parameters,
                self._world,
                self._task,
            )

        self._append_timeline(result)
        self._last_tool_result = result

        grade = self._grader.evaluate(
            self._task,
            before=before,
            after=self._world,
            result=result,
            reasoning=tool_call.reasoning,
            step_number=self._state.step_count,
        )
        self._completed_objectives = grade.completed_objectives
        self._raw_total_reward += grade.raw_points
        episode_score = self._normalized_episode_score()

        observation = self._make_observation(reward=episode_score, done=grade.done)
        observation.metadata["terminal_outcome"] = grade.terminal_outcome
        observation.metadata["task_strategy"] = self._task.strategy
        observation.metadata["service_recovered"] = self._world["service_recovered"]
        observation.metadata["unsafe_actions"] = list(self._world["unsafe_actions"])
        observation.metadata["auto_rollout_paused"] = self._world["auto_rollout_paused"]
        observation.metadata["recovery_verified"] = self._world["recovery_verified"]
        observation.metadata["step_score"] = grade.reward
        observation.metadata["debug_step_points"] = grade.raw_points
        observation.metadata["debug_total_points"] = round(self._raw_total_reward, 2)
        observation.metadata["episode_score"] = episode_score
        return observation

    @property
    def state(self) -> State:
        return self._state.model_copy()

    def _build_world(self, task: Task) -> Dict[str, Any]:
        base = {
            "production_version": "unknown",
            "previous_version": "unknown",
            "candidate_version": "unknown",
            "incident_status": "unknown",
            "impacted_surface": "unknown",
            "error_rate_pct": 0.0,
            "latency_ms": 0,
            "alerts": [],
            "ci_failure_reason": None,
            "failing_check": None,
            "ci_status": "not_started",
            "ci_runs": {},
            "latest_ci_run_id": None,
            "hotfix_branch": None,
            "applied_patch_id": None,
            "patch_correct": False,
            "latest_deployment_id": None,
            "canary_status": "not_started",
            "ticket_status": "not_created",
            "incident_id": None,
            "slack_updates": [],
            "status_page_updates": [],
            "postmortem_scheduled": False,
            "unsafe_actions": [],
            "service_recovered": False,
            "auto_rollout_paused": False,
            "recovery_verified": False,
            "flags": {
                "inspected_release": False,
                "inspected_metrics": False,
                "inspected_ci": False,
            },
            "timeline": [f"Scenario loaded: {task.title}"],
            "sequence": 1,
            "strategy": task.strategy,
        }
        base.update(deepcopy(task.initial_world))
        return base

    def _make_observation(self, reward: float, done: bool) -> OpsGauntletObservation:
        assert self._task is not None
        return OpsGauntletObservation(
            task_id=self._task.task_id,
            title=self._task.title,
            difficulty=self._task.difficulty,
            briefing=self._task.briefing,
            available_tools=list(self._task.available_tools),
            tool_schemas=self._registry.schemas_for(self._task.available_tools),
            service_snapshot=ServiceSnapshot(
                production_version=self._world["production_version"],
                previous_version=self._world["previous_version"],
                candidate_version=self._world["candidate_version"],
                active_strategy=self._task.strategy,
                incident_status=self._world["incident_status"],
                canary_status=self._world["canary_status"],
                ticket_status=self._world["ticket_status"],
            ),
            signal_snapshot=SignalSnapshot(
                error_rate_pct=float(self._world["error_rate_pct"]),
                latency_ms=int(self._world["latency_ms"]),
                ci_status=str(self._world["ci_status"]),
                impacted_surface=str(self._world["impacted_surface"]),
                alerts=list(self._world["alerts"]),
            ),
            timeline=list(self._world["timeline"][-8:]),
            completed_objectives=list(self._completed_objectives),
            last_tool_result=self._last_tool_result,
            step_number=self._state.step_count,
            max_steps=self._task.max_steps,
            hint=self._task.hint,
            reward=reward,
            done=done,
            metadata={
                "strategy": self._task.strategy,
                "customer_facing": self._task.customer_facing,
            },
        )

    def _append_timeline(self, result: ToolResult) -> None:
        status = "ok" if result.success else "failed"
        line = f"Step {self._state.step_count}: {result.tool_name} -> {status} ({result.summary})"
        self._world["timeline"].append(line)

    def _normalized_episode_score(self) -> float:
        assert self._task is not None
        if self._task.score_basis <= 0:
            return clamp_strict_score(0.5)
        normalized = self._raw_total_reward / self._task.score_basis
        return clamp_strict_score(normalized)
