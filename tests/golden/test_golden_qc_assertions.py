"""金样例中与质控相关的断言（可随完整生成流水线扩展）。"""

from __future__ import annotations

import json
from pathlib import Path

from clinical_note_agent.qc import run_compliance

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_golden_d2_qc_assertions():
    """D-2：冲突为 warning、可保存草稿、默认不阻断签收。"""
    payload = json.loads((FIXTURES / "d2_conflict_warning.json").read_text(encoding="utf-8"))
    result = run_compliance(
        payload["draft_note"],
        document_type=payload["document_type"],
        department_id=payload["department_id"],
        template=payload["template"],
        conflicts=payload["conflicts"],
    )
    assert result.ok_for_draft  # draft_save_allowed
    assert result.can_sign(blocks_sign_on_conflict=False)  # sign_allowed_with_strong_warning
    w = next(x for x in result.warnings if x.code == "CONFLICT_UNRESOLVED")
    assert w.severity == "strong"
    assert "wbc" in w.field
    assert w.blocks_sign is False


def test_golden_d1_compliance_errors_empty():
    payload = json.loads((FIXTURES / "d1_draft_pass.json").read_text(encoding="utf-8"))
    result = run_compliance(
        payload["draft_note"],
        document_type=payload["document_type"],
        department_id=payload["department_id"],
        template=payload["template"],
        conflicts=payload.get("conflicts"),
    )
    assert len(result.errors) == 0
