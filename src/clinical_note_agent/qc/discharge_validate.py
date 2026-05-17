from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from clinical_note_agent.qc.models import ComplianceIssue

# 出院记录 JSON 字段（中文 key，与现行提示词一致）
FIELD_ADMISSION_DATE = "入院日期"
FIELD_DISCHARGE_DATE = "出院日期"
FIELD_LENGTH_OF_STAY = "住院天数"
FIELD_ADMISSION_STATUS = "入院情况"
FIELD_ADMISSION_DX = "入院诊断"
FIELD_TREATMENT = "诊疗经过"
FIELD_DISCHARGE_STATUS = "出院情况"
FIELD_DISCHARGE_DX = "出院诊断"
FIELD_DISCHARGE_ORDERS = "出院医嘱"

SCENE_E_FIELDS = {FIELD_ADMISSION_DATE, FIELD_DISCHARGE_DATE, FIELD_LENGTH_OF_STAY}

PLACEHOLDER_PATTERNS = [
    re.compile(r"^\s*$"),
    re.compile(r"\[日期待补\]", re.I),
    re.compile(r"待补"),
    re.compile(r"信息不详"),
    re.compile(r"^不详\s*$"),
]

DATE_FMT = "%Y-%m-%d"
LOS_PATTERN = re.compile(r"(\d+)\s*天")


def _is_placeholder(value: str) -> bool:
    for pat in PLACEHOLDER_PATTERNS:
        if pat.search(value):
            return True
    return False


def _parse_date(value: str) -> datetime | None:
    value = value.strip()
    try:
        return datetime.strptime(value[:10], DATE_FMT)
    except ValueError:
        return None


def validate_discharge_output(
    output: dict[str, Any],
    *,
    evidence_has_admission_date: bool = False,
    evidence_has_discharge_date: bool = False,
    evidence_has_length_of_stay: bool = False,
) -> tuple[list[ComplianceIssue], list[ComplianceIssue]]:
    """
    出院记录程序质控（提示词场景 E、住院天数、占位符）。

    evidence_has_*：由上游解析全部记录块后传入；全无则不应输出对应 key。
    """
    errors: list[ComplianceIssue] = []
    warnings: list[ComplianceIssue] = []

    for key, value in output.items():
        if not isinstance(value, str):
            continue
        if _is_placeholder(value):
            errors.append(
                ComplianceIssue(
                    code="SCENE_E_PLACEHOLDER",
                    severity="error",
                    field=key,
                    message="禁止使用空值、待补、不详等占位，应删除该字段 key。",
                )
            )

    # 场景 E：证据中无日期信息却输出了日期字段
    scene_e_map = {
        FIELD_ADMISSION_DATE: evidence_has_admission_date,
        FIELD_DISCHARGE_DATE: evidence_has_discharge_date,
        FIELD_LENGTH_OF_STAY: evidence_has_length_of_stay,
    }
    for field, has_evidence in scene_e_map.items():
        if field in output and not has_evidence:
            warnings.append(
                ComplianceIssue(
                    code="SCENE_E_UNEXPECTED_FIELD",
                    severity="warning",
                    field=field,
                    message="全部原始数据与当前病历均无该日期信息，不应输出此字段。",
                )
            )

    adm = output.get(FIELD_ADMISSION_DATE)
    dis = output.get(FIELD_DISCHARGE_DATE)
    los = output.get(FIELD_LENGTH_OF_STAY)

    if isinstance(adm, str) and isinstance(dis, str):
        d0, d1 = _parse_date(adm), _parse_date(dis)
        if d0 and d1:
            if d0 > d1:
                errors.append(
                    ComplianceIssue(
                        code="DATE_LOGIC_INVALID",
                        severity="error",
                        field=FIELD_DISCHARGE_DATE,
                        message="入院日期应早于出院日期。",
                    )
                )
            expected_days = (d1 - d0).days + 1
            if isinstance(los, str):
                m = LOS_PATTERN.search(los)
                if m:
                    actual = int(m.group(1))
                    if actual != expected_days:
                        errors.append(
                            ComplianceIssue(
                                code="LENGTH_OF_STAY_MISMATCH",
                                severity="error",
                                field=FIELD_LENGTH_OF_STAY,
                                message=(
                                    f"住院天数应为 (出院-入院)+1 = {expected_days}天，"
                                    f"当前为 {actual}天。"
                                ),
                            )
                        )
                else:
                    warnings.append(
                        ComplianceIssue(
                            code="LENGTH_OF_STAY_FORMAT",
                            severity="warning",
                            field=FIELD_LENGTH_OF_STAY,
                            message='住院天数建议使用 "N天" 格式。',
                        )
                    )
            elif los is None:
                warnings.append(
                    ComplianceIssue(
                        code="LENGTH_OF_STAY_MISSING",
                        severity="warning",
                        field=FIELD_LENGTH_OF_STAY,
                        message="已有入出院日期，建议输出住院天数。",
                    )
                )

    return errors, warnings
