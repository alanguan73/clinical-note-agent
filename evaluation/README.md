# 质控评估

按**评估计划**对金样例与夹具执行场景校验，输出结构化报告（执行摘要 → 指标分析 → 规则覆盖 → 改进建议）。

## 快速开始

```bash
pip install -e ".[dev]"

# 运行样例计划（终端摘要）
note-eval evaluation/plans/sample.discharge_admission_qc.yaml

# 生成 JSON + Markdown 报告
note-eval evaluation/plans/sample.discharge_admission_qc.yaml \
  -o evaluation/samples/sample_report.json \
  -m evaluation/samples/sample_report.md

# 仅输出 JSON 到 stdout
note-eval evaluation/plans/sample.discharge_admission_qc.yaml --stdout json
```

退出码：`0` 达标，`1` 未达标（可用于 CI）。

## 新建评估计划

1. 复制模板：`evaluation/plans/template.evaluation_plan.yaml`
2. **规划阶段**填写：`architecture`、`core_metrics`（3–5 项）、`target_pass_rate`、`scoring`
3. **代码阶段**为每项指标增加 `scenarios`（金样例 bad/good 或夹具），实现对应 `machine_code` 后跑 `note-eval`

## 场景类型

| type | 说明 |
|------|------|
| `discharge_golden` | `tests/golden/D-*.yaml`，`variant: bad \| good` |
| `admission_fixture` | `tests/fixtures/*.json`，入院 `run_compliance` |
| `discharge_inline` | 计划内嵌 `output` + `evidence_corpus` |
| `grounding_inline` | 直接调用 `validate_evidence_grounding` |
| `golden_assertion` | 金样例非 compliance 断言（如 D-8 误删信号） |
| `note_generate_fixture` | YAML 请求 → `collect_note_generate()` 端到端 |

五种病历覆盖计划：`evaluation/plans/sample.five_document_types.yaml`。

## expect 字段

| 字段 | 含义 |
|------|------|
| `ok_for_draft` | `ComplianceResult.ok_for_draft` |
| `errors_empty` | errors 必须为空 |
| `must_have_errors` | 必须包含的 error code 列表 |
| `must_not_have_errors` | 不得出现的 error code |
| `must_have_warnings` | 必须包含的 warning code |
| `can_sign` | 结合 `blocks_sign_on_conflict` 判断签收 |

## 与 pytest 的关系

- `pytest`：开发时单测回归
- `note-eval`：按**业务指标**聚合多场景，产出**评估报告**供迭代与 CI 门禁

两者可共用同一份金样例 YAML，避免重复维护输入数据。
