from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from clinical_note_agent.document_types import get_document_type

_TEMPLATES_ROOT = Path(__file__).resolve().parents[3] / "templates"


def template_dir_for(document_type: str) -> Path:
    spec = get_document_type(document_type)
    return _TEMPLATES_ROOT / spec.template_subdir


def _load_builtin_template(template_id: str, document_type: str) -> dict[str, Any] | None:
    directory = template_dir_for(document_type)
    path = directory / f"{template_id}.yaml"
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data and data.get("document_type") and data["document_type"] != document_type:
        raise ValueError(
            f"模板 {template_id} 的 document_type={data['document_type']} "
            f"与请求 {document_type} 不一致"
        )
    return data


def resolve_template(request_template: dict[str, Any], *, document_type: str) -> dict[str, Any]:
    """合并请求 template 与内置模板（sections 缺省时补 default_text）。"""
    get_document_type(document_type)
    tid = request_template.get("template_id")
    builtin = _load_builtin_template(tid, document_type) if tid else None
    if not builtin:
        if request_template.get("sections"):
            return {**request_template, "document_type": document_type}
        raise ValueError(
            f"未找到模板 {tid!r}（document_type={document_type}），"
            f"请提供 template.sections 或使用内置 template_id"
        )

    merged = dict(builtin)
    merged.update({k: v for k, v in request_template.items() if v is not None})
    merged["document_type"] = document_type
    req_sections = {s["key"]: s for s in request_template.get("sections", []) if s.get("key")}
    sections_out = []
    for sec in builtin.get("sections", []):
        key = sec["key"]
        row = dict(sec)
        if key in req_sections:
            row.update(req_sections[key])
        sections_out.append(row)
    for key, sec in req_sections.items():
        if not any(s["key"] == key for s in sections_out):
            sections_out.append(sec)
    merged["sections"] = sections_out
    return merged


def build_template_draft_note(template: dict[str, Any]) -> dict[str, Any]:
    """T0：由模板生成 draft_note 骨架（template_default）。"""
    tid = template.get("template_id", "unknown")
    draft: dict[str, Any] = {}
    for sec in template.get("sections", []):
        key = sec.get("key")
        if not key:
            continue
        default_text = sec.get("default_text", "")
        draft[key] = {
            "text": default_text,
            "source_refs": [f"template:{tid}"],
            "source_type": "template_default",
            "section_status": "ok",
            "locked": False,
        }
        if not default_text and sec.get("required", True):
            draft[key]["gaps"] = ["待补充"]
    return draft
