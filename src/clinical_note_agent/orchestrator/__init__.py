"""入院记录流式编排（方案 B）：先显模板 + 增量 patch。"""

from clinical_note_agent.document_types import list_document_types
from clinical_note_agent.orchestrator.admission import (
    collect_admission_generate,
    stream_admission_generate,
)
from clinical_note_agent.orchestrator.generate import collect_note_generate, stream_note_generate
from clinical_note_agent.orchestrator.models import GenerateRequest, GenerateResult, StreamEvent
from clinical_note_agent.orchestrator.structured import stream_structured_generate

__all__ = [
    "GenerateRequest",
    "GenerateResult",
    "StreamEvent",
    "stream_admission_generate",
    "collect_admission_generate",
    "stream_note_generate",
    "collect_note_generate",
    "stream_structured_generate",
    "list_document_types",
]
