# OpsGauntlet: Final Project Guide

## 1. What This Project Is

OpsGauntlet is an OpenEnv-compatible reinforcement learning environment for safe software operations.

It is designed to simulate realistic release engineering and incident response workflows where an agent must:
- inspect system health
- diagnose failures
- decide rollback vs fix-forward
- contain blast radius
- run CI safely
- deploy cautiously
- verify recovery
- communicate with stakeholders
- complete incident hygiene

This project is built for the Meta PyTorch OpenEnv Hackathon Round 1.

## 2. Why This Project Was Chosen

The original idea was broader API orchestration across many unrelated tools.

That idea was improved because it risked looking like:
- a generic tool-order puzzle
- a toy API simulator
- a broad but shallow benchmark

OpsGauntlet is stronger because it is:
- one coherent domain
- easier for judges to understand
- closer to a real benchmark
- better aligned with OpenEnv expectations
- more useful for agent training and evaluation

## 3. Core Idea

OpsGauntlet is a simulated software operations sandbox.

Each task gives the agent:
- a production situation
- visible telemetry
- available tools
- operational objectives
- reward signals

The agent then interacts with the environment step by step.

The environment updates:
- service state
- CI state
- incident state
- communication state
- objective completion
- reward

## 4. What The Agent Can Do

The environment supports these operational actions:
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

## 5. What The Environment Evaluates

The benchmark checks whether the agent behaves safely and intelligently.

It rewards:
- proper diagnosis before action
- correct remediation strategy
- safe sequencing
- successful recovery
- incident lifecycle completion
- internal and external communication
- postmortem hygiene when required

It penalizes:
- unsafe actions
- premature incident closure
- promoting unhealthy canaries
- tool misuse
- missing preconditions
- incomplete recovery flow

## 6. Task Types Included

OpsGauntlet includes easy, medium, and hard scenarios.

These include:
- simple rollbacks
- CI failure hotfixes
- customer-facing incidents
- containment-first incidents
- full-lifecycle major incidents
- rollback and fix-forward workflows

Current task count:
- `12` total tasks

Example tasks:
- `rollback_alpha`
- `public_payments_incident`
- `checkout_fix_forward_major`
- `database_rollback_simple`
- `notification_service_sev2`
- `ml_pipeline_hard`

## 7. What Was Built

### Core environment

Main environment logic:
- [environment.py](C:\Users\singh\OpsGauntlet\server\environment.py)

This handles:
- reset
- step execution
- task selection
- observation creation
- objective progression
- done/failure handling

### Models

Typed models:
- [models.py](C:\Users\singh\OpsGauntlet\models.py)

This includes:
- action model
- observation model
- tool request model
- tool result model
- service snapshot
- signal snapshot

### Task bank

Task definitions:
- [task_bank.py](C:\Users\singh\OpsGauntlet\server\task_bank.py)

This includes:
- all scenarios
- task toolsets
- constraints
- difficulty labels
- hints
- max reward values

### Tool simulation

Operational tool behaviors:
- [tool_registry.py](C:\Users\singh\OpsGauntlet\server\tool_registry.py)

### Reward and grader logic

Scoring rules:
- [grader.py](C:\Users\singh\OpsGauntlet\server\grader.py)

### API app

OpenEnv/FastAPI app:
- [app.py](C:\Users\singh\OpsGauntlet\server\app.py)

### Client

Typed client:
- [client.py](C:\Users\singh\OpsGauntlet\client.py)

### Demo helpers

Baseline and demo helpers:
- [inference.py](C:\Users\singh\OpsGauntlet\inference.py)
- [demo_runner.py](C:\Users\singh\OpsGauntlet\demo_runner.py)

### Packaging and config

Project packaging:
- [pyproject.toml](C:\Users\singh\OpsGauntlet\pyproject.toml)
- [openenv.yaml](C:\Users\singh\OpsGauntlet\openenv.yaml)
- [Dockerfile](C:\Users\singh\OpsGauntlet\server\Dockerfile)

### Testing

Test suite:
- [test_environment.py](C:\Users\singh\OpsGauntlet\tests\test_environment.py)

### Benchmark artifacts

Benchmark evidence:
- [benchmark.md](C:\Users\singh\OpsGauntlet\benchmark.md)
- [benchmark_comparison.md](C:\Users\singh\OpsGauntlet\benchmark_comparison.md)
- [benchmark.csv](C:\Users\singh\OpsGauntlet\benchmark.csv)

### Submission docs

Submission-facing docs:
- [README.md](C:\Users\singh\OpsGauntlet\README.md)
- [SUBMISSION.md](C:\Users\singh\OpsGauntlet\SUBMISSION.md)
- [PITCH.md](C:\Users\singh\OpsGauntlet\PITCH.md)
- [PROJECT_WALKTHROUGH.md](C:\Users\singh\OpsGauntlet\PROJECT_WALKTHROUGH.md)

## 8. Major Improvements Made During Development

The project was improved beyond the initial concept.

Main improvements:
- changed the concept from generic API orchestration to a stronger release-ops benchmark
- renamed the project to OpsGauntlet
- made the environment domain coherent and realistic
- added stronger task flows
- added safer reward logic
- added full incident lifecycle handling
- added `max_reward` to tasks and observations
- added benchmark reporting
- added scripted-vs-random comparison
- added baseline inference so the environment is demoable without an LLM
- improved README and submission docs
- validated Docker/OpenEnv compatibility

## 9. Baseline Agent

The repo includes a deterministic scripted baseline in:
- [inference.py](C:\Users\singh\OpsGauntlet\inference.py)

Purpose:
- prove the environment is solvable
- show expected operational behavior
- support demos
- avoid needing an LLM for Round 1

Important:
- an LLM is not required for Round 1
- a trained RL model is not required for Round 1
- the environment itself is the main submission artifact

## 10. Benchmark Report System

The repo includes a benchmark report system in:
- [benchmark_report.py](C:\Users\singh\OpsGauntlet\benchmark_report.py)

It provides:
- overall success rate
- average reward
- normalized score
- per-difficulty summary
- per-task breakdown
- CSV export
- Markdown export
- scripted-vs-random comparison

Why it matters:
- helps the examiner understand the benchmark quickly
- proves the environment is measurable
- shows the baseline performs much better than a naive random policy
- adds professionalism to the submission

## 11. Project Status

Current practical status:
- core project is complete
- tests pass
- OpenEnv validation passes
- baseline solves all tasks
- benchmark artifacts exist
- docs are ready
- Docker support exists

Verified results:
- `pytest -q` -> `11 passed`
- `openenv validate .` -> `Ready for multi-mode deployment`
- `python inference.py --scope all --quiet` -> `Solved 12/12 task(s)`

## 12. What This Project Is Not

To be fully honest:

This is not:
- a live enterprise DevOps platform
- a real production CI/CD deployment system
- a fully trained RL model
- a consumer SaaS app

That is okay.

For this hackathon round, the required deliverable is the environment and benchmark, not a live production company platform.

## 13. How To Test It Yourself

From:
- [OpsGauntlet](C:\Users\singh\OpsGauntlet)

Run:

```bash
pip install -e .[dev]
pytest -q
openenv validate .
python inference.py --scope all
python demo_runner.py public_payments_incident
python benchmark_report.py
```

To run the API locally:

```bash
python -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```

Then open:
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/schema`

## 14. How To Test Docker

```bash
docker build -t opsgauntlet:test -f server/Dockerfile .
docker run --rm -p 8000:8000 opsgauntlet:test
```

Then check:
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/schema`

## 15. What Is Remaining For You

Only the account-bound and submission-bound steps remain.

### Still required from you

- log in to Hugging Face
- choose your final Hugging Face Space/repo id
- push the project to Hugging Face
- submit the final project link on the hackathon portal
- handle OTP/CAPTCHA/login prompts if they appear
- optionally present the demo if Round 2 or a live presentation happens

### Commands you will likely use

```bash
hf auth login
hf auth whoami
powershell -ExecutionPolicy Bypass -File .\submit_check.ps1
powershell -ExecutionPolicy Bypass -File .\push_space.ps1 -RepoId YOUR_HF_USERNAME/opsgauntlet
```

## 16. What Is Not Remaining

You do not need to build more core features before submission.

You do not need to:
- add a real production CI/CD backend
- train an RL model
- add an LLM just for Round 1
- rebuild the environment
- create a UI unless you personally want extra polish

## 17. Final Honest Assessment

OpsGauntlet is now:
- a real OpenEnv environment
- a valid Round 1 submission artifact
- benchmarked
- documented
- testable
- Dockerized
- submission-capable

What remains is deployment and portal submission, not core development.

## 18. Best Next Step

Do these next:

1. Open [OpsGauntlet](C:\Users\singh\OpsGauntlet)
2. Run the final checks
3. Log in to Hugging Face
4. Push to your Space
5. Submit the Space/repo link to the hackathon portal

After that, the project is submitted.
