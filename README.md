# Clinical Note Agent（智能病历辅助生成）

院内病历辅助生成系统的产品与技术规格，路线 **C**：事实层 + 模板 + 合规硬约束。

**GitHub**：https://github.com/alanguan73/clinical-note-agent

## 文档

| 文件 | 说明 |
|------|------|
| [docs/product/医疗病历生成Agent-产品文档-v0.4.md](docs/product/医疗病历生成Agent-产品文档-v0.4.md) | **当前** 产品文档（方案 B：程序调度 + 极少 LLM） |
| [docs/product/医疗病历生成Agent-产品文档-v0.3.md](docs/product/医疗病历生成Agent-产品文档-v0.3.md) | 历史版本（多段 LLM 流水线） |

## 输出前质控（T6）

已实现 **方案 B** 质控模块（程序校验，不调 LLM）：

| 模块 | 路径 | 说明 |
|------|------|------|
| `validate.schema` | `src/clinical_note_agent/qc/schema_validate.py` | 各节 JSON Schema |
| `validate.rules` | `src/clinical_note_agent/qc/rules_validate.py` | 必填项、来源、冲突、科室规则 |
| `rules.validate` | `src/clinical_note_agent/qc/engine.py` → `run_compliance()` | 编排入口 + RAG 院规比对 |
| 规则包 | `rules/base/`、`rules/departments/` | 病案质控规则 YAML |

**安装与测试**

```bash
cd clinical-note-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

**CLI（对草稿 JSON 跑质控）**

```bash
note-qc tests/fixtures/d1_draft_pass.json
```

**质控评估（指标 + 报告）**

```bash
note-eval evaluation/plans/sample.discharge_admission_qc.yaml
note-eval evaluation/plans/sample.discharge_admission_qc.yaml \
  -o evaluation/samples/sample_report.json \
  -m evaluation/samples/sample_report.md
```

详见 [evaluation/README.md](evaluation/README.md)。

**编排器接入（生成流水线 T6）**

```python
from clinical_note_agent.qc import run_compliance

compliance = run_compliance(
    draft_note,
    document_type="inpatient_admission",
    department_id="thoracic_surgery",
    template=template,
    conflicts=conflicts,
    rag_hits=rag_hits,  # 程序 RAG 检索结果
)
# → SSE event: compliance，然后 done
```

`compliance.errors` 非空时建议阻断「视为完成」；`warnings`（含 `CONFLICT_UNRESOLVED`）**不阻断**草稿保存（见产品文档 §19、§25）。

## 出院记录流水线（书写 → 程序 QC → LLM QC）

购物车模式出院记录三线流水线：

```text
证据输入 ([[记录类型]] 文本 / JSON)
    → build_evidence_corpus()   # 自动拼接，排除 [[附加信息]]
    → 书写 LLM（或传入 writing_output）
    → run_discharge_compliance()  # 程序 QC
    → LLM 质控（对照 corpus 删幻觉 / 防误删）
    → 终审程序 QC
    → final_output
```

**Python**

```python
from clinical_note_agent import build_evidence_corpus, run_discharge_pipeline
from clinical_note_agent.llm import OpenAICompatibleClient

corpus = build_evidence_corpus(raw_text)  # 含 evidence_flags
client = OpenAICompatibleClient()       # OPENAI_API_KEY / OPENAI_BASE_URL

result = run_discharge_pipeline(
    raw_text,
    writing_client=client,
    llm_qc_client=client,
)
# result.final_output / result.final_compliance / result.stages
```

**CLI**

```bash
# 仅查看拼接后的 evidence_corpus
note-pipeline tests/fixtures/evidence_sample.txt --corpus-only

# 使用已有书写结果 + mock LLM 质控（CI）
note-pipeline input.txt --writing-output draft.json --provider mock

# 全链路 OpenAI-compatible
export OPENAI_API_KEY=...
note-pipeline input.txt --provider openai -o result.json
```

提示词：`prompts/discharge_writing_system.md`（集成方完整书写 prompt）、`prompts/discharge_llm_qc_system.md`。

## 入院记录流式体验（先显模板 + 增量 SSE）

已实现 v0.4 **方案 B** 流式编排（程序填槽为主，T0 不调 LLM）：

```text
revision_created → template_loaded（全文模板骨架）
  → section_patch（检验/影像 T1）
  → physician_verbatim_patch / section_patch（口述 T2）
  → compliance（程序质控 T6）→ done
```

**Python**

```python
from clinical_note_agent import stream_admission_generate, GenerateRequest

req = GenerateRequest(template={...}, evidence={...}, department_id="thoracic_surgery")
for event in stream_admission_generate(req):
    print(event.event, event.data)  # 或 event.to_sse() 写给客户端
```

**CLI（SSE 输出）**

```bash
note-stream tests/fixtures/d1_generate_request.yaml
note-stream tests/fixtures/d1_generate_request.yaml --json-events  # JSON Lines
```

**HTTP API（可选）**

```bash
pip install -e ".[api]"
uvicorn clinical_note_agent.api.app:app --reload
# POST /v1/notes/generate  Content-Type: application/json  → text/event-stream
```

## 五种病历类型

| `document_type` | 中文 | 生成入口 |
|-----------------|------|----------|
| `inpatient_admission` | 入院记录 | `stream_note_generate` / `note-stream` |
| `discharge_summary` | 出院记录 | `run_discharge_pipeline` / `note-pipeline` |
| `first_progress_note` | 首次病程记录 | `stream_note_generate` |
| `senior_round_note` | 上级医师查房记录 | `stream_note_generate` |
| `daily_progress_note` | 日常病程记录 | `stream_note_generate` |

```bash
# 列出类型
note-stream --list-types

# 首次病程示例
note-stream tests/fixtures/first_progress_request.yaml

# 五种病历评估
note-eval evaluation/plans/sample.five_document_types.yaml
```

内置模板：

- 入院：`templates/inpatient/thoracic_trauma_mva.yaml`、`ped_fever_admission.yaml`
- 病程：`templates/progress/first_progress_default.yaml`、`senior_round_default.yaml`、`daily_progress_default.yaml`
- 出院：`templates/discharge/default.yaml`（字段说明；正文走 pipeline）

## 金样例回归

见 `tests/golden/`，与文档附录 D 对应，供 CI 集成。质控相关断言见 `tests/golden/test_golden_qc_assertions.py`。

## 状态

- 版本：**v0.4**（架构方案 B）
- 首期：住院入院记录（儿科、胸外科试点）
- 司法区：中国大陆（默认策略，院方可覆盖）

## 开发与推送

见 [docs/DEV-git-push.md](docs/DEV-git-push.md)（SSH、Cursor Agent 自动 push 说明）。

## 许可

内部产品规格；上线前须经医务、病案、信息科及法务审阅。
