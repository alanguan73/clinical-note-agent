from __future__ import annotations

import json
from pathlib import Path

import yaml

from clinical_note_agent.qc.discharge_engine import run_discharge_compliance
from clinical_note_agent.qc.evidence_grounding import validate_evidence_grounding

GOLDEN = Path(__file__).parent / "golden"


def _load_golden(name: str) -> dict:
    with (GOLDEN / name).open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_d7_minimal_input_hallucination():
    case = _load_golden("D-7-minimal-input-anti-hallucination.yaml")
    flags = case["evidence_flags"]

    bad = run_discharge_compliance(
        case["writing_ai_output_bad"],
        evidence_corpus=case["evidence_corpus"],
        evidence_flags=flags,
    )
    assert not bad.ok_for_draft
    assert any(e.code == "SPARSE_INPUT_EXCESS_OUTPUT" for e in bad.errors)
    assert any(e.code == "UNGROUNDED_CLAIM" for e in bad.errors)

    good = run_discharge_compliance(
        case["writing_ai_output_good"],
        evidence_corpus=case["evidence_corpus"],
        evidence_flags=flags,
    )
    assert good.ok_for_draft


def test_d8_rich_input_grounded():
    case = _load_golden("D-8-rich-input-no-overdelete.yaml")
    good = run_discharge_compliance(
        case["writing_ai_output_good"],
        evidence_corpus=case["evidence_corpus"],
    )
    assert good.ok_for_draft
    assert "7.66" in case["evidence_corpus"]

    # 误删后 WBC 数值不在输出中，但仍在证据中 — 供人工/LLM 质控对比
    over = case["writing_ai_output_overdelete_bad"]
    assert "7.66" not in over.get("入院情况", "")


def test_d9_scene_e_placeholder():
    case = _load_golden("D-9-scene-e-dates.yaml")
    bad = run_discharge_compliance(
        case["writing_ai_output_bad"],
        evidence_corpus=case["evidence_corpus"],
        evidence_flags=case["evidence_flags"],
    )
    assert any(e.code == "SCENE_E_PLACEHOLDER" for e in bad.errors)

    good = run_discharge_compliance(
        case["writing_ai_output_good"],
        evidence_corpus=case["evidence_corpus"],
        evidence_flags=case["evidence_flags"],
    )
    assert good.ok_for_draft


def test_length_of_stay_plus_one():
    output = {
        "入院日期": "2025-01-08",
        "出院日期": "2025-01-12",
        "住院天数": "4天",
    }
    result = run_discharge_compliance(
        output,
        evidence_corpus="入院 2025-01-08 出院 2025-01-12",
        evidence_flags={
            "admission_date": True,
            "discharge_date": True,
            "length_of_stay": True,
        },
    )
    assert any(e.code == "LENGTH_OF_STAY_MISMATCH" for e in result.errors)

    output["住院天数"] = "5天"
    result2 = run_discharge_compliance(
        output,
        evidence_corpus="x",
        evidence_flags={
            "admission_date": True,
            "discharge_date": True,
            "length_of_stay": True,
        },
    )
    assert not any(e.code == "LENGTH_OF_STAY_MISMATCH" for e in result2.errors)


def test_ungrounded_numeric():
    issues = validate_evidence_grounding(
        {"诊疗经过": "白细胞 99.9×10^9/L"},
        "白细胞 12.5×10^9/L",
    )
    assert any(i.code == "UNGROUNDED_NUMERIC" for i in issues)
