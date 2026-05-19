from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

import yaml

from clinical_note_agent.orchestrator import GenerateRequest, collect_note_generate
from clinical_note_agent.qc import run_compliance
from clinical_note_agent.qc.discharge_engine import run_discharge_compliance
from clinical_note_agent.qc.evidence_grounding import validate_evidence_grounding

from clinical_note_agent.evaluation.models import ScenarioResult


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_json(path: Path) -> dict[str, Any]:
    import json

    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _check_expect(
    *,
    scenario_id: str,
    metric_id: str,
    expect: dict[str, Any],
    ok_for_draft: bool,
    errors: list[Any],
    warnings: list[Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> ScenarioResult:
    warnings = warnings or []
    error_codes = [e.code for e in errors]
    warning_codes = [w.code for w in warnings]
    detail: dict[str, Any] = {
        "ok_for_draft": ok_for_draft,
        "error_codes": error_codes,
        "warning_codes": warning_codes,
    }
    if extra:
        detail.update(extra)

    failures: list[str] = []

    if "ok_for_draft" in expect and ok_for_draft != expect["ok_for_draft"]:
        failures.append(f"ok_for_draft 期望 {expect['ok_for_draft']}，实际 {ok_for_draft}")

    if expect.get("errors_empty") and errors:
        failures.append(f"errors 应为空，实际 {error_codes}")

    if expect.get("warnings_empty") and warnings:
        failures.append(f"warnings 应为空，实际 {warning_codes}")

    for code in expect.get("must_have_errors", []):
        if code not in error_codes:
            failures.append(f"缺少 error code: {code}")

    for code in expect.get("must_not_have_errors", []):
        if code in error_codes:
            failures.append(f"不应出现 error code: {code}")

    for code in expect.get("must_have_warnings", []):
        if code not in warning_codes:
            failures.append(f"缺少 warning code: {code}")

    if "can_sign" in expect:
        blocks = expect.get("blocks_sign_on_conflict", False)
        actual = ok_for_draft and (
            not blocks or not any(getattr(w, "blocks_sign", False) for w in warnings)
        )
        if actual != expect["can_sign"]:
            failures.append(f"can_sign 期望 {expect['can_sign']}，实际 {actual}")

    passed = len(failures) == 0
    return ScenarioResult(
        scenario_id=scenario_id,
        metric_id=metric_id,
        passed=passed,
        message="; ".join(failures) if failures else "通过",
        detail=detail,
    )


def run_discharge_golden(
    *,
    golden_path: Path,
    variant: str,
    scenario_id: str,
    metric_id: str,
    expect: dict[str, Any],
) -> ScenarioResult:
    case = _load_yaml(golden_path)
    flags = case.get("evidence_flags")
    corpus = case["evidence_corpus"]

    if variant == "bad":
        output = case["writing_ai_output_bad"]
    elif variant == "good":
        output = case["writing_ai_output_good"]
    else:
        return ScenarioResult(
            scenario_id=scenario_id,
            metric_id=metric_id,
            passed=False,
            message=f"未知 variant: {variant}",
        )

    result = run_discharge_compliance(
        output,
        evidence_corpus=corpus,
        evidence_flags=flags,
    )
    return _check_expect(
        scenario_id=scenario_id,
        metric_id=metric_id,
        expect=expect,
        ok_for_draft=result.ok_for_draft,
        errors=result.errors,
        warnings=result.warnings,
        extra={"golden_id": case.get("id"), "variant": variant},
    )


def run_admission_fixture(
    *,
    fixture_path: Path,
    scenario_id: str,
    metric_id: str,
    expect: dict[str, Any],
) -> ScenarioResult:
    payload = _load_json(fixture_path)
    result = run_compliance(
        payload.get("draft_note", payload),
        document_type=payload.get("document_type", "inpatient_admission"),
        department_id=payload.get("department_id"),
        template=payload.get("template"),
        conflicts=payload.get("conflicts"),
        policy=payload.get("policy"),
        rag_hits=payload.get("rag_hits"),
    )
    can_sign = result.can_sign(
        blocks_sign_on_conflict=expect.get("blocks_sign_on_conflict", False),
    )
    check_expect = {k: v for k, v in expect.items() if k != "can_sign"}
    base = _check_expect(
        scenario_id=scenario_id,
        metric_id=metric_id,
        expect=check_expect,
        ok_for_draft=result.ok_for_draft,
        errors=result.errors,
        warnings=result.warnings,
        extra={"can_sign": can_sign},
    )
    if "can_sign" in expect and can_sign != expect["can_sign"]:
        return ScenarioResult(
            scenario_id=scenario_id,
            metric_id=metric_id,
            passed=False,
            message=f"{base.message}; can_sign 期望 {expect['can_sign']}，实际 {can_sign}".strip("; "),
            detail={**base.detail, "can_sign": can_sign},
        )
    return base


def run_discharge_inline(
    *,
    scenario_id: str,
    metric_id: str,
    output: dict[str, Any],
    evidence_corpus: str,
    evidence_flags: dict[str, bool] | None,
    expect: dict[str, Any],
) -> ScenarioResult:
    result = run_discharge_compliance(
        output,
        evidence_corpus=evidence_corpus,
        evidence_flags=evidence_flags,
    )
    return _check_expect(
        scenario_id=scenario_id,
        metric_id=metric_id,
        expect=expect,
        ok_for_draft=result.ok_for_draft,
        errors=result.errors,
        warnings=result.warnings,
    )


def run_grounding_inline(
    *,
    scenario_id: str,
    metric_id: str,
    output: dict[str, Any],
    evidence_corpus: str,
    expect: dict[str, Any],
) -> ScenarioResult:
    issues = validate_evidence_grounding(output, evidence_corpus)
    error_codes = [i.code for i in issues]
    detail = {"error_codes": error_codes}
    failures: list[str] = []
    for code in expect.get("must_have_errors", []):
        if code not in error_codes:
            failures.append(f"缺少 error code: {code}")
    for code in expect.get("must_not_have_errors", []):
        if code in error_codes:
            failures.append(f"不应出现 error code: {code}")
    return ScenarioResult(
        scenario_id=scenario_id,
        metric_id=metric_id,
        passed=len(failures) == 0,
        message="; ".join(failures) if failures else "通过",
        detail=detail,
    )


def run_note_generate_fixture(
    *,
    fixture_path: Path,
    scenario_id: str,
    metric_id: str,
    expect: dict[str, Any],
) -> ScenarioResult:
    data = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    req = GenerateRequest(
        template=data["template"],
        evidence=data["evidence"],
        document_type=data["document_type"],
        department_id=data.get("department_id"),
    )
    result = collect_note_generate(req)
    compliance = result.compliance
    errors = compliance.get("errors", [])
    error_codes = [e["code"] for e in errors]
    detail: dict[str, Any] = {
        "document_type": data["document_type"],
        "error_codes": error_codes,
        "draft_note_keys": list(result.draft_note.keys()),
    }
    failures: list[str] = []
    if expect.get("errors_empty") and errors:
        failures.append(f"errors 应为空，实际 {error_codes}")
    if expect.get("ok_for_draft") is False and not errors:
        failures.append("期望质控不通过但 errors 为空")
    if expect.get("ok_for_draft") is True and errors:
        failures.append(f"期望质控通过但有 errors: {error_codes}")
    for key in expect.get("must_have_sections", []):
        if key not in result.draft_note:
            failures.append(f"draft_note 缺少节: {key}")
        elif not (result.draft_note[key].get("text") or "").strip():
            failures.append(f"节 {key} 内容为空")
    return ScenarioResult(
        scenario_id=scenario_id,
        metric_id=metric_id,
        passed=len(failures) == 0,
        message="; ".join(failures) if failures else "通过",
        detail=detail,
    )


def run_golden_assertion(
    *,
    golden_path: Path,
    assertion: str,
    scenario_id: str,
    metric_id: str,
) -> ScenarioResult:
    """执行金样例中非 compliance 的回归断言。"""
    case = _load_yaml(golden_path)
    passed = False
    message = ""

    if assertion == "overdelete_bad_loses_numeric":
        over = case.get("writing_ai_output_overdelete_bad", {})
        corpus = case.get("evidence_corpus", "")
        has_wbc = "7.66" in corpus
        lost = "7.66" not in over.get("入院情况", "")
        passed = has_wbc and lost
        message = "误删样例应丢失 WBC 7.66" if passed else "误删样例断言失败"
    elif assertion == "corpus_contains_wbc":
        passed = "7.66" in case.get("evidence_corpus", "")
        message = "证据应含 WBC 7.66" if passed else "证据缺少 WBC 7.66"
    else:
        message = f"未知 assertion: {assertion}"

    return ScenarioResult(
        scenario_id=scenario_id,
        metric_id=metric_id,
        passed=passed,
        message=message,
        detail={"assertion": assertion, "golden_id": case.get("id")},
    )


def run_scenario(
    plan: dict[str, Any],
    metric_id: str,
    scenario: dict[str, Any],
) -> ScenarioResult:
    from clinical_note_agent.evaluation.plan import resolve_repo_path

    scenario_id = scenario["id"]
    stype = scenario["type"]
    expect = scenario.get("expect", {})

    if stype == "discharge_golden":
        path = resolve_repo_path(plan, scenario["golden"])
        return run_discharge_golden(
            golden_path=path,
            variant=scenario["variant"],
            scenario_id=scenario_id,
            metric_id=metric_id,
            expect=expect,
        )
    if stype == "admission_fixture":
        path = resolve_repo_path(plan, scenario["fixture"])
        return run_admission_fixture(
            fixture_path=path,
            scenario_id=scenario_id,
            metric_id=metric_id,
            expect=expect,
        )
    if stype == "discharge_inline":
        return run_discharge_inline(
            scenario_id=scenario_id,
            metric_id=metric_id,
            output=scenario["output"],
            evidence_corpus=scenario["evidence_corpus"],
            evidence_flags=scenario.get("evidence_flags"),
            expect=expect,
        )
    if stype == "grounding_inline":
        return run_grounding_inline(
            scenario_id=scenario_id,
            metric_id=metric_id,
            output=scenario["output"],
            evidence_corpus=scenario["evidence_corpus"],
            expect=expect,
        )
    if stype == "golden_assertion":
        path = resolve_repo_path(plan, scenario["golden"])
        return run_golden_assertion(
            golden_path=path,
            assertion=scenario["assertion"],
            scenario_id=scenario_id,
            metric_id=metric_id,
        )
    if stype == "note_generate_fixture":
        path = resolve_repo_path(plan, scenario["fixture"])
        return run_note_generate_fixture(
            fixture_path=path,
            scenario_id=scenario_id,
            metric_id=metric_id,
            expect=expect,
        )

    return ScenarioResult(
        scenario_id=scenario_id,
        metric_id=metric_id,
        passed=False,
        message=f"未知场景类型: {stype}",
    )
