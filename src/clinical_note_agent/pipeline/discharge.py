from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from clinical_note_agent.evidence.corpus import EvidenceCorpus, build_evidence_corpus
from clinical_note_agent.llm.client import LlmClient
from clinical_note_agent.pipeline.llm_qc import load_qc_prompt, run_llm_qc_stage
from clinical_note_agent.pipeline.models import PipelineResult, PipelineStage, StageRecord
from clinical_note_agent.pipeline.writing import load_prompt, run_writing_stage
from clinical_note_agent.qc.discharge_engine import run_discharge_compliance
from clinical_note_agent.qc.models import ComplianceResult


@dataclass
class DischargePipelineConfig:
    """出院记录三线流水线配置。"""

    department_id: str | None = None
    skip_llm_qc: bool = False
    skip_final_program_qc: bool = False
    block_publish_on_program_errors: bool = False
    writing_system_prompt_path: Path | None = None
    llm_qc_system_prompt_path: Path | None = None


class DischargePipeline:
    """
    书写 → 程序 QC → LLM QC →（可选）终审程序 QC
    """

    def __init__(
        self,
        *,
        writing_client: LlmClient | None = None,
        llm_qc_client: LlmClient | None = None,
        config: DischargePipelineConfig | None = None,
    ) -> None:
        self.writing_client = writing_client
        self.llm_qc_client = llm_qc_client
        self.config = config or DischargePipelineConfig()

    def run(
        self,
        evidence_input: str | dict[str, Any],
        *,
        writing_output: dict[str, Any] | None = None,
    ) -> PipelineResult:
        stages: list[StageRecord] = []
        cfg = self.config

        # --- 0. evidence_corpus ---
        evidence: EvidenceCorpus = build_evidence_corpus(evidence_input)
        if cfg.department_id and not evidence.department:
            evidence.department = cfg.department_id
        stages.append(
            StageRecord(
                stage=PipelineStage.EVIDENCE,
                ok=True,
                detail={
                    "char_count": evidence.char_count,
                    "block_types": evidence.block_types_present,
                    "evidence_flags": evidence.evidence_flags,
                },
            )
        )

        writing_prompt = load_prompt(cfg.writing_system_prompt_path)
        qc_prompt = load_qc_prompt(cfg.llm_qc_system_prompt_path)

        # --- 1. 书写 ---
        draft = run_writing_stage(
            evidence,
            client=self.writing_client,
            system_prompt=writing_prompt,
            supplementary_note=evidence.supplementary_info,
            prewritten_output=writing_output,
        )
        stages.append(
            StageRecord(
                stage=PipelineStage.WRITING,
                ok=True,
                detail={"fields": list(draft.keys()), "prewritten": writing_output is not None},
            )
        )

        dept = cfg.department_id or evidence.department

        # --- 2. 程序 QC ---
        program_compliance: ComplianceResult = run_discharge_compliance(
            draft,
            evidence_corpus=evidence.text,
            department_id=dept,
            evidence_flags=evidence.evidence_flags,
        )
        program_ok = program_compliance.ok_for_draft
        stages.append(
            StageRecord(
                stage=PipelineStage.PROGRAM_QC,
                ok=program_ok,
                detail={
                    "errors": len(program_compliance.errors),
                    "warnings": len(program_compliance.warnings),
                    "rulepack_version": program_compliance.rulepack_version,
                },
            )
        )

        final_output = dict(draft)
        llm_qc_output: dict[str, Any] | None = None
        llm_qc_skipped = cfg.skip_llm_qc

        # --- 3. LLM QC ---
        if not cfg.skip_llm_qc:
            if self.llm_qc_client is None:
                raise ValueError("未配置 llm_qc_client，且 skip_llm_qc=False")
            llm_qc_output = run_llm_qc_stage(
                evidence,
                draft,
                client=self.llm_qc_client,
                system_prompt=qc_prompt,
                program_compliance=program_compliance,
            )
            final_output = llm_qc_output
            stages.append(
                StageRecord(
                    stage=PipelineStage.LLM_QC,
                    ok=True,
                    detail={"fields": list(final_output.keys())},
                )
            )
        else:
            stages.append(
                StageRecord(
                    stage=PipelineStage.LLM_QC,
                    ok=True,
                    detail={"skipped": True},
                )
            )

        # --- 4. 终审程序 QC ---
        if cfg.skip_final_program_qc:
            final_compliance = program_compliance
        else:
            final_compliance = run_discharge_compliance(
                final_output,
                evidence_corpus=evidence.text,
                department_id=dept,
                evidence_flags=evidence.evidence_flags,
            )
            stages.append(
                StageRecord(
                    stage=PipelineStage.FINAL_PROGRAM_QC,
                    ok=final_compliance.ok_for_draft,
                    detail={
                        "errors": len(final_compliance.errors),
                        "warnings": len(final_compliance.warnings),
                    },
                )
            )

        return PipelineResult(
            evidence=evidence,
            writing_output=draft,
            program_compliance=program_compliance,
            llm_qc_output=llm_qc_output,
            final_output=final_output,
            final_compliance=final_compliance,
            stages=stages,
            program_qc_passed=program_ok,
            llm_qc_skipped=llm_qc_skipped,
        )


def run_discharge_pipeline(
    evidence_input: str | dict[str, Any],
    *,
    writing_client: LlmClient | None = None,
    llm_qc_client: LlmClient | None = None,
    writing_output: dict[str, Any] | None = None,
    config: DischargePipelineConfig | None = None,
) -> PipelineResult:
    """便捷入口。"""
    return DischargePipeline(
        writing_client=writing_client,
        llm_qc_client=llm_qc_client,
        config=config,
    ).run(evidence_input, writing_output=writing_output)
