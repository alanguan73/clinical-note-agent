from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScenarioResult:
    """单条测试场景执行结果。"""

    scenario_id: str
    metric_id: str
    passed: bool
    message: str = ""
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "metric_id": self.metric_id,
            "passed": self.passed,
            "message": self.message,
            "detail": self.detail,
        }


@dataclass
class MetricResult:
    """核心指标（含多条场景）汇总。"""

    metric_id: str
    name: str
    target_pass_rate: float
    scenarios: list[ScenarioResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if not self.scenarios:
            return 0.0
        return sum(1 for s in self.scenarios if s.passed) / len(self.scenarios)

    @property
    def passed(self) -> bool:
        return self.pass_rate >= self.target_pass_rate

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "target_pass_rate": self.target_pass_rate,
            "pass_rate": round(self.pass_rate, 4),
            "passed": self.passed,
            "scenarios": [s.to_dict() for s in self.scenarios],
        }


@dataclass
class RuleCoverageRow:
    """提示词规则目录中的一行覆盖状态。"""

    rule_id: str
    name: str
    status: str
    machine_code: str | None
    golden: str | None
    covered_by_metrics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "status": self.status,
            "machine_code": self.machine_code,
            "golden": self.golden,
            "covered_by_metrics": self.covered_by_metrics,
        }


@dataclass
class EvaluationReport:
    """完整评估报告。"""

    plan_id: str
    plan_version: str
    plan_name: str
    scope: list[str]
    metrics: list[MetricResult] = field(default_factory=list)
    rule_coverage: list[RuleCoverageRow] = field(default_factory=list)
    pass_threshold: float = 1.0
    architecture: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)

    @property
    def overall_pass_rate(self) -> float:
        total = sum(len(m.scenarios) for m in self.metrics)
        if total == 0:
            return 0.0
        passed = sum(1 for m in self.metrics for s in m.scenarios if s.passed)
        return passed / total

    @property
    def passed(self) -> bool:
        if not self.metrics:
            return False
        return all(m.passed for m in self.metrics) and self.overall_pass_rate >= self.pass_threshold

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "plan_version": self.plan_version,
            "plan_name": self.plan_name,
            "scope": self.scope,
            "architecture": self.architecture,
            "pass_threshold": self.pass_threshold,
            "overall_pass_rate": round(self.overall_pass_rate, 4),
            "passed": self.passed,
            "executive_summary": self.executive_summary(),
            "metrics": [m.to_dict() for m in self.metrics],
            "rule_coverage": [r.to_dict() for r in self.rule_coverage],
            "improvements": self.improvements,
        }

    def executive_summary(self) -> str:
        n_metrics = len(self.metrics)
        n_pass = sum(1 for m in self.metrics if m.passed)
        n_scenarios = sum(len(m.scenarios) for m in self.metrics)
        n_sc_pass = sum(1 for m in self.metrics for s in m.scenarios if s.passed)
        status = "达标" if self.passed else "未达标"
        return (
            f"{status}：{n_pass}/{n_metrics} 项核心指标通过，"
            f"{n_sc_pass}/{n_scenarios} 条场景通过（总通过率 {self.overall_pass_rate:.0%}）。"
        )
