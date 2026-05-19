from __future__ import annotations

import pytest

from clinical_note_agent.document_types import (
    DOCUMENT_TYPES,
    get_document_type,
    list_document_types,
)


def test_five_document_types_registered():
    types = {s.document_type for s in list_document_types()}
    assert types == {
        "inpatient_admission",
        "discharge_summary",
        "first_progress_note",
        "senior_round_note",
        "daily_progress_note",
    }


def test_labels_zh():
    assert get_document_type("first_progress_note").label_zh == "首次病程记录"
    assert get_document_type("senior_round_note").label_zh == "上级医师查房记录"


def test_unknown_type_raises():
    with pytest.raises(ValueError, match="不支持的 document_type"):
        get_document_type("unknown_type")


def test_rulepack_exists_for_structured_types():
    from clinical_note_agent.qc.rulepack import load_rulepack

    for key in ("first_progress_note", "senior_round_note", "daily_progress_note"):
        pack = load_rulepack(key)
        assert pack.document_type == key

    pack = load_rulepack("discharge_summary")
    assert pack.document_type == "discharge_summary"
