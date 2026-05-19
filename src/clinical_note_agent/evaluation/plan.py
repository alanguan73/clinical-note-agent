from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_evaluation_plan(path: Path) -> dict[str, Any]:
    """加载评估计划 YAML，返回 evaluation_plan 根节点。"""
    with path.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if not doc or "evaluation_plan" not in doc:
        raise ValueError(f"缺少 evaluation_plan 根节点: {path}")
    plan = doc["evaluation_plan"]
    plan["_plan_path"] = str(path.resolve())
    return plan


def resolve_repo_path(plan: dict[str, Any], relative: str) -> Path:
    """将计划内相对路径解析为绝对路径（相对仓库根目录）。"""
    plan_path = Path(plan["_plan_path"])
    # evaluation/plans/*.yaml → 仓库根为 parents[2]
    if "plans" in plan_path.parts:
        repo_root = plan_path.parents[2]
    else:
        repo_root = plan_path.parent
    return (repo_root / relative).resolve()
