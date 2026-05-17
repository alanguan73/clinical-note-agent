"""Clinical note agent — 病历辅助生成（方案 B）。"""

from clinical_note_agent.evidence import build_evidence_corpus
from clinical_note_agent.orchestrator import (
    GenerateRequest,
    collect_admission_generate,
    stream_admission_generate,
)
from clinical_note_agent.pipeline import run_discharge_pipeline

__version__ = "0.4.0"

__all__ = [
    "build_evidence_corpus",
    "run_discharge_pipeline",
    "GenerateRequest",
    "stream_admission_generate",
    "collect_admission_generate",
    "__version__",
]
