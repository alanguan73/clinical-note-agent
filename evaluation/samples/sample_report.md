# 质控评估报告：出院入院质控基线评估

- **计划 ID**: `discharge-admission-qc-baseline`
- **版本**: 2026-05-19
- **范围**: discharge_summary, inpatient_admission
- **通过率阈值**: 100%
- **总结果**: ✅ 达标

## 执行摘要

达标：6/6 项核心指标通过，11/11 条场景通过（总通过率 100%）。

## 分析架构

```text
evidence_corpus → build_evidence_corpus()
入院 program_qc → run_compliance()（Schema + rules + RAG）
出院 program_qc → run_discharge_compliance()（validate + grounding）
出院 llm_qc → run_llm_qc_stage()（句级语义，本计划不执行 LLM）
出院 final_program_qc → 终审程序 QC
```

## 指标分析

### ✅ M01_anti_hallucination — 反幻觉（极少输入 · D-7） （通过率 100%，目标 ≥ 100%）

| 场景 | 结果 | 说明 |
|------|------|------|
| `d7_bad_must_fail` | 通过 | 通过 |
| `d7_good_must_pass` | 通过 | 通过 |

### ✅ M02_scene_e_dates — 场景E日期占位（D-9） （通过率 100%，目标 ≥ 100%）

| 场景 | 结果 | 说明 |
|------|------|------|
| `d9_bad_placeholder` | 通过 | 通过 |
| `d9_good_no_dates` | 通过 | 通过 |

### ✅ M03_length_of_stay — 住院天数公式（W07） （通过率 100%，目标 ≥ 100%）

| 场景 | 结果 | 说明 |
|------|------|------|
| `los_wrong_days` | 通过 | 通过 |
| `los_correct_days` | 通过 | 通过 |

### ✅ M04_ungrounded_numeric — 数值须有来源（Q07） （通过率 100%，目标 ≥ 100%）

| 场景 | 结果 | 说明 |
|------|------|------|
| `numeric_not_in_corpus` | 通过 | 通过 |

### ✅ M05_admission_baseline — 入院记录基线（D-1 / D-2） （通过率 100%，目标 ≥ 100%）

| 场景 | 结果 | 说明 |
|------|------|------|
| `d1_pass_no_errors` | 通过 | 通过 |
| `d2_conflict_warning` | 通过 | 通过 |

### ✅ M06_anti_overdelete_regression — 防误删回归信号（D-8 · 程序层） （通过率 100%，目标 ≥ 100%）

| 场景 | 结果 | 说明 |
|------|------|------|
| `d8_good_program_pass` | 通过 | 通过 |
| `d8_overdelete_detectable` | 通过 | 误删样例应丢失 WBC 7.66 |

## 规则覆盖（提示词目录）

| 规则 | 状态 | machine_code | 本轮指标 |
|------|------|--------------|----------|
| W02 宁可不输出绝不编造 | partial | AI_INVENTED_DIAGNOSIS | — |
| W03 逐字段核查来源 | partial | UNGROUNDED_CLAIM | M01_anti_hallucination |
| W04 字段非强制凑齐 | planned | FIELD_NOT_IN_EVIDENCE | SPARSE_INPUT_EXCESS_OUTPUT, UNGROUNDED_CLAIM, SCENE_E_PLACEHOLDER, LENGTH_OF_STAY_MISMATCH, UNGROUNDED_NUMERIC, CONFLICT_UNRESOLVED |
| W05 输出策略矩阵 A-E | partial | CONFLICT_UNRESOLVED | M05_admission_baseline |
| W06 场景E日期字段不输出 | implemented | SCENE_E_PLACEHOLDER | M02_scene_e_dates |
| W07 住院天数加一 | implemented | LENGTH_OF_STAY | — |
| W12 科室术语规范 | partial | DEPARTMENT_TERM_INAPPROPRIATE | — |
| Q01 删除无据幻觉 | partial | UNGROUNDED_CLAIM | M01_anti_hallucination |
| Q03 字段级无据删整段 | partial | FIELD_NOT_IN_EVIDENCE | — |
| Q05 场景E空值删除 | implemented | SCENE_E_PLACEHOLDER | M02_scene_e_dates |
| Q07 数值须有来源 | partial | UNGROUNDED_NUMERIC | M04_ungrounded_numeric |
| Q08 诊断治疗医嘱验证 | partial | UNGROUNDED_CLAIM | M01_anti_hallucination |

## 改进建议

1. 将 W04 FIELD_NOT_IN_EVIDENCE 从 planned 提升为 implemented，并补充金样例
2. Q02 反误删仍以 LLM 为主，程序层可增「删后关键数值缺失」检测
3. 将 planned 规则程序化（建议从 W04 起），减少 llm_only 兜底
