from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from clinical_note_agent.evidence import build_evidence_corpus
from clinical_note_agent.llm.mock import MockLlmClient
from clinical_note_agent.llm.openai_compatible import OpenAICompatibleClient
from clinical_note_agent.pipeline.discharge import DischargePipeline, DischargePipelineConfig
def _load_input(path: Path) -> str | dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".json",):
        return json.loads(text)
    return text


def _load_json_optional(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="出院记录流水线：evidence_corpus → 书写 → 程序 QC → LLM QC"
    )
    parser.add_argument("input", type=Path, help="证据输入（.txt 含 [[记录类型]] 或 .json）")
    parser.add_argument(
        "--writing-output",
        type=Path,
        help="跳过书写 LLM，直接使用已有出院记录 JSON",
    )
    parser.add_argument(
        "--corpus-only",
        action="store_true",
        help="仅拼接 evidence_corpus 并输出元数据",
    )
    parser.add_argument("--skip-llm-qc", action="store_true")
    parser.add_argument("--department", type=str, default=None)
    parser.add_argument(
        "--provider",
        choices=["mock", "openai"],
        default="mock",
        help="LLM 提供商（默认 mock，需 OPENAI_API_KEY 时用 openai）",
    )
    parser.add_argument("-o", "--output", type=Path, help="结果写入 JSON 文件")
    args = parser.parse_args(argv)

    raw = _load_input(args.input)

    if args.corpus_only:
        corpus = build_evidence_corpus(raw)
        out = {
            "evidence_corpus": corpus.text,
            "char_count": corpus.char_count,
            "department": corpus.department,
            "evidence_flags": corpus.evidence_flags,
            "block_types": corpus.block_types_present,
            "current_note": corpus.current_note,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    prewritten = _load_json_optional(args.writing_output)
    config = DischargePipelineConfig(
        department_id=args.department,
        skip_llm_qc=args.skip_llm_qc,
    )

    if args.provider == "openai":
        client = OpenAICompatibleClient()
        pipeline = DischargePipeline(
            writing_client=client,
            llm_qc_client=client,
            config=config,
        )
    else:
        if prewritten is None:
            print("mock 模式需 --writing-output 或改用 --provider openai", file=sys.stderr)
            return 2
        pipeline = DischargePipeline(
            writing_client=None,
            llm_qc_client=MockLlmClient(responses=[json.dumps(prewritten, ensure_ascii=False)]),
            config=config,
        )

    result = pipeline.run(raw, writing_output=prewritten)
    payload = result.to_dict()
    payload["final_output"] = result.final_output
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text)

    if not result.final_compliance.ok_for_draft:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
