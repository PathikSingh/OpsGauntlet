"""Core behavior tests for the OpsGauntlet environment."""

import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inference import run_episode
from benchmark_report import (
    collect_benchmark_results,
    collect_comparison_report,
    render_markdown_report,
    write_csv_report,
    write_markdown_report,
)
from opsgauntlet.models import OpsGauntletAction, ToolCallRequest
from opsgauntlet.server.environment import OpsGauntletEnvironment
from opsgauntlet.server.task_bank import TASK_BANK


def step(env: OpsGauntletEnvironment, tool_name: str, parameters: dict, reasoning: str = "do the next safe thing"):
    return env.step(
        OpsGauntletAction(
            tool_call=ToolCallRequest(
                tool_name=tool_name,
                parameters=parameters,
                reasoning=reasoning,
            )
        )
    )


def test_reset_returns_valid_observation():
    env = OpsGauntletEnvironment()
    obs = env.reset(task_id="rollback_alpha")
    assert obs.task_id == "rollback_alpha"
    assert obs.available_tools
    assert obs.reward == 0.0
    assert obs.done is False


def test_rollback_scenario_can_complete_successfully():
    env = OpsGauntletEnvironment()
    env.reset(task_id="rollback_alpha")

    step(env, "inspect_release_status", {})
    step(env, "inspect_service_metrics", {})
    step(env, "rollback_release", {"target_version": "2026.03.9"})
    result = step(
        env,
        "notify_slack",
        {"channel": "#engineering", "message": "Rolled back release and recovered checkout."},
    )

    assert result.done is True
    assert result.reward is not None and 0.0 <= result.reward <= 1.0
    assert result.metadata["episode_score"] == 1.0
    assert result.metadata["raw_total_reward"] > 5
    assert "rolled_back_safely" in result.completed_objectives
    assert "internal_comms_sent" in result.completed_objectives


def test_fix_forward_flow_requires_correct_patch():
    env = OpsGauntletEnvironment()
    env.reset(task_id="hotfix_ci_beta")

    step(env, "inspect_ci_failure", {})
    step(env, "create_hotfix_branch", {"branch_name": "hotfix/auth-wheel"})
    step(env, "apply_hotfix", {"branch_name": "hotfix/auth-wheel", "patch_id": "pin-auth-wheel"})
    ci_run = step(env, "trigger_ci", {"branch_name": "hotfix/auth-wheel"})
    run_id = ci_run.last_tool_result.output["run_id"]
    step(env, "check_ci_status", {"run_id": run_id})
    canary = step(env, "deploy_canary", {"run_id": run_id})
    deployment_id = canary.last_tool_result.output["deployment_id"]
    step(env, "promote_canary", {"deployment_id": deployment_id})
    result = step(
        env,
        "notify_slack",
        {"channel": "#release-ops", "message": "Auth release promoted after hotfix validation."},
    )

    assert result.done is True
    assert "fixed_forward_safely" in result.completed_objectives
    assert result.metadata["terminal_outcome"] == "success"


def test_promoting_unhealthy_canary_is_penalized():
    env = OpsGauntletEnvironment()
    env.reset(task_id="hotfix_ci_beta")

    step(env, "inspect_ci_failure", {})
    step(env, "create_hotfix_branch", {"branch_name": "hotfix/auth-wheel"})
    step(env, "apply_hotfix", {"branch_name": "hotfix/auth-wheel", "patch_id": "wrong-patch"})
    ci_run = step(env, "trigger_ci", {"branch_name": "hotfix/auth-wheel"})
    run_id = ci_run.last_tool_result.output["run_id"]
    step(env, "check_ci_status", {"run_id": run_id})

    failed = step(env, "deploy_canary", {"run_id": run_id})
    assert failed.reward is not None and 0.0 <= failed.reward <= 1.0
    assert failed.metadata["raw_step_reward"] < 0


def test_pause_and_verify_recovery_flow():
    env = OpsGauntletEnvironment()
    env.reset(task_id="orders_pause_and_rollback")

    step(env, "inspect_release_status", {})
    step(env, "inspect_service_metrics", {})
    step(env, "pause_auto_rollout", {"reason": "Contain customer impact while reverting"})
    step(env, "rollback_release", {"target_version": "2026.04.6"})
    step(env, "verify_recovery", {})
    result = step(
        env,
        "notify_slack",
        {"channel": "#orders", "message": "Orders recovered after rollout pause and rollback."},
    )

    assert result.done is True
    assert "rollout_contained" in result.completed_objectives
    assert "recovery_verified" in result.completed_objectives
    assert result.metadata["terminal_outcome"] == "success"


def test_cannot_close_customer_incident_before_recovery():
    env = OpsGauntletEnvironment()
    env.reset(task_id="public_payments_incident")

    step(env, "create_incident_ticket", {"title": "Payments outage", "severity": "sev1"})
    result = step(
        env,
        "update_status_page",
        {"status": "resolved", "message": "premature close"},
    )

    assert result.reward is not None and 0.0 <= result.reward <= 1.0
    assert result.metadata["raw_step_reward"] < 0
    assert result.last_tool_result.success is False


def test_scripted_baseline_solves_all_tasks():
    outcomes = [run_episode(task.task_id, verbose=False) for task in TASK_BANK]
    assert all(item["terminal_outcome"] == "success" for item in outcomes)
    assert all(0.0 <= item["score"] <= 1.0 for item in outcomes)


def test_new_tasks_exist_and_can_reset():
    env = OpsGauntletEnvironment()
    for task_id in [
        "database_rollback_simple",
        "api_gateway_fix_forward",
        "notification_service_sev2",
        "ml_pipeline_hard",
    ]:
        obs = env.reset(task_id=task_id)
        assert obs.task_id == task_id
        assert obs.done is False
        assert len(obs.available_tools) > 0


def test_all_tasks_expose_positive_max_reward():
    env = OpsGauntletEnvironment()
    for task in TASK_BANK:
        obs = env.reset(task_id=task.task_id)
        assert isinstance(obs.max_reward, float)
        assert obs.max_reward > 0


def test_benchmark_report_covers_all_tasks_with_normalized_scores():
    report = collect_benchmark_results(scope="all", seed=7)
    assert report["task_count"] == len(TASK_BANK)
    assert report["success_count"] == len(TASK_BANK)
    assert 0.0 <= report["average_normalized_score"] <= 1.0
    for item in report["results"]:
        assert 0.0 <= item["normalized_score"] <= 1.0


def test_root_page_and_robots_are_served():
    from opsgauntlet.server.app import app

    client = TestClient(app)
    root = client.get("/")
    assert root.status_code == 200
    assert "Ops Gauntlet" in root.text

    robots = client.get("/robots.txt")
    assert robots.status_code == 200
    assert "User-agent" in robots.text


def test_http_reset_then_step_keeps_episode_state():
    from opsgauntlet.server.app import app

    client = TestClient(app)
    reset = client.post("/reset", json={"task_id": "rollback_alpha", "seed": 7})
    assert reset.status_code == 200
    assert reset.json()["observation"]["task_id"] == "rollback_alpha"

    step_response = client.post(
        "/step",
        json={
            "action": {
                "tool_call": {
                    "tool_name": "inspect_release_status",
                    "parameters": {},
                    "reasoning": "Check release state first.",
                }
            }
        },
    )
    assert step_response.status_code == 200
    payload = step_response.json()
    assert payload["observation"]["step_number"] == 1
    assert payload["observation"]["last_tool_result"]["tool_name"] == "inspect_release_status"
    assert payload["reward"] == 0.175
    assert payload["observation"]["metadata"]["raw_step_reward"] == 3.5


def test_http_reset_accepts_empty_body():
    from opsgauntlet.server.app import app

    client = TestClient(app)
    response = client.post("/reset")
    assert response.status_code == 200
    payload = response.json()
    assert payload["done"] is False
    assert "task_id" in payload["observation"]


def test_benchmark_report_supports_exports_and_comparison():
    report = collect_benchmark_results(scope="all", seed=7)
    comparison = collect_comparison_report(scope="all", seed=7)
    assert comparison["scripted"]["success_count"] == len(TASK_BANK)
    assert comparison["random"]["task_count"] == len(TASK_BANK)
    assert comparison["delta"]["average_normalized_score"] >= 0.0
    assert comparison["scripted"]["average_reward"] >= comparison["random"]["average_reward"]

    markdown = render_markdown_report(report)
    assert "# OpsGauntlet Benchmark Report" in markdown

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        csv_path = write_csv_report(report, temp_path / "benchmark.csv")
        md_path = write_markdown_report(markdown, temp_path / "benchmark.md")
        assert csv_path.exists()
        assert md_path.exists()
