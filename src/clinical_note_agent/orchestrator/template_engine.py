from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "templates" / "inpatient"


def _load_builtin_template(template_id: str) -> dict[str, Any] | None:
    path = _TEMPLATES_DIR / f"{template_id}.yaml"
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_template(request_template: dict[str, Any]) -> dict[str, Any]:
    """合并请求 template 与内置模板（sections 缺省时补 default_text）。"""
    tid = request_template.get("template_id")
    builtin = _load_builtin_template(tid) if tid else None
    if not builtin:
        return request_template

    merged = dict(builtin)
    merged.update({k: v for k, v in request_template.items() if v is not None})
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
        if not default_text:
            draft[key]["gaps"] = ["待补充"]
    return draft
