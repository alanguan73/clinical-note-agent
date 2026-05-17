from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from clinical_note_agent.evidence.flags import EvidenceFlags, detect_evidence_flags
from clinical_note_agent.evidence.parser import (
    EXCLUDED_FROM_FACTS,
    ParsedEvidence,
    parse_current_note_kv,
    parse_evidence_input,
)


@dataclass
class EvidenceCorpus:
    """拼接后的证据与元数据。"""

    text: str
    flags: EvidenceFlags
    department: str | None = None
    supplementary_info: str | None = None
    current_note: dict[str, str] = field(default_factory=dict)
    block_types_present: list[str] = field(default_factory=list)
    char_count: int = 0

    @property
    def evidence_flags(self) -> dict[str, bool]:
        return self.flags.to_dict()


def record_types_for_facts() -> frozenset[str]:
    from clinical_note_agent.evidence.parser import EVIDENCE_BLOCK_TYPES

    return EVIDENCE_BLOCK_TYPES - EXCLUDED_FROM_FACTS


def build_evidence_corpus(data: str | dict[str, Any]) -> EvidenceCorpus:
    """
    自动拼接 evidence_corpus（不含 [[附加信息]]）。

    各 fact 块按解析顺序拼接，保留 `[[记录类型]]` 标题行供 LLM/质控对照。
    """
    parsed: ParsedEvidence = parse_evidence_input(data)
    parts: list[str] = []
    current_note: dict[str, str] = {}
    types_present: list[str] = []

    for block in parsed.fact_blocks():
        types_present.append(block.record_type)
        header = f"[[{block.record_type}]]"
        body = block.content.strip()
        if block.is_current_note and body:
            kv = parse_current_note_kv(body)
            if kv:
                current_note = kv
                body_kv = "\n".join(f"{k}::{v}" for k, v in kv.items())
                parts.append(f"{header}\n{body_kv}")
            else:
                parts.append(f"{header}\n{body}")
        else:
            parts.append(f"{header}\n{body}" if body else header)

    text = "\n\n".join(parts).strip()
    flags = detect_evidence_flags(text)

    return EvidenceCorpus(
        text=text,
        flags=flags,
        department=parsed.department,
        supplementary_info=parsed.supplementary_info,
        current_note=current_note,
        block_types_present=types_present,
        char_count=len(text),
    )
