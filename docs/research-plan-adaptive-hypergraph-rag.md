---
title: "Query-Conditioned Adaptive Hypergraph Retrieval with Self-Verification for RAG"
type: "research_plan"
status: "draft"
target: "SCI 期刊论文 (IEEE TKDE / IP&M / KBS / ESWA / TNNLS)"
based_on: "Hyper-RAG (Nature Communications 2026, DOI: 10.1038/s41467-026-71411-1)"
duration: "约 6 个月"
language: "zh-CN"
---

# Query-Conditioned Adaptive Hypergraph Retrieval with Self-Verification for RAG

## 一、论文总目标

本研究基于 Hyper-RAG 的超图检索框架，重点解决其离线高阶关系抽取成本较高、动态语料更新不灵活的问题。核心思路不是简单追求全面超过原 Hyper-RAG，而是在答案质量统计不劣的前提下，通过查询时按需构造高阶超边、轻量触发机制和证据级自验证，显著降低知识库构建成本和低/中查询量场景下的平均总成本。

推荐论文主张：

> Query-conditioned hyperedge induction can preserve the factuality advantage of Hyper-RAG while substantially reducing offline construction cost, when activated by a lightweight trigger and controlled by evidence-grounded verification.

## 二、核心贡献

1. **Cost-Aware Query-Conditioned Hyperedge Induction**  
   将原 Hyper-RAG 的离线全量高阶超边抽取，改为围绕 query、初始检索片段、实体集合和低阶关系的 test-time 高阶超边构造。

2. **Lightweight Trigger for Adaptive Activation**  
   基于检索熵、分数间隔、query 复杂度、实体覆盖率等轻量信号，判断单条 query 是否需要动态构造高阶超边，避免 always-on 带来的查询成本膨胀。

3. **Evidence-Grounded Hyperedge Verification**  
   对动态构造出的 candidate hyperedge 进行证据级验证，要求其 entity set、relation description 和 evidence span 能被原文片段支持，从而过滤 unsupported 或 spurious hyperedge。

4. **Amortized Cost-Quality Analysis for Hypergraph RAG**  
   不只比较答案质量，还系统分析 indexing cost、query-time construction cost、verification cost、latency 和不同 query volume 下的 break-even point。

5. **Mechanism and Failure Analysis**  
   通过 KMR、HER、错误传播系数 alpha、unsupported hyperedge rate 和案例分析，解释动态超边构造何时有效、何时失败。

## 三、研究问题

**RQ1:** 动态高阶超边构造能否在显著降低离线 indexing cost 的同时，保持相对 offline Hyper-RAG 的答案质量非劣？

**RQ2:** 轻量 trigger 能否有效识别需要高阶关系增强的 query，并降低不必要的 query-time construction cost？

**RQ3:** evidence-grounded verifier 能否降低 unsupported hyperedge rate、HER 和最终答案幻觉？

**RQ4:** 在不同 query volume 下，本方法相对 offline Hyper-RAG、Hyper-RAG-Lite、LightRAG 和 GraphRAG 的 cost-quality Pareto 优势何时成立？

## 四、总体实验假设

1. 相比 offline Hyper-RAG，本方法可以将离线 indexing token cost 降低至少 50%。
2. 在主测试集上，本方法相对 offline Hyper-RAG 的答案质量满足非劣效标准，例如绝对分差不低于 -3%。
3. 相比 always-on dynamic construction，trigger 能显著降低 query-time 构造调用率，并保持答案质量损失可控。
4. 相比无验证动态构造，verifier 能显著降低 unsupported hyperedge rate 和 hallucination error rate。
5. 在低/中查询量或动态语料场景中，本方法的 amortized total cost 优于 offline Hyper-RAG。

## 五、成本模型

为了避免审稿人质疑“只是把离线成本转移到在线成本”，所有实验统一报告以下成本：

```text
C_total(Q) = C_index + Q * (C_retrieve + p_trigger * C_construct + C_verify + C_generate)
C_avg(Q)   = C_total(Q) / Q
```

其中：

- `C_index`: 离线建库成本，包括 chunk embedding、实体抽取、低阶关系抽取、高阶关系抽取。
- `C_retrieve`: 每次查询的基础检索成本。
- `p_trigger`: trigger 触发动态构造的比例。
- `C_construct`: 单次动态高阶超边构造成本。
- `C_verify`: 动态超边验证成本。
- `C_generate`: 最终答案生成成本。
- `Q`: query volume，建议测试 `10 / 50 / 100 / 500 / 1000`。

## 六、方法框架

### 6.1 Offline Indexing

离线阶段只保留低成本、可复用的基础结构：

1. 文档切块。
2. chunk embedding。
3. 实体抽取。
4. 低阶关系抽取。
5. 可选：跳过或弱化离线高阶关系抽取。

目标是减少原 Hyper-RAG 中高阶超边全量抽取带来的 indexing token 和 LLM 调用成本。

### 6.2 Query-Time Hyperedge Induction

对每条 query，先执行基础检索，获得：

- query entities；
- top-k retrieved chunks；
- retrieved low-order edges；
- entity coverage signal；
- retrieval uncertainty signal。

若 trigger 判定需要高阶关系增强，则构造 candidate hyperedges：

```json
{
  "entity_set": ["entity_1", "entity_2", "entity_3"],
  "relation_description": "description of high-order relation",
  "evidence_chunk_ids": ["chunk-xxx", "chunk-yyy"],
  "evidence_spans": ["span text 1", "span text 2"],
  "confidence": 0.0
}
```

### 6.3 Evidence-Grounded Verification

verifier 对 candidate hyperedge 进行三层验证：

1. **Entity correctness:** entity set 是否均来自证据或可被证据明确指代。
2. **Relation support:** relation description 是否被 evidence spans 支持。
3. **High-order necessity:** 该关系是否确实需要多实体共同表达，而非简单低阶边拼接。

输出：

```json
{
  "label": "supported | partially_supported | unsupported | contradicted",
  "verification_score": 0.0,
  "supported_entities": [],
  "missing_entities": [],
  "evidence_spans": [],
  "reason": "brief explanation"
}
```

只有通过阈值的 hyperedge 才进入最终检索上下文。


## 七、实验计划 (15 步，每步 = 目标 + 验收)

### Phase 0: 基线与环境就绪

**目标:** 跑通原 Hyper-RAG，并建立可审计、可算成本的 baseline。

**Step 1: 环境与 codebase 跑通**  
- 目标：让现有 Hyper-RAG codebase 在本机上完整跑通 Step_0 → Step_3 的全流程  
- 验收：在 `datasets/mix` 上端到端无报错，产出可评测的答案与日志  

**Step 2: 论文核心数字复现**  
- 目标：复现 Hyper-RAG 在 NeurologyCrop 与 9 个跨领域数据集上的关键 baseline 数字  
- 验收：与论文报告的 +12.3% (vs LLM)、+6.0% (vs LightRAG)、+35.5% (9 dataset 均值) 三个核心数字误差 < 5 个百分点  

**Step 3: 现有 pipeline 成本画像**  
- 目标：量化记录现有 Hyper-RAG 的 indexing token / query latency / storage / hyperedge 命中率  
- 验收：产出每个数据集的 cost-quality baseline 表，作为后续所有改进的对照基线

**Go / No-Go 标准:**

- 若 offline Hyper-RAG 和 Hyper-RAG-Lite 无法稳定运行，则优先修复复现管线，不进入方法开发。

---

### Phase 1:单组件开发

**目标:** 实现动态超边构造的最小可用版本，并证明其具备成本优势潜力。

**Step 4:Adaptive Hyperedge Construction 模块**
- 目标:实现 query-time 按需构造 hyperedge 的 minimal working version,在 indexing 阶段跳过 high-order 抽取
- 验收:在 mix 数据集上 indexing token 成本相对论文 baseline 下降 ≥ 50%,且答案质量不低于 baseline 5%

**Step 5:轻量 Trigger 机制**
- 目标:实现决定"是否触发动态构造"的轻量决策器
- 验收:在验证集上触发率落在 20%–50% 区间,且未触发 query 的答案质量与"全 baseline"基本一致(差距 < 2%)

**Step 6:Self-Verification 模块**
- 目标:实现 hyperedge 自验证组件,能过滤未被原文证据支持的 spurious hyperedge
- 验收:在自建 gold hyperedge 小集上,verifier 的 precision ≥ 0.85,recall ≥ 0.70

**Step 7:Gold Hyperedge Benchmark 构造**
- 目标:构造小规模 hyperedge 标注集,用于 verifier 阈值校准与评测
- 验收:≥ 500 条样本(含正负各半),双人 / 双模型一致性(Cohen's κ)≥ 0.7

**Go / No-Go 标准:**

- 若动态构造质量明显低于 Hyper-RAG，先分析是 entity extraction、chunk retrieval 还是 hyperedge induction 出错，不直接进入 trigger 开发。
---

### Phase 2:集成与调优

**Step 8:Adaptive + Verification 联合 framework 集成**
- 目标:把两个模块组装为统一端到端 pipeline
- 验收:在 mix 数据集上联合 pipeline 端到端无 bug 运行,产出可被 `evaluate/` 接收的输出格式

**Step 9:超参联合调优**
- 目标:在验证集上联合搜索 trigger 阈值 × verifier 阈值的最优组合
- 验收:找到一组超参使 KMR / HER / α 三指标均不弱于论文 Hyper-RAG,同时 indexing cost 降幅 ≥ 50%

---

### Phase 3:全面评测与机制分析

**Step 10:9 个跨领域数据集全量评测**
- 目标:在 agriculture / art / fin / legal / math / mix / pathology / physics / neurology 上跑通 4 种配置(baseline / adaptive only / verification only / both)
- 验收:每个数据集 × 每个配置的完整指标都已产出,多次 run 方差 < 1%

**Step 11:核心 Ablation 表**
- 目标:产出论文中心 ablation 表,证明 Adaptive 与 Verification 的独立贡献与互补性
- 验收:both > adaptive-only > baseline 且 both > verification-only > baseline,差异通过显著性检验(p < 0.05)

**Step 12:跨 LLM 鲁棒性**
- 目标:在 GPT-4o-mini / Qwen-Plus / DeepSeek-V3 等多个 LLM 上验证方法稳定性
- 验收:≥ 3 个 LLM 上方法均保持优势,组件相对增益方向一致(无反向情形)

**Step 13:成本-质量 Pareto 分析**
- 目标:绘制 indexing cost / query latency 与答案质量的 Pareto frontier
- 验收:本方法的散点严格落在原 Hyper-RAG 的左上方,且位于 frontier 上

**Step 14:幻觉机制指标分析**
- 目标:复现并对比 KMR / HER / α 三个机制层面指标,验证 framework 在幻觉链路上的改善
- 验收:α 系数低于论文报告的 0.14,KMR 与 HER 不劣于论文 Hyper-RAG

**Step 15:失败模式定位**
- 目标:识别本方法仍然失败的 query 类型,产出 limitations 章节素材
- 验收:≥ 3 类典型失败模式被命名并配有具体案例,可写入 discussion

---

## 八、整体进度判定标准

| 累计完成 | 健康度信号 |
|---|---|
| Step 1-3 | RQ / related-work matrix / claim-risk-evidence 表完成,代表性 baseline 与成本画像跑通 |
| Step 4-7 | 两个组件单独 working,gold benchmark 标完 |
| Step 8-9 | 联合 pipeline 跑通且超参稳定 |
| Step 10-15 | 所有评测完成,论文核心结论已成立 |
