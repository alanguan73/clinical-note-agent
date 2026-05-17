from __future__ import annotations

import re
from dataclasses import dataclass

# 入院/出院日期与住院天数是否在证据中出现（场景 E）
_DATE_RE = re.compile(r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?")
_ADMISSION_HINTS = re.compile(
    r"入院(?:日期|时间)?|于\s*\d{4}|收住入院|办理入院|入院记录",
    re.I,
)
_DISCHARGE_HINTS = re.compile(
    r"出院(?:日期|时间)?|准予\s*(?:今日)?出院|办理出院|出院记录",
    re.I,
)
_LOS_HINTS = re.compile(r"住院\s*\d+\s*天|住院天数|共住院", re.I)


@dataclass
class EvidenceFlags:
    admission_date: bool = False
    discharge_date: bool = False
    length_of_stay: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "admission_date": self.admission_date,
            "discharge_date": self.discharge_date,
            "length_of_stay": self.length_of_stay,
        }


def detect_evidence_flags(corpus: str) -> EvidenceFlags:
    """从 fact corpus 推断日期类字段是否可有依据输出。"""
    text = corpus or ""
    has_date = bool(_DATE_RE.search(text))
    flags = EvidenceFlags()

    if _ADMISSION_HINTS.search(text) and has_date:
        flags.admission_date = True
    if _DISCHARGE_HINTS.search(text) and has_date:
        flags.discharge_date = True
    if _LOS_HINTS.search(text):
        flags.length_of_stay = True
    elif flags.admission_date and flags.discharge_date:
        flags.length_of_stay = True

    # 当前病历 key 行
    if re.search(r"入院日期\s*::", text):
        flags.admission_date = True
    if re.search(r"出院日期\s*::", text):
        flags.discharge_date = True
    if re.search(r"住院天数\s*::", text):
        flags.length_of_stay = True

    return flags
