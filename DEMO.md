# Demo Guide

## What To Say First

`opsgauntlet` is a benchmark environment for training and evaluating tool-using agents on realistic software operations work: incident containment, rollback, fix-forward remediation, CI/CD safety, and stakeholder communication.

Quick demo command:

```bash
python inference.py --task-id public_payments_incident
```

The key point is that this is not a generic workflow simulator. It is a coherent operational environment with:
- branching strategies
- stateful release health
- unsafe action penalties
- recovery verification
- incident hygiene requirements

## Best Demo Order

### Demo 1: Public rollback incident

Task: `public_payments_incident`

Show:
- inspect release state
- inspect service metrics
- create incident ticket
- rollback
- update public status page to resolved
- resolve ticket
- send Slack update

What this proves:
- customer-facing incidents require both recovery and communication
- the environment rewards safe closure, not just service recovery

### Demo 2: Containment + fix-forward

Task: `checkout_fix_forward_major`

Show:
- inspect release
- inspect metrics
- inspect CI failure
- pause auto rollout
- create incident ticket
- create hotfix branch
- apply correct patch
- trigger CI
- verify CI
- deploy canary
- promote canary
- verify recovery
- close status page and ticket
- notify Slack
- schedule postmortem

What this proves:
- the environment supports long-horizon agent behavior
- containment matters
- fix-forward requires correct diagnosis and patch selection
- the environment checks recovery before closure

## Talking Points For Judges

- This benchmark targets a real gap in agent training: operational decision making under release pressure.
- The environment is reusable across rollback and fix-forward strategy classes.
- It encodes safe operational norms instead of rewarding naive tool sequencing.
- It is OpenEnv-native, tested locally, and ready for deployment.

## Suggested One-Line Close

This project trains agents not just to use tools, but to behave like safe release engineers under pressure.
