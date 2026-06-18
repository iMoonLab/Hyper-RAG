# NeurologyCrop（`neurology`）复现调用追踪

本文档满足 [`.cursor/goal.md`](../.cursor/goal.md) 第三节「书面留痕」：记录脚本入口、路径、与库侧主链路索引；**本仓库实测分数**与论文报告数字分开书写。LLM / 嵌入的 URL 与密钥见仓库根目录 `my_config.py`（**不在此重复秘钥**）。

---

## 1. 环境与数据

| 项 | 说明 |
|----|------|
| Conda | `hyper-rag`（与本地约定一致） |
| 依赖 | 根目录 `pip install -r requirements.txt` |
| 嵌入维度 | `python scripts/verify_embedding_dim.py`（与 `my_config.EMB_DIM` 一致后跑索引） |
| Smoke | `python examples/hyperrag_demo.py`（`insert` + 多 `QueryParam.mode`） |
| 数据 | `datasets/neurology/neurology.jsonl` |
| 默认 `data_name` | [`reproduce/pipeline_defaults.py`](../reproduce/pipeline_defaults.py) 中 `DATA_NAME = "neurology"` |

**部署假设（与复现脚本注释一致）**：Chat LLM 走自建 OpenAI 兼容服务；嵌入走公网 API。Step_1 与 Step_3 中 `HyperRAG` 的并发参数以**当前代码**为准（见下表）。

---

## 2. 流水线各 Step（命令与产物）

工作目录：`caches/neurology/`。

| Step | 命令 | 主要输入 | 主要输出 |
|------|------|----------|----------|
| Step_0 | `python reproduce/Step_0.py`（可加 `--data-name neurology`） | `datasets/neurology/*.jsonl` | `caches/neurology/contexts/neurology_unique_contexts.json` |
| Step_1 | `python reproduce/Step_1.py --data-name neurology` | 上表 `*_unique_contexts.json` | 同目录下 `kv_store_*.json`、`vdb_*.json`、`hypergraph_chunk_entity_relation.hgdb`、`HyperRAG.log` 等 |
| Step_2 | `python reproduce/Step_2_extract_question.py` | context + LLM | `questions/2_stage.json`、`questions/2_stage_ref.json`（各 **5** 条；`question_stage=2`，脚本内 `max_cnt=5`） |
| Step_3 | `python reproduce/Step_3_response_question.py`（按需改脚本内 `mode` 后多次运行） | `questions/2_stage.json` + Step_1 索引 | `response/<mode>_2_stage_result.json`、`*_errors.json` |

**本机已跑通的 `QueryParam.mode`**：`naive`、`hyper`、`hyper-lite`（各对应一份 `response/` 结果）。

**Step_1 / Step_3 中 `HyperRAG` 并发（留痕时自代码读取）**：

| 脚本 | `llm_model_max_async` | `embedding_func_max_async` |
|------|------------------------|----------------------------|
| [`reproduce/Step_1.py`](../reproduce/Step_1.py) | 1 | 4 |
| [`reproduce/Step_3_response_question.py`](../reproduce/Step_3_response_question.py) | 32 | 4 |

---

## 3. 库侧主链路（索引与查询）

- **`HyperRAG.insert`**（Step_1）：分块 → 嵌入写入向量库 → LLM 抽取实体/关系 → 超图持久化；实现入口见 [`hyperrag/hyperrag.py`](../hyperrag/hyperrag.py)，分块与抽取逻辑见 [`hyperrag/operate.py`](../hyperrag/operate.py)。
- **`HyperRAG.aquery`**（Step_3）：按 `QueryParam.mode` 走 `naive_query` / `hyper_query` / `hyper_query_lite` 等分支，组上下文后调 LLM；见 [`hyperrag/operate.py`](../hyperrag/operate.py) 与 [`hyperrag/hyperrag.py`](../hyperrag/hyperrag.py)。
- **存储**：KV / 向量库 / 超图文件命名与路径见 [`hyperrag/storage.py`](../hyperrag/storage.py)。

更细的模块表若需对照，可与 [`.cursor/arch.md`](../.cursor/arch.md) 中既有章节交叉引用。

---

## 4. 可选评测（`evaluate_by_scoring`）

| 命令 | 说明 |
|------|------|
| `python evaluate/evaluate_by_scoring.py --data-name neurology --mode naive --question-stage 2` | 与 Step_3 产物前缀一致 |
| 同上，`--mode hyper` / `--mode hyper-lite` | 各跑一遍 |

脚本固定写入 `caches/neurology/evalation/scoring_2_stage_question.json`；本复现另存分 mode 副本便于对照：

- `caches/neurology/evalation/scoring_2_stage_naive.json`
- `caches/neurology/evalation/scoring_2_stage_hyper.json`
- `caches/neurology/evalation/scoring_2_stage_hyper-lite.json`

跑完后将 **`scoring_2_stage_naive.json` 复制回 `scoring_2_stage_question.json`**，与计划文档中的默认文件名一致（内容对应 **naive**）。

### 4.1 本仓库实测五维均分（控制台摘要，非论文结果）

评测使用与 Step_2/3 相同的 `my_config` LLM（评分裁判）。**勿与 Nature Communications 论文表格对比。**

| mode | Comprehensiveness | Diversity | Empowerment | Logical | Readability | **Averaged Score** |
|------|-------------------|-----------|-------------|---------|-------------|-------------------|
| naive | 59.00 | 74.40 | 60.60 | 66.00 | 74.60 | **66.92** |
| hyper | 78.00 | 79.40 | 68.60 | 89.00 | 92.00 | **81.40** |
| hyper-lite | 72.40 | 76.40 | 61.00 | 89.00 | 88.00 | **77.36** |

---

## 5. 异常与重跑

- Step_0 若已有 `*_unique_contexts.json` 会跳过；改源数据后需手动删除再跑。
- 若更换嵌入模型或 `EMB_DIM`，建议清空 `caches/neurology` 下除可保留的 `contexts/` 外索引文件后自 Step_0/1 重建。
- 本阶段未记录阻塞性流水线错误；若 Step_3 产生非空 `*_errors.json`，须在后续版本条目中补充原因（超时 / 429 等）。

---

*文档版本：与 `neurology` 复现阶段对齐；论文数值仍以 DOI `10.1038/s41467-026-71411-1` 为准。*
