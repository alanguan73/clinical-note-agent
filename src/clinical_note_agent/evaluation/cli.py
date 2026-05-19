from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from clinical_note_agent.evaluation.report import report_to_markdown, write_report
from clinical_note_agent.evaluation.runner import run_evaluation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="按评估计划执行质控金样例/夹具场景，输出结构化报告",
    )
    parser.add_argument(
        "plan",
        type=Path,
        help="评估计划 YAML（见 evaluation/plans/）",
    )
    parser.add_argument(
        "-o",
        "--output-json",
        type=Path,
        help="写入 JSON 报告路径",
    )
    parser.add_argument(
        "-m",
        "--output-md",
        type=Path,
        help="写入 Markdown 报告路径",
    )
    parser.add_argument(
        "--stdout",
        choices=["json", "md", "summary"],
        default="summary",
        help="终端输出格式（默认仅摘要）",
    )
    args = parser.parse_args(argv)

    report = run_evaluation(args.plan.resolve())

    write_report(
        report,
        json_path=str(args.output_json) if args.output_json else None,
        markdown_path=str(args.output_md) if args.output_md else None,
    )

    if args.stdout == "json":
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    elif args.stdout == "md":
        print(report_to_markdown(report))
    else:
        print(report.executive_summary())
        for m in report.metrics:
            status = "通过" if m.passed else "失败"
            print(f"  [{status}] {m.metric_id}: {m.name} ({m.pass_rate:.0%})")

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
