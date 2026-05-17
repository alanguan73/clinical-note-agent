from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from clinical_note_agent.qc import run_compliance


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="病历草稿输出前质控（T6 rules.validate）")
    parser.add_argument(
        "note",
        type=Path,
        help="JSON 文件：含 draft_note、document_type、department_id、template、conflicts 等",
    )
    parser.add_argument("--fail-on-warnings", action="store_true", help="warnings 非空时退出码 2")
    args = parser.parse_args(argv)

    payload = _load_json(args.note)
    result = run_compliance(
        payload.get("draft_note", payload),
        document_type=payload.get("document_type", "inpatient_admission"),
        department_id=payload.get("department_id"),
        template=payload.get("template"),
        conflicts=payload.get("conflicts"),
        policy=payload.get("policy"),
        rag_hits=payload.get("rag_hits"),
    )

    out = result.to_dict()
    out["rulepack_version"] = result.rulepack_version
    print(json.dumps(out, ensure_ascii=False, indent=2))

    if result.errors:
        return 1
    if args.fail_on_warnings and result.warnings:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
