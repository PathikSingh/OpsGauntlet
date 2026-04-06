# OpsGauntlet Pitch

## 30-Second Version

OpsGauntlet is an OpenEnv benchmark for training and evaluating agents on safe software operations workflows. Instead of treating tool use as a flat API-ordering puzzle, it simulates real release and incident response decisions like rollback vs fix-forward, rollout containment, CI validation, recovery verification, ticket hygiene, and public communication.

## 2-Minute Demo Script

We built OpsGauntlet because most tool-using benchmarks do not capture operational judgment. In real release engineering, success is not just calling tools in the right order. The agent has to diagnose before acting, choose a safe remediation strategy, avoid unsafe promotions, verify recovery, and communicate correctly.

In this environment, each task gives the agent a briefing, service state, telemetry, and a constrained toolset. The agent then acts step by step inside a simulated operations world. The environment updates state, returns rewards, and checks whether the agent followed safe operational practice.

We included easy, medium, and hard scenarios across rollback, fix-forward, public incidents, and containment-first workflows. We also added penalties for unsafe actions like closing incidents before recovery or promoting unhealthy canaries.

For Round 1, the key contribution is the environment itself. To prove that the benchmark is usable end to end, we also included a deterministic baseline runner that solves all current tasks successfully. So judges can validate that the environment is both realistic and solvable.

## Best Demo Order

1. Run `python inference.py --task-id public_payments_incident`
2. Explain rollback, incident ticketing, public closure, and Slack update
3. Run `python inference.py --task-id checkout_fix_forward_major`
4. Explain containment, hotfix, CI, canary, recovery verification, ticket closure, and postmortem

## Judge Framing

- `This is a benchmark for safe operational agents, not just tool-calling agents.`
- `It evaluates long-horizon decisions with delayed consequences.`
- `It is reusable for both training and evaluation in OpenEnv.`
- `It turns operational judgment into a measurable RL environment.`
