from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from clinical_note_agent.evidence.corpus import EvidenceCorpus
from clinical_note_agent.llm.client import LlmClient, LlmMessage
from clinical_note_agent.pipeline.json_utils import extract_json_object

_PKG_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_WRITING_PROMPT = _PKG_ROOT / "prompts" / "discharge_writing_system.md"


def load_prompt(path: Path | None) -> str:
    p = path or _DEFAULT_WRITING_PROMPT
    if not p.exists():
        return (
            "你是主治医师，根据提供的医疗记录生成出院记录 JSON。"
            "无依据不编造；输入少则只输出有依据的字段；只输出 JSON。"
        )
    return p.read_text(encoding="utf-8")


def run_writing_stage(
    evidence: EvidenceCorpus,
    *,
    client: LlmClient | None,
    system_prompt: str,
    supplementary_note: str | None = None,
    prewritten_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    书写阶段：有 prewritten 则直通；否则调用 LLM。
    """
    if prewritten_output is not None:
        return dict(prewritten_output)

    if client is None:
        raise ValueError("未提供 writing_output 且未配置 writing LLM client")

    user_parts = [
        "## 原始医疗记录（事实依据）\n",
        evidence.text,
    ]
    if supplementary_note:
        user_parts.append("\n\n## 附加信息（仅参考，不作事实依据）\n")
        user_parts.append(supplementary_note)

    user_parts.append("\n\n请生成出院记录 JSON。")

    raw = client.complete(
        [
            LlmMessage(role="system", content=system_prompt),
            LlmMessage(role="user", content="".join(user_parts)),
        ],
        temperature=0,
        response_format_json=True,
    )
    return extract_json_object(raw)


def format_writing_input_preview(evidence: EvidenceCorpus) -> str:
    return json.dumps(
        {"evidence_corpus_preview": evidence.text[:500], "char_count": evidence.char_count},
        ensure_ascii=False,
    )
