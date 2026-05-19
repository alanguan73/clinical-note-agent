from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from clinical_note_agent.evaluation.models import RuleCoverageRow


def load_rule_catalog(catalog_path: Path) -> list[dict[str, Any]]:
    with catalog_path.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    rows: list[dict[str, Any]] = []
    for section in ("writing_rules", "qc_rules"):
        for rule in doc.get(section, []):
            rows.append(
                {
                    "rule_id": rule.get("id"),
                    "name": rule.get("name"),
                    "status": rule.get("status"),
                    "machine_code": rule.get("machine_code"),
                    "golden": rule.get("golden"),
                    "section": section,
                }
            )
    return rows


def build_rule_coverage(
    catalog_path: Path,
    metrics: list[Any],
    *,
    track_status: list[str] | None = None,
) -> list[RuleCoverageRow]:
    """将规则目录与评估指标关联，标出本轮覆盖情况。"""
    track_status = track_status or ["implemented", "partial", "llm_only", "planned"]
    catalog = load_rule_catalog(catalog_path)

    metric_codes: dict[str, list[str]] = {}
    for m in metrics:
        if hasattr(m, "metric_id"):
            mid = m.metric_id
            codes = getattr(m, "machine_codes", []) or []
        else:
            mid = m.get("id", m.get("metric_id", ""))
            codes = m.get("machine_codes", []) or []
        for code in codes or []:
            metric_codes.setdefault(code, []).append(mid)

    coverage: list[RuleCoverageRow] = []
    for row in catalog:
        if row["status"] not in track_status:
            continue
        code = row.get("machine_code")
        if code and " " in str(code):
            code = str(code).split()[0]
        covered: list[str] = []
        if code:
            covered = metric_codes.get(code, [])
        golden = row.get("golden")
        if golden and not covered:
            for mid, _ in metric_codes.items():
                if golden and golden in str(golden):
                    covered.append(mid)

        coverage.append(
            RuleCoverageRow(
                rule_id=row["rule_id"] or "",
                name=row["name"] or "",
                status=row["status"] or "",
                machine_code=code,
                golden=str(golden) if golden else None,
                covered_by_metrics=list(dict.fromkeys(covered)),
            )
        )
    return coverage


def suggest_improvements(coverage: list[RuleCoverageRow], metrics: list[Any]) -> list[str]:
    """根据未达标指标与 planned 规则生成改进建议。"""
    tips: list[str] = []
    for m in metrics:
        if hasattr(m, "passed") and not m.passed:
            failed = [s.scenario_id for s in m.scenarios if not s.passed]
            tips.append(f"优先修复指标 {m.metric_id}（{m.name}）失败场景: {', '.join(failed)}")
    planned = [r for r in coverage if r.status == "planned"]
    if planned:
        ids = ", ".join(r.rule_id for r in planned[:5])
        tips.append(f"将 planned 规则程序化（建议从 {ids} 起），减少 llm_only 兜底")
    llm_only = [r for r in coverage if r.status == "llm_only" and not r.covered_by_metrics]
    if llm_only:
        tips.append(
            f"本轮未覆盖的 llm_only 规则共 {len(llm_only)} 条，"
            "可补充金样例或 LLM 质控回归场景"
        )
    return tips
