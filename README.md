---
title: Ops Gauntlet
emoji: "🚀"
sdk: docker
app_port: 8000
pinned: false
license: mit
---

# Ops Gauntlet

Ops Gauntlet is an OpenEnv-compatible benchmark for evaluating and demonstrating agent behavior during release failures, production incidents, rollback decisions, hotfix workflows, and stakeholder communication.

The environment focuses on operational judgment, not just API sequencing. An agent is expected to diagnose the issue, choose a safe remediation path, validate recovery, and complete the follow-through required in a real ReleaseOps setting.

## Quickstart

```bash
pip install -e .[dev]
pytest -q
openenv validate .
python -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```

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

## Why This Project Matters

Modern coding agents increasingly interact with deployment systems, CI pipelines, telemetry dashboards, incident tooling, and customer-facing status surfaces. They often fail not because they lack syntax, but because they:

- skip diagnosis
- choose unsafe remediation
- promote unhealthy canaries
- miss required communications
- close incidents before service health is actually restored

Ops Gauntlet trains and evaluates those higher-value operational behaviors.

## ReleaseOps Capabilities

Instead of solving a generic API-order puzzle, the agent operates inside a coherent ReleaseOps environment:

- inspect telemetry before acting
- choose rollback versus fix-forward
- patch the right failure cause
- rerun CI safely
- deploy via canary
- communicate internally and externally
- close out incident workflow cleanly

## Scenario Families

- `rollback-first incidents`: a bad release should be reverted quickly and safely
- `fix-forward hotfixes`: rollback is not sufficient; the agent must patch, test, canary, and promote
- `public customer incidents`: service recovery must be paired with ticketing and status-page hygiene
- `containment-first incidents`: the agent is rewarded for pausing rollout before remediation
- `verified recovery`: the agent must confirm healthy telemetry before closing the loop

## Professional Features

- task-local toolsets so the agent must reason inside realistic operational scope
- branching outcomes between rollback and fix-forward strategies
- containment controls such as rollout pause before deeper remediation
- recovery verification before customer-facing closure
- penalties for unsafe behavior like premature incident closure
- benchmark-style scenarios spanning easy, medium, and hard operational chains

## Core Tools

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

## Action And Observation Spaces

The typed action space is `OpsGauntletAction`, which carries one `ToolCallRequest`:
- `tool_name`: the operational tool the agent wants to call
- `parameters`: structured arguments for that tool
- `reasoning`: a short explanation of the chosen action

The typed observation space is `OpsGauntletObservation`, which exposes:
- scenario identity and briefing (`task_id`, `title`, `difficulty`, `briefing`)
- available affordances (`available_tools`, `tool_schemas`)
- live system state (`service_snapshot`, `signal_snapshot`)
- recent execution context (`timeline`, `completed_objectives`, `last_tool_result`)
- scoring and episode controls (`reward`, `max_steps`, `max_reward`, `metadata`, `done`)

## Local Usage

```bash
python demo_runner.py public_payments_incident
python demo_runner.py checkout_fix_forward_major
python inference.py --scope all
python inference.py --task-id rollback_alpha --runner submission
python benchmark_report.py
```

## Reward Philosophy

The environment does not reward tool spam or long reasoning text. It rewards:
- correct diagnosis
- safe operational sequencing
- appropriate remediation strategy
- healthy final service state
- complete incident hygiene

Unsafe or premature actions such as promoting an unhealthy canary are penalized.

## Benchmark Focus

This project is designed as a serious benchmark rather than a toy workflow simulator. It emphasizes:
- long-horizon decision making
- delayed operational outcomes
- branching remediation strategies
- reusable task structure for agent training and eval

## Baseline Agent

Round 1 does not require you to train a model to make the environment valid. The required artifact is the environment itself.

For testing and demos, this repo includes a deterministic scripted baseline:

```bash
python inference.py --scope all
python inference.py --task-id checkout_fix_forward_major
```

This baseline is useful for:
- proving that the environment is solvable end to end
- showing judges the expected operational flow
- giving you a no-LLM demo path for Round 1

## Benchmark Report

This repo also includes a benchmark score report system:

```bash
python benchmark_report.py
python benchmark_report.py --scope hard
python benchmark_report.py --json
python benchmark_report.py --csv-out benchmark.csv --md-out benchmark.md
python benchmark_report.py --compare-random
```

The report includes:
- overall success rate
- average reward
- average normalized score
- per-difficulty summary
- per-task score breakdown
- optional CSV export
- optional Markdown export
- optional scripted-vs-random comparison

Normalized score is computed against each task's `max_reward` and then clamped strictly inside `(0, 1)` for validator-safe reporting.
The surfaced environment `reward` and benchmark `score` therefore stay strictly between `0.0` and `1.0`, while raw shaped reward remains available through observation metadata and benchmark report fields for debugging.

## Submission Compliance Notes

The root-level `inference.py` is set up for the submission checklist:
- required env vars: `API_BASE_URL`, `MODEL_NAME`, `API_KEY`
- optional env var when using `from_docker_image()`: `LOCAL_IMAGE_NAME`
- defaults are provided only for `API_BASE_URL` and `MODEL_NAME`
- any LLM-backed path uses `from openai import OpenAI`
- the default `--policy auto` path uses the organizer proxy whenever `API_KEY` is injected, and otherwise falls back to the scripted baseline for local validation
- stdout is restricted to structured `[START]`, `[STEP]`, and `[END]` log lines
- `python inference.py` runs the local in-process baseline for reproducible validation, while `--runner submission` can smoke-test the deployed Space or Docker image path

## Demo Flow

For a confident hackathon demo, walk one rollback scenario and one fix-forward scenario:
- rollback demo: `public_payments_incident`
- fix-forward demo: `checkout_fix_forward_major`

You can run the scripted demos directly:

```bash
python demo_runner.py public_payments_incident
python demo_runner.py checkout_fix_forward_major
```

Use the observation timeline to explain:
- what the agent knew
- why it chose containment / rollback / patching
- how the environment scored safe versus unsafe behavior
 
## Development Notes

- package name: `openenv-opsgauntlet`
- runtime entrypoint: `server.app:app`
- test suite: `tests/test_environment.py`
- OpenEnv config: `openenv.yaml`

## License

This project is licensed under the MIT License. See `LICENSE` for details.

