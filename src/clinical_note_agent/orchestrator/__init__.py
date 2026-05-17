"""入院记录流式编排（方案 B）：先显模板 + 增量 patch。"""

from clinical_note_agent.orchestrator.admission import (
    collect_admission_generate,
    stream_admission_generate,
)
from clinical_note_agent.orchestrator.models import GenerateRequest, GenerateResult, StreamEvent

__all__ = [
    "GenerateRequest",
    "GenerateResult",
    "StreamEvent",
    "stream_admission_generate",
    "collect_admission_generate",
]
