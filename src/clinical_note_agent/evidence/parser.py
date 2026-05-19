from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# 与现行出院记录提示词一致的记录块类型
EVIDENCE_BLOCK_TYPES = frozenset(
    {
        "科室类别",
        "门诊初诊病历",
        "入院记录",
        "首次病程记录",
        "日常病程记录",
        "上级医师查房记录",
        "出院记录",
        "检验报告",
        "录音记录",
        "图像记录",
        "当前病历",
        "附加信息",
    }
)

# 不作为事实依据（不进入 evidence_corpus）
EXCLUDED_FROM_FACTS = frozenset({"附加信息"})

_BLOCK_HEADER_RE = re.compile(r"^\[\[([^\]]+)\]\]\s*$", re.MULTILINE)
_CURRENT_NOTE_KV_RE = re.compile(r"^([^:\n]+)::(.+)$", re.MULTILINE)


@dataclass
class RecordBlock:
    record_type: str
    content: str
    excluded_from_facts: bool = False

    @property
    def is_current_note(self) -> bool:
        return self.record_type == "当前病历"


@dataclass
class ParsedEvidence:
    blocks: list[RecordBlock] = field(default_factory=list)
    department: str | None = None
    supplementary_info: str | None = None  # [[附加信息]]，仅参考

    def fact_blocks(self) -> list[RecordBlock]:
        return [b for b in self.blocks if not b.excluded_from_facts]


def parse_evidence_input(data: str | dict[str, Any]) -> ParsedEvidence:
    """
    解析证据输入。

    - str：含 `[[记录类型]]` 标记的整段文本（购物车模式原始输入）
    - dict：`{ "raw_text": "..." }` 或 `{ "blocks": [{"type","content"}, ...] }`
    """
    if isinstance(data, str):
        return _parse_raw_text(data)
    if isinstance(data, dict):
        if "raw_text" in data and data["raw_text"]:
            parsed = _parse_raw_text(str(data["raw_text"]))
            _merge_blocks_dict(parsed, data.get("blocks"))
            return parsed
        if data.get("blocks"):
            return _parse_blocks_list(data["blocks"])
        raise ValueError("dict 输入需包含 raw_text 或 blocks")
    raise TypeError(f"不支持的证据输入类型: {type(data)}")


def _parse_blocks_list(blocks: list[dict[str, Any]]) -> ParsedEvidence:
    parsed = ParsedEvidence()
    for item in blocks:
        rtype = str(item.get("type") or item.get("record_type", "")).strip()
        content = str(item.get("content", "")).strip()
        excluded = rtype in EXCLUDED_FROM_FACTS
        parsed.blocks.append(
            RecordBlock(record_type=rtype, content=content, excluded_from_facts=excluded)
        )
        if rtype == "科室类别" and content:
            parsed.department = content.splitlines()[0].strip()
        if rtype == "附加信息":
            parsed.supplementary_info = content
    return parsed


def _merge_blocks_dict(parsed: ParsedEvidence, blocks: Any) -> None:
    if not blocks:
        return
    extra = _parse_blocks_list(blocks)
    existing_types = {b.record_type for b in parsed.blocks}
    for b in extra.blocks:
        if b.record_type not in existing_types:
            parsed.blocks.append(b)


def _parse_raw_text(text: str) -> ParsedEvidence:
    parsed = ParsedEvidence()
    matches = list(_BLOCK_HEADER_RE.finditer(text))
    if not matches:
        # 无块标记：整体视为当前病历或单段证据
        parsed.blocks.append(RecordBlock(record_type="当前病历", content=text.strip()))
        return parsed

    for i, match in enumerate(matches):
        rtype = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        excluded = rtype in EXCLUDED_FROM_FACTS
        parsed.blocks.append(
            RecordBlock(record_type=rtype, content=content, excluded_from_facts=excluded)
        )
        if rtype == "科室类别" and content:
            parsed.department = content.splitlines()[0].strip()
        if rtype == "附加信息":
            parsed.supplementary_info = content

    return parsed


def parse_current_note_kv(content: str) -> dict[str, str]:
    """解析 [[当前病历]] 内 keyname::value 行。"""
    result: dict[str, str] = {}
    for m in _CURRENT_NOTE_KV_RE.finditer(content):
        key = m.group(1).strip()
        val = m.group(2).strip()
        if key:
            result[key] = val
    return result
