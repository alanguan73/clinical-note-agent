from __future__ import annotations

from typing import Any

# 首期：RAG 检索由程序固定 query 完成；此处仅消费检索结果做合规比对。
# 集成方传入 rag_hits: [{ "section_key", "policy_id", "excerpt", "must_include"?, "forbidden_phrases"? }]


def check_rag_policy(
    draft_note: dict[str, Any],
    rag_hits: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """根据院规 RAG 命中结果生成 violations（不调 LLM）。"""
    violations: list[dict[str, Any]] = []
    if not rag_hits:
        return violations

    for hit in rag_hits:
        section_key = hit.get("section_key")
        if not section_key:
            continue
        section = draft_note.get(section_key)
        if not isinstance(section, dict):
            continue
        text = (section.get("text") or "") + (section.get("verbatim") or "")

        for phrase in hit.get("forbidden_phrases") or []:
            if phrase and phrase in text:
                violations.append(
                    {
                        "code": "RAG_POLICY_VIOLATION",
                        "field": f"draft_note.{section_key}",
                        "severity": "warning",
                        "message": f"院规要求避免使用「{phrase}」，请核对。",
                    }
                )

        must_include = hit.get("must_include")
        if must_include and must_include not in text:
            violations.append(
                {
                    "code": "RAG_POLICY_VIOLATION",
                    "field": f"draft_note.{section_key}",
                    "severity": "warning",
                    "message": f"院规建议包含：{must_include}",
                }
            )

    return violations
