# Gauntlet

Gauntlet is an OpenEnv-compatible benchmark environment for evaluating and demonstrating agent behavior during release failures, production incidents, rollback decisions, hotfix workflows, and stakeholder communication.

The project is designed around realistic ReleaseOps decision-making rather than toy API tasks. An agent is expected to diagnose the problem, choose a safe remediation path, validate recovery, and complete the operational follow-through.

## Why This Project Exists

Modern AI agents increasingly interact with operational systems such as CI pipelines, deployment controls, telemetry dashboards, incident tooling, and customer-facing status surfaces. In practice, many failures are not syntax failures. They are judgment failures:

- acting before diagnosing
- choosing an unsafe remediation strategy
- promoting an unhealthy canary
- forgetting required communications
- closing an incident before service health is actually restored

Gauntlet focuses on these higher-value operational behaviors.

## What Gauntlet Evaluates

- diagnosis before action
- rollback versus fix-forward decision quality
- safe use of containment controls
- CI-aware remediation workflows
- canary validation before promotion
- recovery verification
- complete incident hygiene and communication

## Scenario Families

- `rollback-first incidents`
- `fix-forward hotfixes`
- `public customer incidents`
- `containment-first incidents`
- `verified recovery`

## Core Tool Surface

The environment exposes a realistic operational toolset, including:

- `inspect_release_status`
- `inspect_service_metrics`
- `inspect_ci_failure`
- `pause_auto_rollout`
- `create_incident_ticket`
- `update_incident_ticket`
- `create_hotfix_branch`
- `apply_hotfix`
- `trigger_ci`
- `check_ci_status`
- `deploy_canary`
- `promote_canary`
- `rollback_release`
- `verify_recovery`
- `notify_slack`
- `update_status_page`
- `schedule_postmortem`

## Project Structure

```text
.
|-- server/
|   |-- app.py
|   |-- environment.py
|   |-- grader.py
|   |-- task_bank.py
|   `-- tool_registry.py
|-- tests/
|   `-- test_environment.py
|-- demo_runner.py
|-- inference.py
|-- benchmark_report.py
|-- openenv.yaml
`-- pyproject.toml
```

## Quick Start

### Requirements

- Python 3.10+
- `pip` or another Python package manager

### Install

```bash
pip install -e .[dev]
```

### Run the test suite

```bash
pytest -q
```

### Validate the environment

```bash
openenv validate .
```

### Start the local API server

```bash
python -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```

## Example Usage

```python
from opsgauntlet import OpsGauntletEnv, OpsGauntletAction, ToolCallRequest

env = OpsGauntletEnv(base_url="http://localhost:8000").sync()
with env:
    result = env.reset(seed=7)
    print(result.observation.title)
    result = env.step(
        OpsGauntletAction(
            tool_call=ToolCallRequest(
                tool_name="inspect_service_metrics",
                parameters={},
                reasoning="Check production health before choosing rollback or fix-forward.",
            )
        )
    )
    print(result.reward, result.observation.last_tool_result.summary)
```

## Demo Commands

```bash
python demo_runner.py public_payments_incident
python demo_runner.py checkout_fix_forward_major
```

Suggested demo flow:

- show one rollback-first scenario
- show one fix-forward scenario
- explain what the agent observed
- explain why the chosen remediation path was rewarded or penalized

## Baseline Agent

This repository includes a deterministic scripted baseline for validation and demonstration:

```bash
python inference.py --scope all
python inference.py --task-id checkout_fix_forward_major
```

This is useful for:

- proving the environment is solvable end to end
- demonstrating expected tool sequencing
- producing benchmark results without relying on an external LLM agent

## Benchmark Reporting

Generate benchmark summaries with:

```bash
python benchmark_report.py
python benchmark_report.py --scope hard
python benchmark_report.py --json
python benchmark_report.py --csv-out benchmark.csv --md-out benchmark.md
python benchmark_report.py --compare-random
```

The reporting flow supports:

- overall success rate
- average reward
- average normalized score
- per-difficulty summaries
- per-task score breakdowns
- scripted-versus-random comparisons

## Submission Support

Helper scripts included in the repository:

```bash
powershell -ExecutionPolicy Bypass -File .\submit_check.ps1
powershell -ExecutionPolicy Bypass -File .\push_space.ps1 -RepoId YOUR_HF_USERNAME/opsgauntlet
```

Supporting documents:

- `SUBMISSION.md`
- `PITCH.md`
- `DEMO.md`
- `PROJECT_WALKTHROUGH.md`
- `FINAL_PROJECT_GUIDE.md`

## Development Notes

- package name: `openenv-opsgauntlet`
- runtime entrypoint: `server.app:app`
- test file: `tests/test_environment.py`
- OpenEnv config: `openenv.yaml`

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
