from __future__ import annotations

from typing import Any

from clinical_note_agent.qc.discharge_validate import validate_discharge_output
from clinical_note_agent.qc.evidence_grounding import (
    validate_evidence_grounding,
    validate_sparse_input_guard,
)
from clinical_note_agent.qc.models import ComplianceResult
from clinical_note_agent.qc.rulepack import load_rulepack


def run_discharge_compliance(
    output: dict[str, Any],
    *,
    evidence_corpus: str,
    department_id: str | None = None,
    evidence_flags: dict[str, bool] | None = None,
) -> ComplianceResult:
    """
    出院记录质控入口（现行提示词场景）。

    evidence_corpus: 全部记录块拼接文本（不含 [[附加信息]]）
    evidence_flags: admission_date / discharge_date / length_of_stay 是否在证据中存在
    """
    pack = load_rulepack("discharge_summary", department_id)
    flags = evidence_flags or {}

    errors: list = []
    warnings: list = []

    e, w = validate_discharge_output(
        output,
        evidence_has_admission_date=flags.get("admission_date", False),
        evidence_has_discharge_date=flags.get("discharge_date", False),
        evidence_has_length_of_stay=flags.get("length_of_stay", False),
    )
    errors.extend(e)
    warnings.extend(w)

    errors.extend(validate_evidence_grounding(output, evidence_corpus))
    errors.extend(validate_sparse_input_guard(output, evidence_corpus))

    return ComplianceResult(
        errors=errors,
        warnings=warnings,
        rulepack_version=pack.rulepack_version,
    )
