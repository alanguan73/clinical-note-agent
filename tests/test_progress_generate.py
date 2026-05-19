from __future__ import annotations

from pathlib import Path

import yaml

from clinical_note_agent.orchestrator import GenerateRequest, collect_note_generate

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> GenerateRequest:
    data = yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))
    return GenerateRequest(
        template=data["template"],
        evidence=data["evidence"],
        document_type=data["document_type"],
        department_id=data.get("department_id"),
    )


def test_first_progress_generate():
    result = collect_note_generate(_load("first_progress_request.yaml"))
    assert result.draft_note["course_summary"]["text"]
    assert "发热" in result.draft_note["course_summary"]["text"]
    assert result.draft_note["treatment_plan"]["source_type"] == "physician_verbatim"
    assert result.compliance["errors"] == []


def test_senior_round_generate():
    result = collect_note_generate(_load("senior_round_request.yaml"))
    assert "精神" in result.draft_note["round_record"]["text"]
    assert result.compliance["errors"] == []


def test_daily_progress_generate():
    result = collect_note_generate(_load("daily_progress_request.yaml"))
    assert result.draft_note["daily_course"]["text"]
    assert result.compliance["errors"] == []


def test_empty_progress_fails_compliance():
    req = GenerateRequest(
        template={"template_id": "daily_progress_default"},
        evidence={},
        document_type="daily_progress_note",
    )
    result = collect_note_generate(req)
    assert any(e["code"] == "REQUIRED_SECTION_EMPTY" for e in result.compliance["errors"])
