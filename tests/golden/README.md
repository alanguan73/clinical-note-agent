# 金样例（附录 D）

与 `docs/product/医疗病历生成Agent-产品文档-v0.3.md` 附录 D 一致。

运行方式（示例）：将 `input` 作为 `EvidenceBundle` 调用生成 API，用 `assertions` 做自动化校验。

**质控（T6）**：对生成得到的 `draft_note` 调用 `clinical_note_agent.qc.run_compliance()`；见 `tests/golden/test_golden_qc_assertions.py` 与 `tests/fixtures/`。

**出院记录（现行提示词）**：`run_discharge_compliance()` + 金样例 D-7～D-9；规则映射见 `rules/prompt_catalog/discharge_prompt_rules.yaml`。

**质控评估（指标 + 报告）**：`note-eval evaluation/plans/sample.discharge_admission_qc.yaml`；见 `evaluation/README.md`。
