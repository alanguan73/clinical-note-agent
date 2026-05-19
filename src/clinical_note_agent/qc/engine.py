from __future__ import annotations

from typing import Any

from clinical_note_agent.document_types import DOCUMENT_TYPES, get_document_type
from clinical_note_agent.qc.models import ComplianceResult
from clinical_note_agent.qc.rag_check import check_rag_policy
from clinical_note_agent.qc.rulepack import load_rulepack
from clinical_note_agent.qc.rules_validate import validate_rules
from clinical_note_agent.qc.schema_validate import validate_draft_note_schema

# 附录 B 入院记录 section_key（向后兼容导出）
INPATIENT_SECTION_KEYS = DOCUMENT_TYPES["inpatient_admission"].section_keys


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
    try:
        spec = get_document_type(document_type)
        known_keys: set[str] | None = set(spec.section_keys) if spec.generation_mode == "structured_stream" else None
    except ValueError:
        known_keys = None
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
