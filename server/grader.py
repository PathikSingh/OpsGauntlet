"""Reward shaping and objective evaluation for OpsGauntlet."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Dict, List

try:
    from ..models import ToolResult
except ImportError:  # pragma: no cover
    from models import ToolResult  # type: ignore
from .task_bank import Task


@dataclass
class GradeResult:
    reward: float
    raw_points: float
    completed_objectives: List[str]
    done: bool
    terminal_outcome: str


class Grader:
    """Compute per-step rewards and terminal success."""

    @staticmethod
    def _strict_score(value: float) -> float:
        if not isfinite(value):
            return 0.5
        return round(max(0.001, min(value, 0.999)), 3)

    def evaluate(
        self,
        task: Task,
        before: Dict[str, object],
        after: Dict[str, object],
        result: ToolResult,
        reasoning: str,
        step_number: int,
    ) -> GradeResult:
        objectives = self._completed_objectives(task, after)
        previous_objectives = set(self._completed_objectives(task, before))
        new_objectives = [obj for obj in objectives if obj not in previous_objectives]

        raw_reward = -0.2
        if result.success:
            raw_reward += 1.1
        else:
            raw_reward -= 1.0

        if "unsafe_action" in result.tags:
            raw_reward -= 4.5
        if "precondition_failed" in result.tags:
            raw_reward -= 1.5
        if "redundant" in result.tags:
            raw_reward -= 0.6
        if "diagnostic" in result.tags and result.success:
            raw_reward += 0.8
        if "communication" in result.tags and not after["flags"].get("inspected_metrics"):
            raw_reward -= 0.8

        raw_reward += 1.6 * len(new_objectives)

        if reasoning.strip():
            raw_reward += 0.2

        done = self._is_success(task, after, objectives) or step_number >= task.max_steps
        terminal_outcome = "in_progress"

        if done and self._is_success(task, after, objectives):
            raw_reward += 12.0
            terminal_outcome = "success"
        elif done:
            if after.get("service_recovered"):
                raw_reward += 3.5
                terminal_outcome = "partial"
            else:
                raw_reward -= 5.0
                terminal_outcome = "failure"

        normalized_reward = self._strict_score(
            raw_reward / task.points_budget if task.points_budget > 0 else 0.5
        )

        return GradeResult(
            reward=normalized_reward,
            raw_points=round(raw_reward, 2),
            completed_objectives=objectives,
            done=done,
            terminal_outcome=terminal_outcome,
        )

    def _completed_objectives(self, task: Task, world: Dict[str, object]) -> List[str]:
        objectives: List[str] = []

        if "inspect_release_status" in task.must_use_diagnostics and world["flags"].get("inspected_release"):
            objectives.append("diagnosed_release_state")
        if "inspect_service_metrics" in task.must_use_diagnostics and world["flags"].get("inspected_metrics"):
            objectives.append("diagnosed_service_metrics")
        if "inspect_ci_failure" in task.must_use_diagnostics and world["flags"].get("inspected_ci"):
            objectives.append("diagnosed_ci_failure")

        if task.requires_ticket and world.get("incident_id"):
            objectives.append("ticket_opened")

        if task.requires_rollout_pause and world.get("auto_rollout_paused"):
            objectives.append("rollout_contained")

        if task.strategy == "rollback":
            if world.get("service_recovered") and world.get("production_version") == world.get("previous_version"):
                objectives.append("rolled_back_safely")
        else:
            if world.get("service_recovered") and world.get("production_version") == world.get("candidate_version"):
                objectives.append("fixed_forward_safely")

        if task.requires_recovery_verification and world.get("recovery_verified"):
            objectives.append("recovery_verified")

        if task.requires_slack and world.get("slack_updates"):
            objectives.append("internal_comms_sent")

        if task.requires_status_page:
            statuses = [update["status"] for update in world.get("status_page_updates", [])]
            if statuses:
                objectives.append("status_page_used")
            if "resolved" in statuses:
                objectives.append("status_page_closed")

        if task.requires_ticket and world.get("ticket_status") in {"resolved", "closed"}:
            objectives.append("ticket_closed")

        if task.requires_postmortem and world.get("postmortem_scheduled"):
            objectives.append("postmortem_scheduled")

        return objectives

    def _is_success(self, task: Task, world: Dict[str, object], objectives: List[str]) -> bool:
        if task.strategy == "rollback":
            resolved = "rolled_back_safely" in objectives
        else:
            resolved = "fixed_forward_safely" in objectives

        if not resolved:
            return False

        if world.get("unsafe_actions"):
            return False

        for diagnostic in task.must_use_diagnostics:
            flag_name = {
                "inspect_release_status": "inspected_release",
                "inspect_service_metrics": "inspected_metrics",
                "inspect_ci_failure": "inspected_ci",
            }[diagnostic]
            if not world["flags"].get(flag_name):
                return False

        if task.requires_ticket and "ticket_opened" not in objectives:
            return False
        if task.requires_rollout_pause and "rollout_contained" not in objectives:
            return False
        if task.requires_recovery_verification and "recovery_verified" not in objectives:
            return False
        if task.requires_status_page and "status_page_closed" not in objectives:
            return False
        if task.requires_slack and "internal_comms_sent" not in objectives:
            return False
        if task.requires_ticket and "ticket_closed" not in objectives:
            return False
        if task.requires_postmortem and "postmortem_scheduled" not in objectives:
            return False

        return True
