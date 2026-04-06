# OpsGauntlet Submission Guide

## What This Project Is

`opsgauntlet` is an OpenEnv-compatible reinforcement learning environment.

The environment trains and evaluates agents on safe software operations behavior:
- diagnose incidents before acting
- choose rollback vs fix-forward correctly
- pause rollout when containment matters
- validate CI before deployment
- verify recovery before closure
- complete internal and public communication steps

This is the correct kind of artifact for Round 1.

## What Round 1 Needs

For Round 1, the main deliverable is the environment itself:
- environment code
- task bank
- tool simulation
- reward logic
- packaging
- Docker compatibility
- OpenEnv validation

You do not need a real production CI/CD platform.
You do not need a trained RL model to make the environment valid.

## Current Project Status

Verified locally:
- `pytest -q` passes
- `openenv validate .` passes
- Docker build works
- Docker container responds on `/health` and `/schema`
- `python inference.py --scope all --quiet` solves all tasks with the baseline policy

## What You Need To Do

Only account-gated steps remain:
- log in to Hugging Face
- create or choose the final Space repo
- push the environment
- submit the Space/repo link on the hackathon portal

## Exact Local Validation Commands

From the project root:

```bash
pip install -e .[dev]
pytest -q
openenv validate .
python inference.py --scope all
python demo_runner.py public_payments_incident
```

## Docker Commands

```bash
docker build -t opsgauntlet:test -f server/Dockerfile .
docker run --rm -p 8000:8000 opsgauntlet:test
```

Then test:
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/schema`

## Hugging Face Login

If not logged in:

```bash
hf auth login
hf auth whoami
```

You will need a token from:
- [Hugging Face Access Tokens](https://huggingface.co/settings/tokens)

## Push Command

Recommended repo id:

```bash
YOUR_HF_USERNAME/opsgauntlet
```

Push:

```bash
openenv push . --repo-id YOUR_HF_USERNAME/opsgauntlet
```

Or with the helper script on Windows:

```bash
powershell -ExecutionPolicy Bypass -File .\push_space.ps1 -RepoId YOUR_HF_USERNAME/opsgauntlet
```

If you want the default inferred repo name:

```bash
openenv push .
```

## Suggested Submission Summary

Project name:
- `OpsGauntlet`

One-line description:
- `An OpenEnv benchmark for training and evaluating agents on safe release engineering and incident response workflows.`

Problem:
- `Tool-using agents often fail in operational settings because they skip diagnosis, choose unsafe remediation, or close incidents before service is actually healthy.`

Solution:
- `OpsGauntlet simulates realistic rollback, fix-forward, CI/CD, containment, recovery verification, and stakeholder communication tasks with explicit rewards and penalties.`

Why it is strong:
- `It is not a generic API-sequencing toy. It is a coherent operational benchmark with long-horizon state, branching strategies, and safety-aware grading.`

## Is An LLM Required?

No.

For Round 1:
- the environment is required
- an LLM is optional
- a baseline policy is enough to demonstrate solvability

## If You Still Want An LLM For Demo

Use an LLM only as a demo driver on top of the environment.

Good practical options:
- `gpt-4.1-mini` or similar low-cost tool-using model for a live demo
- `Qwen2.5-7B-Instruct` or similar open model if you want an open-stack demo

But this is optional for Round 1.
