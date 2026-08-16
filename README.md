# Research Agent Platform & Evaluation Harness

一个面向技术调研场景的智能研究 Agent 平台，以及配套的自动化评测与发布门禁体系。

项目目标是解决技术调研过程中**资料来源分散、人工整理效率低、大模型回答缺少来源依据，以及 Agent 质量难以系统评估**的问题，打通从问题输入、资料检索、证据整理、报告生成，到自动化评测、问题定位和回归验证的完整闭环。

---

## 1. 项目亮点

### 研究 Agent 平台

* 支持即时问答与深度研究两类任务链路
* 支持异步任务执行、状态恢复、进度查询与历史结果追踪
* 基于 RAG 组织本地知识与 Web 检索
* 支持向量检索、全文检索及 Hybrid 检索策略
* 将检索证据关联至报告内容，提升结论可追溯性
* 支持任务、报告、会话及文档的数据隔离
* 对高成本研究任务增加确定性保护，避免意图误判直接触发任务

### Agent Evaluation Harness

* 覆盖 Intent、Multi-turn、Tool Use、Memory、Fuzz、Security、Planning、Fact Quality 等能力
* 支持提交后快速回归、发版前验证和夜间评测
* 基于 pytest + JSONL 管理测试集
* 接入 GitHub Actions 与结果看板
* 支持失败 Case 冻结、Replay、独立 Holdout 验证
* 支持 LLM-as-Judge 与人工复核
* 区分 Agent 缺陷、评分器缺陷和数据缺失问题

---

## 2. 关键结果

### Agent 产品性能

单机受控 Chat 压测：

* 并发：5
* 持续时间：30 分钟
* 成功请求：5361
* 错误率：0
* 吞吐：约 2.98 req/s
* P95 延迟：约 2.2s

### 意图路由评测

构建 80 条离线意图用例，并针对否定表达、歧义输入和上下文切换等边界场景进行受控 Live API 验证。

首轮 24 条 Live Case 中：

* Accuracy：70.83% → 95.83%
* Macro F1：71.54% → 96.15%
* 错误创建研究报告：3 → 0

另外使用 12 条独立 Holdout Case 验证：

* Accuracy：91.67%
* 错误创建研究报告：0

该过程形成了：

**发现问题 → 冻结失败 Case → 修复 → 原集回归 → 独立 Holdout 验证**

的完整闭环。

### Planning 评测

共构建 40 条复杂研究任务：

* 主评测集：30 条
* 独立 Holdout：10 条

主评测：

* Subgoal Coverage：88%
* Constraint Retention：98%
* Redundant Step Rate：0%
* Irrelevant Step Rate：0%

Holdout：

* Subgoal Coverage：85%
* Constraint Retention：96%

失败主要集中在多约束叠加和多阶段任务拆解不完整。

### 事实质量与评分校准

使用 SimpleQA 和高风险开放问题分别评估事实准确性与证据一致性。

在 LLM-as-Judge 重复评分过程中，曾发现评分结果出现系统性偏移。进一步通过 Trace 和 Replay 排查后，定位到历史样本保存的证据内容不完整，而不是模型随机性或评分规则本身的问题。

后续改为：

* 持久化完整检索证据
* 证据不足时直接阻断评分
* 保留人工复核样本进行校准

该问题也体现了本项目不仅评估 Agent 本身，同时关注**评测系统自身是否可靠**。

---

## 3. 系统架构

### Agent 平台

```text
User
  ↓
Next.js / TypeScript
  ↓
FastAPI
  ↓
Intent / Policy
  ↓
Chat / Research Job
  ↓
Redis + ARQ
  ↓
Planning
  ↓
RAG / Web Search / Tool Use
  ↓
Report Generation
  ↓
PostgreSQL / pgvector / MinIO
```

### Evaluation Harness

```text
JSONL Cases
  ↓
Runner
  ↓
Agent / API / Planner
  ↓
Scorer
  ↓
Metrics
  ↓
Dashboard
  ↓
Quality Gate
  ↓
Failure Queue / Replay / Holdout
```

---

## 4. 技术栈

### Agent Platform

* Python
* FastAPI
* LangChain
* PostgreSQL
* pgvector
* PostgreSQL FTS
* Redis
* ARQ
* MinIO
* Next.js
* TypeScript
* Docker

### Evaluation

* Python
* pytest
* JSONL
* GitHub Actions
* LLM-as-Judge
* Tracing
* Replay
* Fuzz / Adversarial Testing

---

## 5. 评测覆盖

当前 Evaluation Harness 主要覆盖以下能力：

* 意图识别与路由
* 多轮会话状态
* 工具选择与参数生成
* 返回结果解析
* 超时与异常恢复
* Memory 与跨轮引用
* 模糊输入与噪声输入
* Prompt Injection
* 越权访问
* 跨用户数据隔离
* 事实准确性
* 证据一致性
* Planning 子目标拆解
* 约束保留
* 性能与稳定性

---

## 6. 工程设计思路

这个项目并不是单纯追求“测试全部通过”，而是重点解决以下问题：

### 1. 高成本动作不能完全依赖模型判断

报告创建属于有明显成本和副作用的动作，因此采用：

**LLM 负责语义判断 + 确定性规则负责最终保护**

避免模型误判直接创建任务。

### 2. 评测集需要防止过拟合

失败 Case 不会删除，而是冻结进入回归集；修复后除了重新跑原 Case，还会增加独立 Holdout 验证，避免只针对原测试集调规则。

### 3. Scorer 和 Judge 本身也需要被验证

Planning 评测曾因字符串匹配和文本处理问题低估 Planner 能力；Judge Replay 也曾因历史证据保存不完整导致系统性误判。

因此 Harness 不仅关注：

> Agent 是否出错

也关注：

> 评分器是否可信
> 数据是否完整
> 指标是否能被正确解释

### 4. 性能优化以重复验收为准

性能优化过程中，不采用单次最好结果作为结论，而是通过固定输入重复测试和阶段耗时拆分，区分：

* 稳定优化
* 偶发快样本
* 真正瓶颈
* 外部依赖问题

---

## 7. 项目结构

```text
app / backend
    Agent API 与业务逻辑

evals/
    datasets/
    runners/
    scorers/
    planning_eval/
    judge_eval/
    results/
    dashboard/

tests/
    自动化测试

frontend/
    Web 控制台
```

具体目录名称可能根据当前代码版本有所不同，以仓库实际结构为准。

---

## 8. 项目定位

这个项目主要用于展示以下能力：

* Agent 应用设计与工程化
* RAG 与知识增强
* Planning / Memory / Tool Use
* 异步任务系统
* Agent Evaluation Harness
* LLM-as-Judge
* Fuzz / Security Testing
* Tracing / Replay
* CI / Quality Gate
* 性能分析与问题定位

---

## 9. 当前限制

当前项目仍存在以下已知边界：

* Multi-Agent 不是当前默认架构，当前主要采用可控的单 Agent Workflow
* 部分 RAG 评测仍以本地受控数据为主，尚未覆盖大规模向量语料
* Agent Evaluation 结果均为受控测试环境指标，不等同于生产流量表现
* Planning 在多约束、多阶段任务中仍存在部分子目标拆解不完整问题
* 历史评测中缺少完整证据的样本不支持可靠 Replay，会明确标记为 BLOCKED

---

## 10. Why this project

这个项目的核心不是“调用一个大模型生成报告”，而是尝试回答两个更实际的问题：

**如何把 Agent 做成一个可持续运行、可恢复、可追踪的产品？**

以及：

**如何知道这个 Agent 真的变好了，而不是只在 Demo 中看起来更好？**

因此项目同时建设了 Agent 产品链路和 Evaluation Harness，并通过真实失败 Case 不断推动路由、评分、规划和可靠性机制迭代。

