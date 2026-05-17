from __future__ import annotations

import re
from typing import Any


def fill_labs_imaging(
    draft_note: dict[str, Any],
    evidence: dict[str, Any],
    *,
    template_id: str,
) -> dict[str, Any] | None:
    """T1：检验/影像结构化写入 auxiliary_exam。"""
    labs = evidence.get("labs_struct") or []
    imaging = evidence.get("imaging_struct") or []
    if not labs and not imaging:
        return None

    parts: list[str] = []
    refs: list[str] = []
    for lab in labs:
        name = lab.get("name") or lab.get("code", "")
        val = lab.get("value", "")
        unit = lab.get("unit", "")
        flag = lab.get("flag", "")
        flag_s = f"（{flag}）" if flag else ""
        parts.append(f"{name} {val}{unit}{flag_s}".strip())
        if lab.get("source_ref"):
            refs.append(lab["source_ref"])
    for img in imaging:
        imp = img.get("impression") or img.get("findings", "")
        modality = img.get("modality", "")
        body = img.get("body_part", "")
        if imp:
            parts.append(f"{modality} {body}：{imp}".strip())
        if img.get("source_ref"):
            refs.append(img["source_ref"])

    text = "；".join(parts)
    return {
        "text": text,
        "source_refs": refs or [f"template:{template_id}"],
        "source_type": "fact",
        "section_status": "ok",
        "locked": False,
    }


def detect_wbc_conflict(
    evidence: dict[str, Any],
) -> dict[str, Any] | None:
    """D-2 风格：LIS WBC vs 口述「白细胞」冲突。"""
    asr = (evidence.get("asr_final_text") or "").strip()
    if not asr or "白细胞" not in asr:
        return None
    labs = evidence.get("labs_struct") or []
    wbc = next((l for l in labs if (l.get("code") or "").upper() == "WBC"), None)
    if not wbc:
        return None

    structured_display = f"{wbc.get('name', '白细胞')} {wbc.get('value', '')}{wbc.get('unit', '')}"
    # 提取口述片段（简化）
    m = re.search(r"白细胞[^。；\n]*", asr)
    dictation_display = m.group(0) if m else "白细胞（口述）"

    return {
        "conflict_id": "c_wbc_1",
        "field": "auxiliary_exam.wbc",
        "resolution": "pending",
        "structured": {
            "display": structured_display.strip(),
            "value": wbc.get("value"),
            "unit": wbc.get("unit"),
            "source_ref": wbc.get("source_ref", "lis:unknown"),
        },
        "dictation": {
            "display": dictation_display,
            "verbatim": dictation_display,
            "source_ref": "asr:final",
        },
    }


def apply_conflict_to_auxiliary(
    section: dict[str, Any],
    conflict: dict[str, Any],
) -> dict[str, Any]:
    """冲突待决：双轨展示，不静默选一。"""
    return {
        **section,
        "text": None,
        "display_mode": "conflict_pending",
        "candidates": [
            {"source": "structured", "display": conflict["structured"]["display"]},
            {"source": "dictation", "display": conflict["dictation"]["display"]},
        ],
        "section_status": "ok",
    }
