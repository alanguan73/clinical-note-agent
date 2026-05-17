from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from clinical_note_agent.evidence.corpus import EvidenceCorpus
from clinical_note_agent.llm.client import LlmClient, LlmMessage
from clinical_note_agent.pipeline.json_utils import extract_json_object
from clinical_note_agent.qc.models import ComplianceResult

_PKG_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_QC_PROMPT = _PKG_ROOT / "prompts" / "discharge_llm_qc_system.md"


def load_qc_prompt(path: Path | None) -> str:
    p = path or _DEFAULT_QC_PROMPT
    return p.read_text(encoding="utf-8")


def run_llm_qc_stage(
    evidence: EvidenceCorpus,
    writing_output: dict[str, Any],
    *,
    client: LlmClient,
    system_prompt: str,
    program_compliance: ComplianceResult | None = None,
) -> dict[str, Any]:
    """LLM 质控：对照 evidence_corpus 修正书写输出。"""
    user_payload = {
        "原始输入数据": evidence.text,
        "出院记录生成结果": writing_output,
    }
    if program_compliance and (program_compliance.errors or program_compliance.warnings):
        user_payload["程序质控提示"] = {
            "errors": [e.to_dict() for e in program_compliance.errors],
            "warnings": [w.to_dict() for w in program_compliance.warnings],
        }

    raw = client.complete(
        [
            LlmMessage(role="system", content=system_prompt),
            LlmMessage(
                role="user",
                content=json.dumps(user_payload, ensure_ascii=False, indent=2),
            ),
        ],
        temperature=0,
        response_format_json=True,
    )
    return extract_json_object(raw)
