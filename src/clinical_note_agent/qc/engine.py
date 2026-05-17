from __future__ import annotations

from typing import Any

from clinical_note_agent.qc.models import ComplianceResult
from clinical_note_agent.qc.rag_check import check_rag_policy
from clinical_note_agent.qc.rulepack import load_rulepack
from clinical_note_agent.qc.rules_validate import validate_rules
from clinical_note_agent.qc.schema_validate import validate_draft_note_schema

# 附录 B 首期支持的 section_key
INPATIENT_SECTION_KEYS = {
    "chief_complaint",
    "present_illness",
    "past_history",
    "personal_history",
    "marital_reproductive_history",
    "family_history",
    "physical_exam",
    "specialist_exam",
    "auxiliary_exam",
    "preliminary_diagnosis",
    "treatment_plan",
}


def run_compliance(
    draft_note: dict[str, Any],
    *,
    document_type: str,
    department_id: str | None = None,
    template: dict[str, Any] | None = None,
    conflicts: list[dict[str, Any]] | None = None,
    policy: dict[str, Any] | None = None,
    rag_hits: list[dict[str, Any]] | None = None,
) -> ComplianceResult:
    """
    T6 rules.validate + RAG：输出前质控入口。

    对应产品文档 `rules.validate` / `validate.schema` / `validate.rules`。
    """
    pack = load_rulepack(document_type, department_id)
    schema_errors = validate_draft_note_schema(draft_note, document_type=document_type)

    rag_violations = check_rag_policy(draft_note, rag_hits)
    known_keys = INPATIENT_SECTION_KEYS if document_type == "inpatient_admission" else None
    if template and template.get("sections"):
        known_keys = {s["key"] for s in template["sections"] if s.get("key")} | (
            known_keys or set()
        )

    rule_errors, warnings = validate_rules(
        draft_note,
        pack=pack,
        template=template,
        conflicts=conflicts,
        policy=policy,
        rag_violations=rag_violations,
        known_section_keys=known_keys,
    )

    return ComplianceResult(
        errors=schema_errors + rule_errors,
        warnings=warnings,
        rulepack_version=pack.rulepack_version,
    )
