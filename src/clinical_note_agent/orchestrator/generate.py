from __future__ import annotations

from typing import Any, Iterator

from clinical_note_agent.document_types import (
    DISCHARGE_SUMMARY,
    INPATIENT_ADMISSION,
    get_document_type,
)
from clinical_note_agent.orchestrator.admission import stream_admission_generate
from clinical_note_agent.orchestrator.models import GenerateRequest, GenerateResult, StreamEvent
from clinical_note_agent.orchestrator.structured import stream_structured_generate


def stream_note_generate(
    request: GenerateRequest,
    *,
    inter_step_delay_s: float = 0,
) -> Iterator[StreamEvent]:
    """
    按 document_type 分发流式生成（五种病历入口）。

    - inpatient_admission → 入院编排（含 T1 检验填充）
    - first_progress_note / senior_round_note / daily_progress_note → 结构化病程
    - discharge_summary → 请使用 run_discharge_pipeline() 或 note-pipeline
    """
    spec = get_document_type(request.document_type)

    if spec.document_type == DISCHARGE_SUMMARY.document_type:
        raise ValueError(
            "出院记录请使用 run_discharge_pipeline() 或 CLI note-pipeline；"
            "本 SSE 接口仅支持 structured draft_note 四类文书"
        )

    if spec.document_type == INPATIENT_ADMISSION.document_type:
        yield from stream_admission_generate(request, inter_step_delay_s=inter_step_delay_s)
        return

    yield from stream_structured_generate(request, inter_step_delay_s=inter_step_delay_s)


def collect_note_generate(
    request: GenerateRequest,
    **kwargs: Any,
) -> GenerateResult:
    """非流式：收集全部事件并返回最终结果。"""
    events = list(stream_note_generate(request, **kwargs))
    done = next(e for e in reversed(events) if e.event == "done")
    compliance_event = next(e for e in events if e.event == "compliance")
    return GenerateResult(
        events=events,
        draft_note=done.data["draft_note"],
        conflicts=done.data.get("conflicts", []),
        compliance=compliance_event.data["compliance"],
        provenance=done.data.get("provenance", {}),
        note_id=done.data["note_id"],
        revision_id=done.data["revision_id"],
    )
