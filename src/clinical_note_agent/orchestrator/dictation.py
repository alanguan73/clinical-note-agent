from __future__ import annotations

import re
from typing import Any


# 简易口述切分（首期规则，非 LLM）
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("physical_exam", re.compile(r"查体[：:]([^。]+)")),
    ("preliminary_diagnosis", re.compile(r"初步诊断(?:考虑)?[：:为]?([^。；]+)")),
    ("chief_complaint", re.compile(r"主诉[：:]([^。]+)")),
]


def map_dictation_to_sections(
    asr_text: str,
    *,
    speaker_physician: bool = True,
) -> dict[str, dict[str, Any]]:
    """T2：口述 verbatim 映射到 section_key。"""
    if not asr_text.strip():
        return {}

    patches: dict[str, dict[str, Any]] = {}
    remaining = asr_text

    for key, pattern in _PATTERNS:
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
