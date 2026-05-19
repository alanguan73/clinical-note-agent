from __future__ import annotations

import json
from pathlib import Path

import yaml

from clinical_note_agent.llm.mock import MockLlmClient
from clinical_note_agent.pipeline import run_discharge_pipeline
from clinical_note_agent.pipeline.discharge import DischargePipeline, DischargePipelineConfig

GOLDEN = Path(__file__).parent / "golden"


def _load_case(name: str) -> dict:
    with (GOLDEN / name).open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_pipeline_three_stages_d7():
    """书写(差) → 程序QC(失败) → LLM QC(修正) → 终审通过。"""
    case = _load_case("D-7-minimal-input-anti-hallucination.yaml")
    raw = f"[[当前病历]]\n主诉::头痛、头晕、发热和咽痛的症状"

    bad = case["writing_ai_output_bad"]
    good = case["writing_ai_output_good"]

    llm_qc = MockLlmClient(responses=[MockLlmClient.json_response(good)])

    result = run_discharge_pipeline(
        raw,
        writing_output=bad,
        llm_qc_client=llm_qc,
        config=DischargePipelineConfig(skip_llm_qc=False),
    )

    assert result.evidence.char_count < 80
    assert not result.program_compliance.ok_for_draft
    assert result.llm_qc_output is not None
    assert result.final_output == good
    assert result.final_compliance.ok_for_draft

    stage_names = [s.stage.value for s in result.stages]
    assert stage_names == [
        "evidence",
        "writing",
        "program_qc",
        "llm_qc",
        "final_program_qc",
    ]
    assert len(llm_qc.calls) == 1
    assert "原始输入数据" in llm_qc.calls[0][1].content or "主诉" in llm_qc.calls[0][1].content


def test_pipeline_skip_llm_qc():
    case = _load_case("D-7-minimal-input-anti-hallucination.yaml")
    raw = "[[当前病历]]\n主诉::头痛、头晕、发热和咽痛的症状"
    result = run_discharge_pipeline(
        raw,
        writing_output=case["writing_ai_output_good"],
        config=DischargePipelineConfig(skip_llm_qc=True),
    )
    assert result.llm_qc_skipped
    assert result.final_output == case["writing_ai_output_good"]
    assert "llm_qc" in [s.stage.value for s in result.stages]


def test_pipeline_d8_corpus_in_llm_qc():
    case = _load_case("D-8-rich-input-no-overdelete.yaml")
    raw_input = case["evidence_corpus"]

    good = case["writing_ai_output_good"]
    captured: list[str] = []

    def handler(messages):
        captured.append(messages[1].content)
        return json.dumps(good, ensure_ascii=False)

    pipeline = DischargePipeline(
        writing_client=None,
        llm_qc_client=MockLlmClient(handler=handler),
    )
    # 略差的中间稿
    mid = dict(good)
    mid["诊疗经过"] = mid["诊疗经过"] + " 予补液治疗。"

    result = pipeline.run(raw_input, writing_output=mid)
    assert "7.66" in result.evidence.text
    assert "头孢呋辛" in captured[0]
    assert result.final_compliance.ok_for_draft
