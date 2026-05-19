from __future__ import annotations

import json
from pathlib import Path

import pytest

from clinical_note_agent.evaluation import load_evaluation_plan, run_evaluation
from clinical_note_agent.evaluation.report import report_to_markdown, write_report

REPO = Path(__file__).resolve().parents[1]
SAMPLE_PLAN = REPO / "evaluation/plans/sample.discharge_admission_qc.yaml"


def test_load_sample_plan():
    plan = load_evaluation_plan(SAMPLE_PLAN)
    assert plan["id"] == "discharge-admission-qc-baseline"
    assert len(plan["core_metrics"]) >= 5


def test_run_sample_evaluation_passes():
    report = run_evaluation(SAMPLE_PLAN)
    assert report.passed, report.executive_summary()
    assert report.overall_pass_rate == 1.0
    assert len(report.metrics) == 6
    for m in report.metrics:
        assert m.passed, f"{m.metric_id}: {[s.message for s in m.scenarios if not s.passed]}"


def test_report_markdown_and_json(tmp_path):
    report = run_evaluation(SAMPLE_PLAN)
    json_path = tmp_path / "out.json"
    md_path = tmp_path / "out.md"
    data = write_report(report, json_path=str(json_path), markdown_path=str(md_path))
    assert data["passed"] is True
    assert "executive_summary" in data
    md = md_path.read_text(encoding="utf-8")
    assert "## 执行摘要" in md
    assert report_to_markdown(report) == md
    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded["plan_id"] == "discharge-admission-qc-baseline"


def test_rule_coverage_populated():
    report = run_evaluation(SAMPLE_PLAN)
    assert len(report.rule_coverage) > 0
    w06 = next((r for r in report.rule_coverage if r.rule_id == "W06"), None)
    assert w06 is not None
    assert w06.status == "implemented"
