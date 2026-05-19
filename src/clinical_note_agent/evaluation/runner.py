from __future__ import annotations

from pathlib import Path
from typing import Any

from clinical_note_agent.evaluation.catalog import build_rule_coverage, suggest_improvements
from clinical_note_agent.evaluation.models import EvaluationReport, MetricResult
from clinical_note_agent.evaluation.plan import load_evaluation_plan, resolve_repo_path
from clinical_note_agent.evaluation.scenarios import run_scenario


def run_evaluation(plan_path: Path) -> EvaluationReport:
    """执行评估计划，返回结构化报告。"""
    plan = load_evaluation_plan(plan_path)

    scope = plan.get("scope", [])
    if isinstance(scope, str):
        scope = [scope]

    metrics_cfg = plan.get("core_metrics", [])
    scoring = plan.get("scoring", {})
    pass_threshold = float(scoring.get("pass_threshold", 1.0))

    metric_results: list[MetricResult] = []
    for mc in metrics_cfg:
        metric_id = mc["id"]
        scenarios_out = [
            run_scenario(plan, metric_id, sc) for sc in mc.get("scenarios", [])
        ]
        metric_results.append(
            MetricResult(
                metric_id=metric_id,
                name=mc.get("name", metric_id),
                target_pass_rate=float(mc.get("target_pass_rate", 1.0)),
                scenarios=scenarios_out,
            )
        )

    rule_coverage: list[Any] = []
    improvements: list[str] = []
    rcfg = plan.get("rule_coverage")
    if rcfg:
        catalog_path = resolve_repo_path(plan, rcfg["catalog_path"])
        track = rcfg.get("track_status")
        rule_coverage = build_rule_coverage(
            catalog_path,
            metrics_cfg,
            track_status=track,
        )
        improvements = suggest_improvements(rule_coverage, metric_results)
        if plan.get("improvements"):
            improvements = list(plan["improvements"]) + improvements

    return EvaluationReport(
        plan_id=plan.get("id", "unknown"),
        plan_version=str(plan.get("version", "")),
        plan_name=plan.get("name", ""),
        scope=scope,
        metrics=metric_results,
        rule_coverage=rule_coverage,
        pass_threshold=pass_threshold,
        architecture=plan.get("architecture", []),
        improvements=improvements,
    )
