from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

GenerationMode = Literal["structured_stream", "discharge_pipeline"]


@dataclass(frozen=True)
class DocumentTypeSpec:
    """文书类型元数据（五种病历的统一注册表）。"""

    document_type: str
    label_zh: str
    template_subdir: str
    section_keys: frozenset[str]
    generation_mode: GenerationMode
    evidence_block_label: str | None = None


# 附录 B / 27.4 + 出院 + 三种病程
INPATIENT_ADMISSION = DocumentTypeSpec(
    document_type="inpatient_admission",
    label_zh="入院记录",
    template_subdir="inpatient",
    section_keys=frozenset(
        {
            "chief_complaint",
            "present_illness",
            "past_history",
            "personal_history",
            "marital_reproductive_history",
            "family_history",
            "physical_exam",
            "specialist_exam",
            "auxiliary_exam",
            "preliminary_diagnosis",
            "treatment_plan",
        }
    ),
    generation_mode="structured_stream",
    evidence_block_label="入院记录",
)

DISCHARGE_SUMMARY = DocumentTypeSpec(
    document_type="discharge_summary",
    label_zh="出院记录",
    template_subdir="discharge",
    section_keys=frozenset(
        {
            "admission_date",
            "discharge_date",
            "length_of_stay",
            "admission_status",
            "admission_diagnosis",
            "course_summary",
            "discharge_status",
            "discharge_diagnosis",
            "discharge_orders",
        }
    ),
    generation_mode="discharge_pipeline",
    evidence_block_label="出院记录",
)

FIRST_PROGRESS_NOTE = DocumentTypeSpec(
    document_type="first_progress_note",
    label_zh="首次病程记录",
    template_subdir="progress",
    section_keys=frozenset(
        {
            "course_summary",
            "diagnosis_discussion",
            "treatment_plan",
        }
    ),
    generation_mode="structured_stream",
    evidence_block_label="首次病程记录",
)

SENIOR_ROUND_NOTE = DocumentTypeSpec(
    document_type="senior_round_note",
    label_zh="上级医师查房记录",
    template_subdir="progress",
    section_keys=frozenset(
        {
            "round_record",
            "round_opinion",
            "treatment_plan",
        }
    ),
    generation_mode="structured_stream",
    evidence_block_label="上级医师查房记录",
)

DAILY_PROGRESS_NOTE = DocumentTypeSpec(
    document_type="daily_progress_note",
    label_zh="日常病程记录",
    template_subdir="progress",
    section_keys=frozenset(
        {
            "daily_course",
            "observation_treatment",
        }
    ),
    generation_mode="structured_stream",
    evidence_block_label="日常病程记录",
)

DOCUMENT_TYPES: dict[str, DocumentTypeSpec] = {
    INPATIENT_ADMISSION.document_type: INPATIENT_ADMISSION,
    DISCHARGE_SUMMARY.document_type: DISCHARGE_SUMMARY,
    FIRST_PROGRESS_NOTE.document_type: FIRST_PROGRESS_NOTE,
    SENIOR_ROUND_NOTE.document_type: SENIOR_ROUND_NOTE,
    DAILY_PROGRESS_NOTE.document_type: DAILY_PROGRESS_NOTE,
}

STRUCTURED_STREAM_TYPES = frozenset(
    t.document_type
    for t in DOCUMENT_TYPES.values()
    if t.generation_mode == "structured_stream"
)

SCHEMA_VALIDATED_TYPES = STRUCTURED_STREAM_TYPES


def get_document_type(document_type: str) -> DocumentTypeSpec:
    spec = DOCUMENT_TYPES.get(document_type)
    if spec is None:
        known = ", ".join(sorted(DOCUMENT_TYPES))
        raise ValueError(f"不支持的 document_type: {document_type!r}，可选: {known}")
    return spec


def list_document_types() -> list[DocumentTypeSpec]:
    return list(DOCUMENT_TYPES.values())
