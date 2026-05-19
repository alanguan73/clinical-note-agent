from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from clinical_note_agent.document_types import list_document_types
from clinical_note_agent.orchestrator import GenerateRequest, stream_note_generate


def _load_request(path: Path) -> GenerateRequest:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if "input" in data:
        data = data["input"]
    return GenerateRequest(
        template=data["template"],
        evidence=data["evidence"],
        document_type=data.get("document_type", "inpatient_admission"),
        department_id=data.get("department_id"),
        note_id=data.get("note_id"),
        options=data.get("options", {}),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="病历流式生成 SSE（入院/首次病程/查房/日常病程；出院请用 note-pipeline）",
    )
    parser.add_argument(
        "--list-types",
        action="store_true",
        help="列出支持的 document_type",
    )
    parser.add_argument(
        "request",
        type=Path,
        nargs="?",
        help="生成请求 JSON/YAML（含 template + evidence）",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0,
        help="阶段间隔秒数（演示用）",
    )
    parser.add_argument(
        "--json-events",
        action="store_true",
        help="输出 JSON Lines 而非 SSE",
    )
    args = parser.parse_args(argv)

    if args.list_types:
        for spec in list_document_types():
            print(f"{spec.document_type}\t{spec.label_zh}\t{spec.generation_mode}")
        return 0

    if not args.request:
        parser.error("请提供 request 文件，或使用 --list-types")

    req = _load_request(args.request)
    for event in stream_note_generate(req, inter_step_delay_s=args.delay):
        if args.json_events:
            print(json.dumps({"event": event.event, **event.data}, ensure_ascii=False))
        else:
            sys.stdout.write(event.to_sse())
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
