from __future__ import annotations

import re
from typing import Any


# 简易口述切分（首期规则，非 LLM）
_ADMISSION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("physical_exam", re.compile(r"查体[：:]([^。]+)")),
    ("preliminary_diagnosis", re.compile(r"初步诊断(?:考虑)?[：:为]?([^。；]+)")),
    ("chief_complaint", re.compile(r"主诉[：:]([^。]+)")),
]

_FIRST_PROGRESS_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("course_summary", re.compile(r"病例特点[：:]([^。]+)")),
    ("diagnosis_discussion", re.compile(r"(?:拟诊讨论|诊断讨论)[：:]([^。]+)")),
    ("treatment_plan", re.compile(r"诊疗计划[：:]([^。]+)")),
]

_SENIOR_ROUND_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("round_record", re.compile(r"查房记录[：:]([^。]+)")),
    ("round_opinion", re.compile(r"(?:查房意见|上级医师意见)[：:]([^。]+)")),
    ("treatment_plan", re.compile(r"(?:诊疗计划|治疗计划)[：:]([^。]+)")),
]

_DAILY_PROGRESS_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("daily_course", re.compile(r"(?:病程记录|日常病程)[：:]([^。]+)")),
    ("observation_treatment", re.compile(r"(?:观察与处理|处理意见)[：:]([^。]+)")),
]

_PATTERNS_BY_DOCUMENT_TYPE: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    "inpatient_admission": _ADMISSION_PATTERNS,
    "first_progress_note": _FIRST_PROGRESS_PATTERNS,
    "senior_round_note": _SENIOR_ROUND_PATTERNS,
    "daily_progress_note": _DAILY_PROGRESS_PATTERNS,
}


def map_dictation_to_sections(
    asr_text: str,
    *,
    document_type: str = "inpatient_admission",
    speaker_physician: bool = True,
) -> dict[str, dict[str, Any]]:
    """T2：口述 verbatim 映射到 section_key。"""
    if not asr_text.strip():
        return {}

    patterns = _PATTERNS_BY_DOCUMENT_TYPE.get(document_type, _ADMISSION_PATTERNS)
    patches: dict[str, dict[str, Any]] = {}
    remaining = asr_text

    for key, pattern in patterns:
        m = pattern.search(asr_text)
        if not m:
            continue
        text = m.group(1).strip() if m.lastindex else m.group(0).strip()
        if not text:
            continue
        patches[key] = {
            "text": text if key != "physical_exam" else f"查体：{text}",
            "verbatim": m.group(0).strip(),
            "source_refs": ["asr:final"],
            "source_type": "physician_verbatim" if speaker_physician else "fact",
            "section_status": "ok",
            "locked": False,
        }
        remaining = remaining.replace(m.group(0), "")

    if document_type != "inpatient_admission":
        if not patches and asr_text.strip():
            fallback_key = {
                "first_progress_note": "course_summary",
                "senior_round_note": "round_record",
                "daily_progress_note": "daily_course",
            }.get(document_type)
            if fallback_key:
                patches[fallback_key] = {
                    "text": asr_text.strip(),
                    "verbatim": asr_text.strip(),
                    "source_refs": ["asr:final"],
                    "source_type": "physician_verbatim" if speaker_physician else "fact",
                    "section_status": "ok",
                    "locked": False,
                }
        return patches

    # 若整段像查体描述且无匹配，落入 physical_exam（D-1）
    if not patches and ("呼吸音" in asr_text or "查体" in asr_text):
        patches["physical_exam"] = {
            "text": asr_text.strip(),
            "verbatim": asr_text.strip(),
            "source_refs": ["asr:final"],
            "source_type": "physician_verbatim",
            "section_status": "ok",
            "locked": False,
        }

    # 诊断句若单独出现
    if "初步诊断" in asr_text and "preliminary_diagnosis" not in patches:
        m = re.search(r"初步诊断(?:考虑)?[：:为]?([^。；]+)", asr_text)
        if m:
            patches["preliminary_diagnosis"] = {
                "text": m.group(1).strip(),
                "verbatim": m.group(0).strip(),
                "source_refs": ["asr:final"],
                "source_type": "physician_verbatim",
                "section_status": "ok",
                "locked": True,
            }

    return patches
