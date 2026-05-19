from __future__ import annotations

import time
from typing import Any, Iterator

from clinical_note_agent.document_types import get_document_type
from clinical_note_agent.orchestrator.admission import (
    _base_payload,
    _emit,
    _section_patch_payload,
)
from clinical_note_agent.orchestrator.dictation import map_dictation_to_sections
from clinical_note_agent.orchestrator.models import GenerateRequest, GenerateState, StreamEvent
from clinical_note_agent.orchestrator.template_engine import build_template_draft_note, resolve_template
from clinical_note_agent.qc import run_compliance


def stream_structured_generate(
    request: GenerateRequest,
    *,
    inter_step_delay_s: float = 0,
) -> Iterator[StreamEvent]:
    """
    流式生成结构化 draft_note 文书：首次病程、上级查房、日常病程等。

    流程：T0 模板 → T2 口述映射 → T6 质控 → done（无检验填充，方案 B）。
    """
    spec = get_document_type(request.document_type)
    if spec.generation_mode != "structured_stream":
        raise ValueError(f"{request.document_type} 不使用 structured 流水线")

    template = resolve_template(request.template, document_type=request.document_type)
    if template.get("document_type") and template["document_type"] != request.document_type:
        raise ValueError("template.document_type 与请求 document_type 不一致")

    state = GenerateState()
    req = request
    t0_start = time.perf_counter()

    yield _emit(
        state,
        "revision_created",
        {**_base_payload(state, req, template), "parent_revision_id": None},
    )

    state.draft_note = build_template_draft_note(template)
    t0_ms = (time.perf_counter() - t0_start) * 1000
    yield _emit(
        state,
        "template_loaded",
        {
            **_base_payload(state, req, template),
            "draft_note": state.draft_note,
            "elapsed_ms": round(t0_ms, 2),
        },
    )
    if inter_step_delay_s:
        time.sleep(inter_step_delay_s)

    asr = request.evidence.get("asr_final_text") or ""
    meta = request.evidence.get("asr_metadata") or {}
    physician = meta.get("speaker") == "physician_only"
    dictation_patches = map_dictation_to_sections(
        asr,
        document_type=request.document_type,
        speaker_physician=physician,
    )

    for section_key, section in dictation_patches.items():
        state.draft_note[section_key] = section
        event_name = (
            "physician_verbatim_patch"
            if section.get("source_type") == "physician_verbatim"
            else "section_patch"
        )
        yield _emit(
            state,
            event_name,
            _section_patch_payload(state, req, template, section_key, section),
        )
        if inter_step_delay_s:
            time.sleep(inter_step_delay_s)

    dept = req.department_id or template.get("department_id")
    compliance = run_compliance(
        state.draft_note,
        document_type=req.document_type,
        department_id=dept,
        template=template,
        conflicts=state.conflicts,
    )
    yield _emit(
        state,
        "compliance",
        {
            **_base_payload(state, req, template),
            "compliance": compliance.to_dict(),
            "rulepack_version": compliance.rulepack_version,
        },
    )

    provenance = {
        "architecture": "B",
        "document_type": req.document_type,
        "document_label": spec.label_zh,
        "ai_call_budget": {"max": 1, "used": len(state.ai_calls)},
        "ai_calls": state.ai_calls,
        "template_version": template.get("template_version"),
        "rulepack_version": compliance.rulepack_version,
    }
    yield _emit(
        state,
        "done",
        {
            **_base_payload(state, req, template),
            "draft_note": state.draft_note,
            "conflicts": state.conflicts,
            "compliance": compliance.to_dict(),
            "provenance": provenance,
            "note_status": "draft",
        },
    )
