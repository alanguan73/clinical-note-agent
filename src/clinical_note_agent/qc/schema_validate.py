from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

from clinical_note_agent.document_types import SCHEMA_VALIDATED_TYPES
from clinical_note_agent.qc.models import ComplianceIssue

_SCHEMAS_DIR = Path(__file__).resolve().parents[3] / "schemas"
_SECTION_SCHEMA: dict[str, Any] | None = None


def _section_schema() -> dict[str, Any]:
    global _SECTION_SCHEMA
    if _SECTION_SCHEMA is None:
        path = _SCHEMAS_DIR / "draft_note_section.json"
        with path.open(encoding="utf-8") as f:
            _SECTION_SCHEMA = json.load(f)
    return _SECTION_SCHEMA


def validate_draft_note_schema(
    draft_note: dict[str, Any],
    *,
    document_type: str,
) -> list[ComplianceIssue]:
    """validate.schema：校验 draft_note 各节对象形态。"""
    if document_type not in SCHEMA_VALIDATED_TYPES:
        return []

    validator = Draft202012Validator(_section_schema())
    issues: list[ComplianceIssue] = []

    for section_key, section in draft_note.items():
        if not isinstance(section, dict):
            issues.append(
                ComplianceIssue(
                    code="SCHEMA_INVALID",
                    severity="error",
                    field=f"draft_note.{section_key}",
                    message=f"章节 {section_key} 必须为对象",
                )
            )
            continue
        for err in validator.iter_errors(section):
            field_path = f"draft_note.{section_key}"
            if err.path:
                field_path += "." + ".".join(str(p) for p in err.path)
            issues.append(
                ComplianceIssue(
                    code="SCHEMA_INVALID",
                    severity="error",
                    field=field_path,
                    message=_format_validation_error(err),
                )
            )
    return issues


def _format_validation_error(err: ValidationError) -> str:
    loc = ".".join(str(p) for p in err.path)
    return f"字段不符合 Schema：{loc or 'root'} — {err.message}"
