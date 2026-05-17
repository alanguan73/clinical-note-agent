"""证据解析与 evidence_corpus 自动拼接。"""

from clinical_note_agent.evidence.corpus import (
    EvidenceCorpus,
    build_evidence_corpus,
    record_types_for_facts,
)
from clinical_note_agent.evidence.parser import (
    EVIDENCE_BLOCK_TYPES,
    EXCLUDED_FROM_FACTS,
    RecordBlock,
    parse_evidence_input,
)

__all__ = [
    "EvidenceCorpus",
    "build_evidence_corpus",
    "record_types_for_facts",
    "EVIDENCE_BLOCK_TYPES",
    "EXCLUDED_FROM_FACTS",
    "RecordBlock",
    "parse_evidence_input",
]
