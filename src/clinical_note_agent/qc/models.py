from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ComplianceIssue:
    """单条合规/质控项（errors 或 warnings 元素）。"""

    code: str
    field: str
    message: str
    severity: str = "warning"  # error | warning | strong（warning 条目内可用 strong）
    blocks_sign: bool = False

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "code": self.code,
            "field": self.field,
            "message": self.message,
        }
        if self.severity != "error":
            out["severity"] = self.severity
        if self.blocks_sign:
            out["blocks_sign"] = True
        return out


@dataclass
class ComplianceResult:
    """T6 rules.validate 产出，对应 API 响应 compliance 字段。"""

    errors: list[ComplianceIssue] = field(default_factory=list)
    warnings: list[ComplianceIssue] = field(default_factory=list)
    rulepack_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
        }

    @property
    def ok_for_draft(self) -> bool:
        """草稿保存：errors 为空即可（warnings 不阻断）。"""
        return len(self.errors) == 0

    def can_sign(self, *, blocks_sign_on_conflict: bool = False) -> bool:
        if not self.ok_for_draft:
            return False
        if not blocks_sign_on_conflict:
            return True
        return not any(w.blocks_sign for w in self.warnings)
