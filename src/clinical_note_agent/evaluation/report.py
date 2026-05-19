from __future__ import annotations

import json
from typing import Any

from clinical_note_agent.evaluation.models import EvaluationReport


def report_to_markdown(report: EvaluationReport) -> str:
    """生成 Markdown 质控评估报告。"""
    lines: list[str] = [
        f"# 质控评估报告：{report.plan_name}",
        "",
        f"- **计划 ID**: `{report.plan_id}`",
        f"- **版本**: {report.plan_version}",
        f"- **范围**: {', '.join(report.scope)}",
        f"- **通过率阈值**: {report.pass_threshold:.0%}",
        f"- **总结果**: {'✅ 达标' if report.passed else '❌ 未达标'}",
        "",
        "## 执行摘要",
        "",
        report.executive_summary(),
        "",
    ]

    if report.architecture:
        lines.extend(["## 分析架构", "", "```text", *report.architecture, "```", ""])

    lines.extend(["## 指标分析", ""])
    for m in report.metrics:
        icon = "✅" if m.passed else "❌"
        lines.append(
            f"### {icon} {m.metric_id} — {m.name} "
            f"（通过率 {m.pass_rate:.0%}，目标 ≥ {m.target_pass_rate:.0%}）"
        )
        lines.append("")
        lines.append("| 场景 | 结果 | 说明 |")
        lines.append("|------|------|------|")
        for s in m.scenarios:
            mark = "通过" if s.passed else "失败"
            lines.append(f"| `{s.scenario_id}` | {mark} | {s.message} |")
        lines.append("")

    if report.rule_coverage:
        lines.extend(["## 规则覆盖（提示词目录）", ""])
        lines.append("| 规则 | 状态 | machine_code | 本轮指标 |")
        lines.append("|------|------|--------------|----------|")
        for r in report.rule_coverage:
            covered = ", ".join(r.covered_by_metrics) if r.covered_by_metrics else "—"
            lines.append(
                f"| {r.rule_id} {r.name} | {r.status} | {r.machine_code or '—'} | {covered} |"
            )
        lines.append("")

    if report.improvements:
        lines.extend(["## 改进建议", ""])
        for i, tip in enumerate(report.improvements, 1):
            lines.append(f"{i}. {tip}")
        lines.append("")

    return "\n".join(lines)


def write_report(
    report: EvaluationReport,
    *,
    json_path: str | None = None,
    markdown_path: str | None = None,
) -> dict[str, Any]:
    """写入 JSON / Markdown 报告文件。"""
    from pathlib import Path

    data = report.to_dict()
    if json_path:
        p = Path(json_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    if markdown_path:
        p = Path(markdown_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            f.write(report_to_markdown(report))
    return data
