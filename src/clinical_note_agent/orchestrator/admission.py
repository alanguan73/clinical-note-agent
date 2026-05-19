from __future__ import annotations

import time
from typing import Any, Iterator

from clinical_note_agent.orchestrator.dictation import map_dictation_to_sections
from clinical_note_agent.orchestrator.fill_structured import (
    apply_conflict_to_auxiliary,
    detect_wbc_conflict,
    fill_labs_imaging,
)
from clinical_note_agent.orchestrator.models import GenerateRequest, GenerateResult, GenerateState, StreamEvent
from clinical_note_agent.orchestrator.template_engine import build_template_draft_note, resolve_template
from clinical_note_agent.qc import run_compliance


def _base_payload(state: GenerateState, req: GenerateRequest, template: dict[str, Any]) -> dict[str, Any]:
    return {
        "revision_id": state.revision_id,
        "note_id": req.note_id,
        "session_id": req.session_id,
        "template_id": template.get("template_id"),
        "template_version": template.get("template_version"),
        "document_type": req.document_type,
        "department_id": req.department_id or template.get("department_id"),
    }


def _emit(state: GenerateState, event: str, payload: dict[str, Any]) -> StreamEvent:
    payload["seq"] = state.next_seq()
    return StreamEvent(event=event, data=payload, seq=payload["seq"])


def _section_patch_payload(
    state: GenerateState,
    req: GenerateRequest,
    template: dict[str, Any],
    section_key: str,
    section: dict[str, Any],
    *,
    op: str = "replace",
) -> dict[str, Any]:
    body = _base_payload(state, req, template)
    body.update(
        {
            "section_key": section_key,
            "op": op,
            "text": section.get("text"),
            "source_refs": section.get("source_refs", []),
            "source_type": section.get("source_type"),
            "section_status": section.get("section_status", "ok"),
        }
    )
    if section.get("display_mode"):
        body["display_mode"] = section["display_mode"]
    if section.get("candidates"):
        body["candidates"] = section["candidates"]
    return body


def stream_admission_generate(
    request: GenerateRequest,
    *,
    inter_step_delay_s: float = 0,
) -> Iterator[StreamEvent]:
    """
    流式生成入院记录：T0 template_loaded → T1–T4 patch → compliance → done。

    inter_step_delay_s：便于演示/测试 SSE 先后顺序（生产设为 0）。
    """
    req = request
    template = resolve_template(request.template, document_type=req.document_type)
    state = GenerateState()
    t0_start = time.perf_counter()

    yield _emit(
        state,
        "revision_created",
        {**_base_payload(state, req, template), "parent_revision_id": None},
    )

    # --- T0 模板先显 ---
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

    tid = template.get("template_id", "unknown")
    evidence = request.evidence

    # --- T1 检验/影像 ---
    aux = fill_labs_imaging(state.draft_note, evidence, template_id=tid)
    if aux:
        conflict = detect_wbc_conflict(evidence)
        if conflict:
            state.conflicts.append(conflict)
            aux = apply_conflict_to_auxiliary(aux, conflict)
        state.draft_note["auxiliary_exam"] = aux
        yield _emit(
            state,
            "section_patch",
            _section_patch_payload(state, req, template, "auxiliary_exam", aux),
        )
        if inter_step_delay_s:
            time.sleep(inter_step_delay_s)

    # --- T2 口述映射 ---
    asr = evidence.get("asr_final_text") or ""
    meta = evidence.get("asr_metadata") or {}
    physician = meta.get("speaker") == "physician_only"
    dictation_patches = map_dictation_to_sections(
        asr,
        document_type=req.document_type,
        speaker_physician=physician,
    )

    for section_key, section in dictation_patches.items():
        state.draft_note[section_key] = section
        if section.get("source_type") == "physician_verbatim":
            yield _emit(
                state,
                "physician_verbatim_patch",
                _section_patch_payload(state, req, template, section_key, section),
            )
        else:
            yield _emit(
                state,
                "section_patch",
                _section_patch_payload(state, req, template, section_key, section),
            )
        if inter_step_delay_s:
            time.sleep(inter_step_delay_s)

    # --- T3 占位符保留（模板默认句仍在）；无额外 LLM 时跳过 T4 ---
    # --- T6 质控 ---
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

    # --- done ---
    provenance = {
        "architecture": "B",
        "ai_call_budget": {"max": 2, "used": len(state.ai_calls)},
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


def collect_admission_generate(
    request: GenerateRequest,
    **kwargs: Any,
) -> GenerateResult:
    """非流式：收集全部事件并返回最终结果。"""
    events = list(stream_admission_generate(request, **kwargs))
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
