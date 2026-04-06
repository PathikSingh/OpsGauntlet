"""Typed client for OpsGauntlet."""

from typing import Dict

from openenv.core import EnvClient, State
from openenv.core.client_types import StepResult

try:
    from .models import OpsGauntletAction, OpsGauntletObservation
except ImportError:  # pragma: no cover
    from models import OpsGauntletAction, OpsGauntletObservation  # type: ignore


class OpsGauntletEnv(
    EnvClient[OpsGauntletAction, OpsGauntletObservation, State]
):
    """Persistent WebSocket client for the environment."""

    def _step_payload(self, action: OpsGauntletAction) -> Dict:
        return action.model_dump()

    def _parse_result(self, payload: Dict) -> StepResult[OpsGauntletObservation]:
        obs_data = payload.get("observation", {})
        observation = OpsGauntletObservation.model_validate(
            {
                **obs_data,
                "done": payload.get("done", False),
                "reward": payload.get("reward"),
            }
        )
        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        return State.model_validate(payload)
