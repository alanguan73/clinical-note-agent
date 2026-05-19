from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_PKG_ROOT = Path(__file__).resolve().parents[3]
RULES_DIR = _PKG_ROOT / "rules"


@dataclass
class ForbiddenPattern:
    pattern: str
    code: str
    message: str
    _compiled: re.Pattern[str] = field(repr=False)

    @classmethod
    def from_dict(cls, raw: dict[str, str]) -> ForbiddenPattern:
        return cls(
            pattern=raw["pattern"],
            code=raw["code"],
            message=raw["message"],
            _compiled=re.compile(raw["pattern"]),
        )


@dataclass
class RulePack:
    version: str
    document_type: str
    default_required_sections: list[str]
    physician_only_sections: list[str]
    sections_requiring_source_refs: list[str]
    department_id: str | None = None
    hidden_sections: list[str] = field(default_factory=list)
    extra_required_sections: list[str] = field(default_factory=list)
    forbidden_patterns: list[ForbiddenPattern] = field(default_factory=list)

    @property
    def rulepack_version(self) -> str:
        base = self.version
        if self.department_id:
            return f"{base}+{self.department_id}"
        return base

    def required_sections(self, template: dict[str, Any] | None) -> list[str]:
        """模板 sections 优先，否则用规则包默认 + 科室增量。"""
        if template and template.get("sections"):
            keys = [
                s["key"]
                for s in template["sections"]
                if s.get("required", True) and s.get("key")
            ]
            if keys:
                return keys
        req = list(self.default_required_sections)
        for key in self.extra_required_sections:
            if key not in req:
                req.append(key)
        return [k for k in req if k not in self.hidden_sections]


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_rulepack(document_type: str, department_id: str | None = None) -> RulePack:
    base_path = RULES_DIR / "base" / f"{document_type}.yaml"
    if not base_path.exists():
        raise FileNotFoundError(f"未找到文书类型规则包: {document_type} ({base_path})")

    base = _load_yaml(base_path)
    pack = RulePack(
        version=str(base.get("version", "0.0.0")),
        document_type=document_type,
        default_required_sections=list(base.get("default_required_sections", [])),
        physician_only_sections=list(base.get("physician_only_sections", [])),
        sections_requiring_source_refs=list(base.get("sections_requiring_source_refs", [])),
    )

    if not department_id:
        return pack

    dept_path = RULES_DIR / "departments" / f"{department_id}.yaml"
    if not dept_path.exists():
        return pack

    dept = _load_yaml(dept_path)
    pack.department_id = department_id
    pack.hidden_sections = list(dept.get("hidden_sections", []))
    pack.extra_required_sections = list(dept.get("extra_required_sections", []))
    pack.forbidden_patterns = [
        ForbiddenPattern.from_dict(p) for p in dept.get("forbidden_patterns", [])
    ]
    dept_ver = dept.get("version")
    if dept_ver:
        pack.version = f"{pack.version}/{dept_ver}"
    return pack
