"""Data models for OpsGauntlet."""

from typing import Any, Dict, Optional

from openenv.core import Action, Observation
from pydantic import BaseModel, Field


class ToolCallRequest(BaseModel):
    """One tool invocation proposed by the agent."""

    tool_name: str = Field(..., description="Name of the tool to call.")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments passed to the selected tool.",
    )
    reasoning: str = Field(
        default="",
        description="Short explanation of why this action is appropriate now.",
    )


class OpsGauntletAction(Action):
    """Agent action for the OpsGauntlet environment."""

    tool_call: ToolCallRequest = Field(..., description="Tool invocation to execute.")


class ToolResult(BaseModel):
    """Normalized tool execution result returned in observations."""

    tool_name: str
    success: bool
    summary: str
    output: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class ServiceSnapshot(BaseModel):
    """High-level deployment and incident state visible to the agent."""

    production_version: str
    previous_version: str
    candidate_version: str
    active_strategy: str
    incident_status: str
    canary_status: str
    ticket_status: str


class SignalSnapshot(BaseModel):
    """Observable telemetry made available to the agent."""

    error_rate_pct: float
    latency_ms: int
    ci_status: str
    impacted_surface: str
    alerts: list[str] = Field(default_factory=list)


class OpsGauntletObservation(Observation):
    """Observation returned after reset and each step."""

    task_id: str = Field(..., description="Current task identifier.")
    title: str = Field(..., description="Short task title.")
    difficulty: str = Field(..., description="Task difficulty bucket.")
    briefing: str = Field(..., description="Natural language task briefing.")
    available_tools: list[str] = Field(
        default_factory=list,
        description="Tools available for the current scenario.",
    )
    tool_schemas: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Tool descriptions and parameter requirements.",
    )
    service_snapshot: ServiceSnapshot = Field(
        ..., description="Operational state of the service."
    )
    signal_snapshot: SignalSnapshot = Field(
        ..., description="Key telemetry and alerting signals."
    )
    timeline: list[str] = Field(
        default_factory=list,
        description="Recent execution timeline and environment events.",
    )
    completed_objectives: list[str] = Field(
        default_factory=list,
        description="Objectives already satisfied in this episode.",
    )
    last_tool_result: Optional[ToolResult] = Field(
        default=None,
        description="Result from the immediately previous tool execution.",
    )
    step_number: int = Field(default=0, description="Current step number.")
    max_steps: int = Field(default=10, description="Maximum steps for the task.")
    max_reward: float = Field(default=0.0, description="Reference maximum reward for the task.")
    hint: Optional[str] = Field(
        default=None,
        description="Scenario hint that nudges the agent toward safe behavior.",
    )
