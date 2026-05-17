from __future__ import annotations

import time
from pathlib import Path

import yaml

from clinical_note_agent.orchestrator import GenerateRequest, collect_admission_generate, stream_admission_generate

FIXTURES = Path(__file__).parent / "fixtures"


def _d1_request() -> GenerateRequest:
    with (FIXTURES / "d1_generate_request.yaml").open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return GenerateRequest(
        template=data["template"],
        evidence=data["evidence"],
        document_type=data["document_type"],
        department_id=data["department_id"],
    )


def test_event_order():
    events = [e.event for e in stream_admission_generate(_d1_request())]
    assert events[0] == "revision_created"
    assert events[1] == "template_loaded"
    assert "section_patch" in events or "physician_verbatim_patch" in events
    assert events[-2] == "compliance"
    assert events[-1] == "done"


def test_template_loaded_fast():
    req = _d1_request()
    t0 = time.perf_counter()
    first_patch = None
    for ev in stream_admission_generate(req):
        if ev.event == "template_loaded":
            ms = (time.perf_counter() - t0) * 1000
            assert ms < 200, f"template_loaded 应 <200ms，实际 {ms:.1f}ms"
            assert "draft_note" in ev.data
            assert "present_illness" in ev.data["draft_note"]
        if ev.event in ("section_patch", "physician_verbatim_patch") and first_patch is None:
            first_patch = ev
    assert first_patch is not None


def test_d1_auxiliary_and_diagnosis():
    result = collect_admission_generate(_d1_request())
    aux = result.draft_note["auxiliary_exam"]
    assert "12.5" in (aux.get("text") or "")
    assert "骨折" in (aux.get("text") or "")
    assert result.draft_note["physical_exam"]["source_type"] == "physician_verbatim"
    dx = result.draft_note.get("preliminary_diagnosis", {})
    assert "肋骨" in (dx.get("text") or "")
    assert dx.get("source_type") == "physician_verbatim"
    assert len(result.compliance.get("errors", [])) == 0


def test_d2_conflict_via_asr():
    req = _d1_request()
    req.evidence = dict(req.evidence)
    req.evidence["asr_final_text"] = (
        "查体：右侧呼吸音减弱。初步诊断考虑肋骨骨折。白细胞一万二。"
    )
    result = collect_admission_generate(req)
    assert len(result.conflicts) >= 1
    assert result.conflicts[0]["resolution"] == "pending"
    warnings = result.compliance.get("warnings", [])
    assert any(w.get("code") == "CONFLICT_UNRESOLVED" for w in warnings)


def test_sse_format():
    ev = next(stream_admission_generate(_d1_request()))
    sse = ev.to_sse()
    assert sse.startswith("event: revision_created\n")
    assert "data: {" in sse
    assert sse.endswith("\n\n")
