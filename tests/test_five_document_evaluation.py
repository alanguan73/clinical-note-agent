from __future__ import annotations

from pathlib import Path

from clinical_note_agent.evaluation.runner import run_evaluation

REPO = Path(__file__).resolve().parents[1]
FIVE_PLAN = REPO / "evaluation/plans/sample.five_document_types.yaml"


def test_five_document_types_evaluation():
    report = run_evaluation(FIVE_PLAN)
    assert report.passed
    assert len(report.metrics) == 3
