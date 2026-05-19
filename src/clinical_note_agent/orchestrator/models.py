from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class GenerateRequest:
    """POST /v1/notes/generate 契约（简化）。"""

    template: dict[str, Any]
    evidence: dict[str, Any]
    document_type: str = "inpatient_admission"
    department_id: str | None = None
    note_id: str | None = None
    session_id: str | None = None
    options: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.note_id = self.note_id or str(uuid.uuid4())
        self.session_id = self.session_id or str(uuid.uuid4())
        self.options = self.options or {}


@dataclass
class StreamEvent:
    """SSE 事件（event 名 + data JSON 体）。"""

    event: str
    data: dict[str, Any]
    seq: int

    def to_sse(self) -> str:
        import json

        payload = json.dumps(self.data, ensure_ascii=False)
        return f"event: {self.event}\ndata: {payload}\n\n"


@dataclass
class GenerateState:
    """流水线可变状态。"""

    revision_id: str = field(default_factory=lambda: f"rev_{uuid.uuid4().hex[:12]}")
    seq: int = 0
    draft_note: dict[str, Any] = field(default_factory=dict)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)
    ai_calls: list[dict[str, Any]] = field(default_factory=list)

    def next_seq(self) -> int:
        self.seq += 1
        return self.seq


@dataclass
class GenerateResult:
    events: list[StreamEvent]
    draft_note: dict[str, Any]
    conflicts: list[dict[str, Any]]
    compliance: dict[str, Any]
    provenance: dict[str, Any]
    note_id: str
    revision_id: str


def iter_events(events: Iterator[StreamEvent]) -> list[StreamEvent]:
    return list(events)
