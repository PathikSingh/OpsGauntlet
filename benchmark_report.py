"""Benchmark score report system for OpsGauntlet."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from random import Random
from typing import Any, Dict, Iterable

from inference import ScriptedBaselineAgent, iter_task_ids, run_episode

try:
    from opsgauntlet.models import OpsGauntletAction, ToolCallRequest
    from opsgauntlet.server.environment import OpsGauntletEnvironment, clamp_strict_score
    from opsgauntlet.server.task_bank import TASK_BANK, get_task_by_id
except ImportError:  # pragma: no cover
    from models import OpsGauntletAction, ToolCallRequest  # type: ignore
    from server.environment import OpsGauntletEnvironment, clamp_strict_score  # type: ignore
    from server.task_bank import TASK_BANK, get_task_by_id  # type: ignore


def collect_benchmark_results(
    scope: str = "all",
    seed: int = 7,
    policy: str = "scripted",
) -> Dict[str, Any]:
    """Run a policy across tasks and return aggregate benchmark metrics."""

    task_ids = list(iter_task_ids(scope, None))
    results = []
    for task_id in task_ids:
        outcome = _run_policy_episode(task_id=task_id, seed=seed, policy=policy)
        task = get_task_by_id(task_id)
        total_points = float(outcome.get("total_points", outcome.get("total_reward", 0.0)))
        score = float(outcome.get("score", total_points))
        results.append(
            {
                **outcome,
                "score": round(score, 3),
                "total_points": round(total_points, 2),
                "normalized_score": clamp_strict_score(score),
            }
        )

    difficulty_summary = _summarize_by_difficulty(results)
    success_count = sum(1 for item in results if item["terminal_outcome"] == "success")
    total_points = sum(item["total_points"] for item in results)
    total_normalized = sum(item["normalized_score"] for item in results)

    return {
        "scope": scope,
        "seed": seed,
        "policy": policy,
        "task_count": len(results),
        "success_count": success_count,
        "success_rate": round(success_count / len(results), 3) if results else 0.0,
        "average_points": round(total_points / len(results), 2) if results else 0.0,
        "average_normalized_score": round(total_normalized / len(results), 3) if results else 0.0,
        "difficulty_summary": difficulty_summary,
        "results": results,
    }


def collect_comparison_report(scope: str = "all", seed: int = 7) -> Dict[str, Any]:
    """Collect a scripted-vs-random comparison report."""

    scripted = collect_benchmark_results(scope=scope, seed=seed, policy="scripted")
    random_report = collect_benchmark_results(scope=scope, seed=seed, policy="random")
    return {
        "scope": scope,
        "seed": seed,
        "scripted": scripted,
        "random": random_report,
        "delta": {
            "success_rate": round(scripted["success_rate"] - random_report["success_rate"], 3),
            "average_points": round(scripted["average_points"] - random_report["average_points"], 2),
            "average_normalized_score": round(
                scripted["average_normalized_score"] - random_report["average_normalized_score"],
                3,
            ),
        },
    }


def _summarize_by_difficulty(results: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    buckets: Dict[str, list[Dict[str, Any]]] = {}
    for item in results:
        buckets.setdefault(item["difficulty"], []).append(item)

    summary: Dict[str, Dict[str, Any]] = {}
    for difficulty, items in sorted(buckets.items()):
        success_count = sum(1 for item in items if item["terminal_outcome"] == "success")
        summary[difficulty] = {
            "task_count": len(items),
            "success_count": success_count,
            "success_rate": round(success_count / len(items), 3) if items else 0.0,
            "average_points": round(sum(item["total_points"] for item in items) / len(items), 2) if items else 0.0,
            "average_normalized_score": round(sum(item["normalized_score"] for item in items) / len(items), 3) if items else 0.0,
        }
    return summary


def _run_policy_episode(task_id: str, seed: int, policy: str) -> Dict[str, Any]:
    if policy == "scripted":
        return run_episode(task_id, seed=seed, verbose=False)
    if policy == "random":
        return run_random_episode(task_id, seed=seed, verbose=False)
    raise ValueError(f"Unknown policy: {policy}")


def run_random_episode(task_id: str, seed: int = 7, verbose: bool = True) -> Dict[str, Any]:
    """Run a deterministic random policy for benchmark comparison."""

    env = OpsGauntletEnvironment()
    rng = Random(seed)
    observation = env.reset(seed=seed, task_id=task_id)

    if verbose:
        print(f"\n=== Random policy: {observation.title} ({task_id}) ===")

    while not observation.done and observation.step_number < observation.max_steps:
        tool_name = rng.choice(observation.available_tools)
        parameters = _random_parameters(observation.tool_schemas.get(tool_name, {}), observation, rng)
        action = OpsGauntletAction(
            tool_call=ToolCallRequest(
                tool_name=tool_name,
                parameters=parameters,
                reasoning="Random baseline action for benchmark comparison.",
            )
        )
        observation = env.step(action)

    return {
        "task_id": task_id,
        "title": observation.title,
        "difficulty": observation.difficulty,
        "terminal_outcome": observation.metadata.get("terminal_outcome", "unknown"),
        "score": clamp_strict_score(float(observation.metadata.get("episode_score", observation.reward) or 0.5)),
        "total_points": round(float(observation.metadata.get("debug_total_points", 0.0)), 2),
        "steps": observation.step_number,
    }


def _random_parameters(schema: Dict[str, Any], observation: Any, rng: Random) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    for name in schema.get("required_params", []):
        params[name] = _placeholder_for_param(name, observation, rng)
    return params


def _placeholder_for_param(name: str, observation: Any, rng: Random) -> Any:
    if name == "reason":
        return "Random benchmark baseline action."
    if name == "title":
        return f"{observation.signal_snapshot.impacted_surface} incident"
    if name == "severity":
        return "sev2"
    if name == "owner":
        return "random-baseline"
    if name == "incident_id":
        return "INC-1"
    if name == "status":
        return rng.choice(["investigating", "resolved"])
    if name == "summary":
        return "Random benchmark update."
    if name == "branch_name":
        return f"random/{observation.task_id}"
    if name == "patch_id":
        task = get_task_by_id(observation.task_id)
        return task.required_patch_id or "random-patch"
    if name == "run_id":
        return "run-1"
    if name == "deployment_id":
        return "deploy-1"
    if name == "target_version":
        return observation.service_snapshot.previous_version
    if name == "channel":
        return "#random"
    if name == "message":
        return "Random benchmark baseline update."
    if name == "checkpoint":
        return "random-checkpoint"
    if name == "date":
        return "2026-04-10"
    return "random-value"


def print_report(report: Dict[str, Any]) -> None:
    """Print a human-readable benchmark report."""

    print("\n=== OpsGauntlet Benchmark Report ===")
    print(f"Scope: {report['scope']}")
    print(f"Seed: {report['seed']}")
    print(f"Policy: {report['policy']}")
    print(f"Tasks: {report['task_count']}")
    print(
        "Overall: "
        f"success={report['success_count']}/{report['task_count']} "
        f"success_rate={report['success_rate']:.1%} "
        f"avg_points={report['average_points']:.2f} "
        f"avg_normalized={report['average_normalized_score']:.3f}"
    )

    print("\nBy difficulty:")
    for difficulty, summary in report["difficulty_summary"].items():
        print(
            f"- {difficulty}: "
            f"success={summary['success_count']}/{summary['task_count']} "
            f"success_rate={summary['success_rate']:.1%} "
            f"avg_points={summary['average_points']:.2f} "
            f"avg_normalized={summary['average_normalized_score']:.3f}"
        )

    print("\nPer task:")
    for item in report["results"]:
        print(
            f"- {item['task_id']}: "
            f"{item['terminal_outcome']} "
            f"(difficulty={item['difficulty']}, "
            f"steps={item['steps']}, "
            f"points={item['total_points']}, "
            f"normalized={item['normalized_score']:.3f})"
        )


def print_comparison_report(comparison: Dict[str, Any]) -> None:
    """Print a scripted-vs-random comparison summary."""

    print_report(comparison["scripted"])
    print("\n--- Random Policy Comparison ---")
    print_report(comparison["random"])
    print("\n--- Delta (scripted - random) ---")
    print(
        f"success_rate_delta={comparison['delta']['success_rate']:.1%} "
        f"avg_points_delta={comparison['delta']['average_points']:.2f} "
        f"avg_normalized_delta={comparison['delta']['average_normalized_score']:.3f}"
    )


def render_markdown_report(report: Dict[str, Any]) -> str:
    """Render a single policy report as Markdown."""

    lines = [
        "# OpsGauntlet Benchmark Report",
        "",
        f"- Scope: `{report['scope']}`",
        f"- Seed: `{report['seed']}`",
        f"- Policy: `{report['policy']}`",
        f"- Tasks: `{report['task_count']}`",
        f"- Success: `{report['success_count']}/{report['task_count']}`",
        f"- Success rate: `{report['success_rate']:.1%}`",
        f"- Average points: `{report['average_points']:.2f}`",
        f"- Average normalized score: `{report['average_normalized_score']:.3f}`",
        "",
        "## By Difficulty",
        "",
        "| Difficulty | Tasks | Success | Success Rate | Avg Points | Avg Normalized |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for difficulty, summary in report["difficulty_summary"].items():
        lines.append(
            f"| {difficulty} | {summary['task_count']} | {summary['success_count']} | "
            f"{summary['success_rate']:.1%} | {summary['average_points']:.2f} | "
            f"{summary['average_normalized_score']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Per Task",
            "",
            "| Task | Difficulty | Outcome | Steps | Points | Normalized |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for item in report["results"]:
        lines.append(
            f"| {item['task_id']} | {item['difficulty']} | {item['terminal_outcome']} | "
            f"{item['steps']} | {item['total_points']} | {item['normalized_score']:.3f} |"
        )
    return "\n".join(lines)


def render_comparison_markdown(comparison: Dict[str, Any]) -> str:
    """Render scripted-vs-random comparison as Markdown."""

    scripted = comparison["scripted"]
    random_report = comparison["random"]
    return "\n".join(
        [
            "# OpsGauntlet Benchmark Comparison",
            "",
            f"- Scope: `{comparison['scope']}`",
            f"- Seed: `{comparison['seed']}`",
            "",
            "| Policy | Success Rate | Avg Points | Avg Normalized |",
            "|---|---:|---:|---:|",
            f"| scripted | {scripted['success_rate']:.1%} | {scripted['average_points']:.2f} | {scripted['average_normalized_score']:.3f} |",
            f"| random | {random_report['success_rate']:.1%} | {random_report['average_points']:.2f} | {random_report['average_normalized_score']:.3f} |",
            "",
            "## Delta",
            "",
            f"- Success rate delta: `{comparison['delta']['success_rate']:.1%}`",
            f"- Average points delta: `{comparison['delta']['average_points']:.2f}`",
            f"- Average normalized score delta: `{comparison['delta']['average_normalized_score']:.3f}`",
        ]
    )


def write_csv_report(report: Dict[str, Any], path: str | Path) -> Path:
    """Write per-task results to a CSV file."""

    output_path = Path(path)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "task_id",
                "title",
                "difficulty",
                "terminal_outcome",
                "steps",
                "score",
                "total_points",
                "normalized_score",
            ],
        )
        writer.writeheader()
        for item in report["results"]:
            writer.writerow(
                {
                    "task_id": item["task_id"],
                    "title": item["title"],
                    "difficulty": item["difficulty"],
                    "terminal_outcome": item["terminal_outcome"],
                    "steps": item["steps"],
                    "score": item["score"],
                    "total_points": item["total_points"],
                    "normalized_score": item["normalized_score"],
                }
            )
    return output_path


def write_markdown_report(content: str, path: str | Path) -> Path:
    """Write Markdown report content to a file."""

    output_path = Path(path)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a benchmark score report for OpsGauntlet.")
    parser.add_argument(
        "--scope",
        choices=["easy", "medium", "hard", "all"],
        default="all",
        help="Task difficulty bucket to evaluate.",
    )
    parser.add_argument("--seed", type=int, default=7, help="Deterministic seed for task runs.")
    parser.add_argument(
        "--policy",
        choices=["scripted", "random"],
        default="scripted",
        help="Policy to evaluate when not running comparison mode.",
    )
    parser.add_argument("--compare-random", action="store_true", help="Compare the scripted baseline against a random policy.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a human-readable report.")
    parser.add_argument("--csv-out", help="Write per-task results to a CSV file.")
    parser.add_argument("--md-out", help="Write a Markdown report to a file.")
    args = parser.parse_args()

    if args.compare_random:
        comparison = collect_comparison_report(scope=args.scope, seed=args.seed)
        if args.csv_out:
            write_csv_report(comparison["scripted"], args.csv_out)
        if args.md_out:
            write_markdown_report(render_comparison_markdown(comparison), args.md_out)
        if args.json:
            print(json.dumps(comparison, indent=2))
            return
        print_comparison_report(comparison)
        return

    report = collect_benchmark_results(scope=args.scope, seed=args.seed, policy=args.policy)
    if args.csv_out:
        write_csv_report(report, args.csv_out)
    if args.md_out:
        write_markdown_report(render_markdown_report(report), args.md_out)
    if args.json:
        print(json.dumps(report, indent=2))
        return
    print_report(report)


if __name__ == "__main__":
    main()
