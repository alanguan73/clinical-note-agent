from __future__ import annotations

import json
from pathlib import Path

import pytest

from clinical_note_agent.qc import run_compliance

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    with (FIXTURES / name).open(encoding="utf-8") as f:
        return json.load(f)


def test_d1_compliance_errors_empty():
    payload = _load("d1_draft_pass.json")
    result = run_compliance(
        payload["draft_note"],
        document_type=payload["document_type"],
        department_id=payload["department_id"],
        template=payload["template"],
        conflicts=payload["conflicts"],
    )
    assert result.errors == []
    assert result.ok_for_draft
    assert result.rulepack_version.startswith("1.0.0")


def test_d2_conflict_is_warning_not_error():
    payload = _load("d2_conflict_warning.json")
    result = run_compliance(
        payload["draft_note"],
        document_type=payload["document_type"],
        department_id=payload["department_id"],
        template=payload["template"],
        conflicts=payload["conflicts"],
    )
    assert result.ok_for_draft
    codes = [w.code for w in result.warnings]
    assert "CONFLICT_UNRESOLVED" in codes
    conflict = next(w for w in result.warnings if w.code == "CONFLICT_UNRESOLVED")
    assert conflict.severity == "strong"
    assert conflict.field == "auxiliary_exam.wbc"
    assert conflict.blocks_sign is False
    assert result.can_sign()


def test_ai_invented_diagnosis_blocked():
    draft = _load("d1_draft_pass.json")["draft_note"]
    draft["preliminary_diagnosis"] = {
        "text": "肺癌",
        "source_type": "llm_patch",
        "section_status": "ok",
    }
    result = run_compliance(
        draft,
        document_type="inpatient_admission",
        department_id="thoracic_surgery",
    )
    assert any(e.code == "AI_INVENTED_DIAGNOSIS" for e in result.errors)


def test_pediatrics_forbidden_term():
    draft = {
        "chief_complaint": {"text": "发热2天", "section_status": "ok"},
        "present_illness": {"text": "患儿发热，饮酒史20年。", "section_status": "ok"},
        "past_history": {"text": "既往体健", "section_status": "ok"},
        "physical_exam": {"text": "神志清", "section_status": "ok"},
        "auxiliary_exam": {
            "text": "CRP 28",
            "source_refs": ["lis:ord_3001"],
            "section_status": "ok",
        },
    }
    result = run_compliance(
        draft,
        document_type="inpatient_admission",
        department_id="pediatrics",
    )
    assert any(w.code == "PEDIATRICS_TERM_INAPPROPRIATE" for w in result.warnings)


def test_rag_forbidden_phrase():
    draft = _load("d1_draft_pass.json")["draft_note"]
    result = run_compliance(
        draft,
        document_type="inpatient_admission",
        department_id="thoracic_surgery",
        rag_hits=[
            {
                "section_key": "present_illness",
                "forbidden_phrases": ["交通事故"],
            }
        ],
    )
    assert any(w.code == "RAG_POLICY_VIOLATION" for w in result.warnings)


def test_required_section_empty():
    draft = {"chief_complaint": {"text": "", "section_status": "ok"}}
    result = run_compliance(
        draft,
        document_type="inpatient_admission",
        department_id="thoracic_surgery",
    )
    assert any(e.code == "REQUIRED_SECTION_EMPTY" for e in result.errors)


def test_schema_invalid_source_type():
    draft = {
        "chief_complaint": {
            "text": "胸痛",
            "source_type": "invalid_type",
            "section_status": "ok",
        }
    }
    result = run_compliance(
        draft,
        document_type="inpatient_admission",
    )
    assert any(e.code == "SCHEMA_INVALID" for e in result.errors)
