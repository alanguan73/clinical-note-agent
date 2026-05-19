from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from clinical_note_agent.evidence.corpus import EvidenceCorpus
from clinical_note_agent.qc.models import ComplianceResult


class PipelineStage(str, Enum):
    EVIDENCE = "evidence"
    WRITING = "writing"
    PROGRAM_QC = "program_qc"
    LLM_QC = "llm_qc"
    FINAL_PROGRAM_QC = "final_program_qc"


@dataclass
class StageRecord:
    stage: PipelineStage
    ok: bool
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    evidence: EvidenceCorpus
    writing_output: dict[str, Any]
    program_compliance: ComplianceResult
    llm_qc_output: dict[str, Any] | None
    final_output: dict[str, Any]
    final_compliance: ComplianceResult
    stages: list[StageRecord] = field(default_factory=list)
    program_qc_passed: bool = True
    llm_qc_skipped: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence": {
                "char_count": self.evidence.char_count,
                "department": self.evidence.department,
                "block_types": self.evidence.block_types_present,
                "evidence_flags": self.evidence.evidence_flags,
            },
            "writing_output": self.writing_output,
            "program_compliance": self.program_compliance.to_dict(),
            "llm_qc_output": self.llm_qc_output,
            "final_output": self.final_output,
            "final_compliance": self.final_compliance.to_dict(),
            "program_qc_passed": self.program_qc_passed,
            "llm_qc_skipped": self.llm_qc_skipped,
            "stages": [
                {"stage": s.stage.value, "ok": s.ok, "detail": s.detail} for s in self.stages
            ],
        }
