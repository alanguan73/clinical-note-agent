from __future__ import annotations

import re
from typing import Any

from clinical_note_agent.qc.models import ComplianceIssue

# 出院记录字段（中文 key）
_CLINICAL_FIELDS = (
    "入院情况",
    "入院诊断",
    "诊疗经过",
    "出院情况",
    "出院诊断",
    "出院医嘱",
)

# 提取可能需溯源的片段：数值、常见药名片段（可扩展词表）
_NUMERIC_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:×10\^?\d+|mmol/L|mg/L|mmHg|℃|次/分|mg|g|ml|U/L|%|/L)?",
    re.I,
)
_DX_LINE_RE = re.compile(r"^\s*\d+[\.\、]\s*(.+)$", re.M)


def _normalize_corpus(corpus: str) -> str:
    return re.sub(r"\s+", "", corpus.lower())


def _in_corpus(fragment: str, corpus_norm: str) -> bool:
    frag = re.sub(r"\s+", "", fragment.lower())
    if len(frag) < 2:
        return True
    return frag in corpus_norm


def validate_evidence_grounding(
    output: dict[str, Any],
    evidence_corpus: str,
    *,
    check_numerics: bool = True,
    check_diagnosis_lines: bool = True,
) -> list[ComplianceIssue]:
    """
    对照「全部原始数据」做可程序化的反幻觉检查（质控提示词 P1–P3 的子集）。

    说明：无法替代 LLM 质控的句级语义判断；用于 CI 与高置信规则（数值、诊断行）。
    """
    issues: list[ComplianceIssue] = []
    if not evidence_corpus.strip():
        return issues

    corpus_norm = _normalize_corpus(evidence_corpus)

    for field in _CLINICAL_FIELDS:
        text = output.get(field)
        if not text or not isinstance(text, str) or not text.strip():
            continue

        if check_diagnosis_lines and field in ("入院诊断", "出院诊断"):
            for m in _DX_LINE_RE.finditer(text):
                dx = m.group(1).strip()
                if len(dx) >= 2 and not _in_corpus(dx[: min(len(dx), 20)], corpus_norm):
                    # 诊断名至少部分出现在证据中
                    if not _in_corpus(dx, corpus_norm):
                        issues.append(
                            ComplianceIssue(
                                code="UNGROUNDED_CLAIM",
                                severity="error",
                                field=field,
                                message=f"诊断「{dx}」在全部原始数据中未找到依据。",
                            )
                        )

        if check_numerics:
            for m in _NUMERIC_RE.finditer(text):
                num = m.group(0).strip()
                # 过滤极短数字（如列表序号）
                if len(re.sub(r"\D", "", num)) < 2:
                    continue
                if not _in_corpus(num, corpus_norm):
                    issues.append(
                        ComplianceIssue(
                            code="UNGROUNDED_NUMERIC",
                            severity="error",
                            field=field,
                            message=f"数值「{num}」在全部原始数据中未找到来源。",
                        )
                    )

    return issues


def validate_sparse_input_guard(
    output: dict[str, Any],
    evidence_corpus: str,
    *,
    max_fields_without_rich_evidence: int = 3,
    minimal_corpus_chars: int = 80,
) -> list[ComplianceIssue]:
    """
    铁律1：输入极少时不得输出完整出院记录（金样例 D-7）。

    仅当证据总长 < minimal_corpus_chars（如仅一句主诉）且输出字段过多时触发。
    """
    issues: list[ComplianceIssue] = []
    corpus_len = len(evidence_corpus.strip())
    present_fields = [k for k in _CLINICAL_FIELDS if output.get(k)]

    if corpus_len < minimal_corpus_chars and len(present_fields) > max_fields_without_rich_evidence:
        issues.append(
            ComplianceIssue(
                code="SPARSE_INPUT_EXCESS_OUTPUT",
                severity="error",
                field="*",
                message=(
                    f"原始输入极少（约 {corpus_len} 字），却输出了 {len(present_fields)} 个临床字段，"
                    "疑似幻觉性扩写，应仅保留有依据字段。"
                ),
            )
        )
    return issues
