from __future__ import annotations

from typing import Any

from clinical_note_agent.qc.models import ComplianceIssue
from clinical_note_agent.qc.rulepack import ForbiddenPattern, RulePack

# 固定文案表（§9.7）：客户端可用 code 映射；此处附带默认 message
_MESSAGES: dict[str, str] = {
    "REQUIRED_SECTION_EMPTY": "必填章节内容为空，请补充或标注待核实。",
    "MISSING_SOURCE_REFS": "该章节含检验/检查内容但缺少可追溯来源引用。",
    "AI_INVENTED_DIAGNOSIS": "初步诊断须来自医师口述或手工录入，系统不得自动推断。",
    "CONFLICT_UNRESOLVED": "字段存在未解决的结构化与口述冲突，请核对。",
    "SECTION_DEGRADED": "该章节生成降级，请人工补全。",
    "RAG_POLICY_VIOLATION": "内容与院规书写要求不一致，请核对引用规范。",
    "UNKNOWN_SECTION_KEY": "存在未在模板/Schema 中定义的章节键，已忽略写入。",
}


def _section_text(section: dict[str, Any] | None) -> str | None:
    if not section or not isinstance(section, dict):
        return None
    text = section.get("text")
    if text is None:
        return None
    return str(text).strip() or None


def _is_effectively_empty(section: dict[str, Any] | None) -> bool:
    if not section:
        return True
    if section.get("display_mode") == "conflict_pending":
        # 冲突待决：有 structured/dictation 展示，不算“空”
        if section.get("candidates") or section.get("structured") or section.get("dictation"):
            return False
    text = _section_text(section)
    return not text


def validate_rules(
    draft_note: dict[str, Any],
    *,
    pack: RulePack,
    template: dict[str, Any] | None,
    conflicts: list[dict[str, Any]] | None,
    policy: dict[str, Any] | None,
    rag_violations: list[dict[str, Any]] | None,
    known_section_keys: set[str] | None,
) -> tuple[list[ComplianceIssue], list[ComplianceIssue]]:
    """validate.rules：病案质控规则包。"""
    errors: list[ComplianceIssue] = []
    warnings: list[ComplianceIssue] = []
    policy = policy or {}
    blocks_sign_on_conflict = bool(
        policy.get("blocks_sign_on_conflict")
        or policy.get("compliance", {}).get("policy", {}).get("blocks_sign_on_conflict")
    )

    required = pack.required_sections(template)
    for key in required:
        section = draft_note.get(key)
        if _is_effectively_empty(section):
            errors.append(
                ComplianceIssue(
                    code="REQUIRED_SECTION_EMPTY",
                    severity="error",
                    field=f"draft_note.{key}",
                    message=_MESSAGES["REQUIRED_SECTION_EMPTY"],
                )
            )

    for key in pack.sections_requiring_source_refs:
        section = draft_note.get(key)
        if not section or _is_effectively_empty(section):
            continue
        refs = section.get("source_refs") or []
        if not refs:
            warnings.append(
                ComplianceIssue(
                    code="MISSING_SOURCE_REFS",
                    severity="warning",
                    field=f"draft_note.{key}",
                    message=_MESSAGES["MISSING_SOURCE_REFS"],
                )
            )

    for key in pack.physician_only_sections:
        section = draft_note.get(key)
        if not section or _is_effectively_empty(section):
            continue
        source_type = section.get("source_type")
        if source_type == "llm_patch":
            errors.append(
                ComplianceIssue(
                    code="AI_INVENTED_DIAGNOSIS",
                    severity="error",
                    field=f"draft_note.{key}",
                    message=_MESSAGES["AI_INVENTED_DIAGNOSIS"],
                )
            )

    for key, section in draft_note.items():
        if isinstance(section, dict) and section.get("section_status") == "degraded":
            warnings.append(
                ComplianceIssue(
                    code="SECTION_DEGRADED",
                    severity="warning",
                    field=f"draft_note.{key}",
                    message=_MESSAGES["SECTION_DEGRADED"],
                )
            )

    if known_section_keys:
        for key in draft_note:
            if key not in known_section_keys:
                warnings.append(
                    ComplianceIssue(
                        code="UNKNOWN_SECTION_KEY",
                        severity="warning",
                        field=f"draft_note.{key}",
                        message=_MESSAGES["UNKNOWN_SECTION_KEY"],
                    )
                )

    for conflict in conflicts or []:
        if conflict.get("resolution", "pending") != "pending":
            continue
        field = conflict.get("field", "unknown")
        warnings.append(
            ComplianceIssue(
                code="CONFLICT_UNRESOLVED",
                severity="strong",
                field=field,
                message=_MESSAGES["CONFLICT_UNRESOLVED"],
                blocks_sign=blocks_sign_on_conflict,
            )
        )

    for violation in rag_violations or []:
        warnings.append(
            ComplianceIssue(
                code=violation.get("code", "RAG_POLICY_VIOLATION"),
                severity=violation.get("severity", "warning"),
                field=violation.get("field", "draft_note"),
                message=violation.get("message", _MESSAGES["RAG_POLICY_VIOLATION"]),
            )
        )

    _apply_forbidden_patterns(draft_note, pack.forbidden_patterns, warnings)
    return errors, warnings


def _apply_forbidden_patterns(
    draft_note: dict[str, Any],
    patterns: list[ForbiddenPattern],
    warnings: list[ComplianceIssue],
) -> None:
    for key, section in draft_note.items():
        if not isinstance(section, dict):
            continue
        text = _section_text(section) or ""
        for fp in patterns:
            if fp._compiled.search(text):
                warnings.append(
                    ComplianceIssue(
                        code=fp.code,
                        severity="warning",
                        field=f"draft_note.{key}",
                        message=fp.message,
                    )
                )
