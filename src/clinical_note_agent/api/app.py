from __future__ import annotations

from typing import Any

from clinical_note_agent.orchestrator import GenerateRequest, stream_admission_generate

try:
    from fastapi import FastAPI
    from fastapi.responses import StreamingResponse
except ImportError as e:  # pragma: no cover
    raise ImportError("请安装 API 依赖：pip install 'clinical-note-agent[api]'") from e

app = FastAPI(title="Clinical Note Agent", version="0.4.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/notes/generate")
def generate_note(body: dict[str, Any]) -> StreamingResponse:
    """流式生成：SSE（方案 B）。"""
    req = GenerateRequest(
        template=body["template"],
        evidence=body["evidence"],
        document_type=body.get("document_type", "inpatient_admission"),
        department_id=body.get("department_id"),
        note_id=body.get("note_id"),
        session_id=body.get("session_id"),
        options=body.get("options", {}),
    )

    def event_stream():
        for event in stream_admission_generate(req):
            yield event.to_sse()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
