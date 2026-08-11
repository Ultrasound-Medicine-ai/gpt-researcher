# 项目二评测：简历指标与面试讲法

面向「可放进简历的数字」+「能把评测过程讲完整」。

## 一句话定位

> 为研究 Agent SaaS 建了分层评测闭环：cheap 离线护栏（对话/工具/记忆/Fuzz/Perf schema）→ full 抽样 live + Chat P95 → nightly **支柱分账**（SimpleQA topic 分层事实性 / 幻觉全量 70 + risk bucket / 产品 JSONL），指标落盘到看板与回归队列，seed 可复现。

## 抽样分层（支柱内 + 支柱间）

| 支柱 | 抽样方式 | 默认 |
|------|----------|------|
| A 事实 SimpleQA | 按 `metadata.topic` **比例分层**（`--sample-mode stratified`） | n=100, seed=42 |
| B 忠实度幻觉 | 母集仅 70：请求 n≥70 时 **全量**；按 risk_bucket 分桶报告 | effective_n=70 |
| C 产品行为 | dialogue/tool/fuzz/memory JSONL 全量门禁（含 blocked） | 不并入 SimpleQA |

禁止把三支柱合成一个「总准确率」。`--sample-mode random` 保留旧均匀随机行为。

## 面试必补三个数字

### （1）测试规模

| 资产 | 数量 | 说明 |
|------|------|------|
| 产品回归 JSONL | **68** 条（active **65** / blocked **3**） | dialogue+live chat+tool+memory+fuzz+perf+harness |
| cheap 单测（pytest） | **40+** | citation / language / planning / seed+stratified / product JSONL floor / p95 helper |
| SimpleQA 题库 | **4326**（对外质量 **topic 分层 n=100**） | 上游 CSV，seed=42，`sample_mode=stratified` |
| 幻觉查询集 | **70**（对外质量 **全量**） | 上游 jsonl + MAJOR-only judge + risk_bucket |

**面试一句：**「事实用 SimpleQA 按 topic 分层抽 100；幻觉跑全量 70 高风险开放题并分桶；工具/澄清另走产品 JSONL，三支柱分账不混报。」

### （2）门禁耗时（本机实测 / 量级）

| 门禁 | 耗时 | 依据 |
|------|------|------|
| **cheap** | **通常 &lt; 1 分钟**（本机约 **15s**） | `gate_cheap_latest` 各步合计 ≈14.8s |
| **full** | **约 2–5 分钟**（API 正常） | live 调研约 1 分钟级 + live chat + Chat P95≈20s |
| **nightly（n=10）** | **约 20–40 分钟** | SimpleQA×10 + 幻觉×10（看网络/模型） |
| **portfolio 一键（n=10）** | **约 30–60 分钟** | cheap + full + nightly |

**面试一句：**「CI 上的 cheap 一分多钟内就能绿；full 几分钟验真链路；nightly 半小时量级出质量数字。」

### （3）性能指标（P95 门禁）

| 项 | 阈值（门禁） | 本机结果（2026-08-10） |
|----|--------------|------------------------|
| `/api/chat` P95 | **&lt; 8000 ms（8s）** | **≈ 1.6–2.4s PASS**（并发 2–5，n=10） |
| Job 队列 P95 | **&lt; 180s** | **≈ 70s PASS**（并发 2，对齐全局槽位默认） |
| 压测设定 | Chat 并发 **2–5** / Job 并发 **2** | Redis + ARQ 异步 Job，非 Celery |

**面试一句：**「Chat P95 门禁 8 秒，实测约 2 秒；异步研究 Job 端到端 P95 门禁 180 秒，实测约 70 秒。」

## 简历可直接粘贴（中文）

### 标准版（推荐投递）

**项目二 · 研究 Agent 评测体系与发布门禁（GPT-Researcher 二次开发）**  
面向多用户研究 Agent SaaS，独立搭建可复现的分层评测与发布护栏：CI **cheap** 离线门禁（对话意图澄清 / 工具路由 / 记忆槽位 / Fuzz / 引用与语言契约）→ 发版前 **full**（live Chat + 研究 Job）→ 夜间 **nightly** 质量三支柱分账（事实 / 忠实度 / 产品行为，禁止合成「总准确率」）。  
- **规模：** 产品回归 JSONL **68** 条（active **65** / blocked **3**）+ pytest **40+**；事实侧复用 SimpleQA **4326**，对外质量按 topic **分层抽样 n=100**（seed=42）；忠实度侧 **70** 条高风险开放题 **全量**评测并按 risk bucket 分桶。  
- **性能：** `/api/chat` P95 门禁 **&lt;8s**（实测 **≈1.6–2.4s**）；异步研究 Job（Redis + ARQ）端到端 P95 门禁 **&lt;180s**（实测 **≈70s**）。  
- **质量结果：** SimpleQA 分层 n=100 事实 accuracy **≈81.5%**（F1≈0.78）；高风险集 MAJOR 级错误检出率 **≈65.7%**（多源 evidence pack + LLM-as-Judge）。  
- **闭环：** 失败写入回归队列，Fuzz 弱点可晋升为正式用例；已知能力缺口用 blocked 显式隔离。  
*技术栈：Python / pytest / FastAPI / JSONL harness / Redis+ARQ / LLM-as-Judge / CI gate / 指标看板*

### 精简版（一行偏紧）

搭建研究 Agent 分层评测（cheap / full / nightly，三支柱分账）：68 条产品 JSONL；Chat P95&lt;8s（≈2s）、Job P95&lt;180s（≈70s）；SimpleQA topic 分层 n=100 accuracy≈81.5%；高风险幻觉全量 70，MAJOR 检出率≈65.7%；失败 Case 回流可晋升。

### 面试 30 秒版

项目一做产品能力，项目二做可发布护栏：CI cheap 分钟级防回归；发版前验 live Chat 与异步 Job P95；夜间用分层 SimpleQA（n=100）和高风险幻觉全量 70 出质量数字——事实准确率与 MAJOR 检出率分账，不混成一个总准确率；失败进队列可晋升用例。

## 跑出指标（推荐）

环境：`conda activate gptresearcher`（Python ≥ 3.10），API 容器在 `8000` 可选（live chat 用）。

```bash
# 一键 portfolio：默认 SimpleQA topic 分层；幻觉 n≥70 即全量
# 默认 sample seed=42（可用 --seed / EVAL_SAMPLE_SEED 覆盖）
D:\anaconda3\envs\gptresearcher\python.exe evals/run_portfolio.py --num-examples 100 --seed 42 --sample-mode stratified
```

产物：

| 文件 | 内容 |
|------|------|
| `evals/results/portfolio_latest.json` | 全量结构化结果（含 sample_mode / product_strata） |
| `evals/results/PORTFOLIO_METRICS.md` | 简历可用摘要表（A/B/C 分账） |
| `evals/results/simpleqa_latest.json` | accuracy / F1 / strata_counts / cost |
| `evals/results/hallucination_latest.json` | hallucination_rate / by_bucket |
| `evals/results/live_chat_latest.json` | Chat 工具路由抽样 |

成本可控：`EVAL_TOTAL_WORDS=350`（默认）缩短成文；冒烟可用 `--num-examples 3`，对外质量用 **n=100 stratified**。

## 分层门禁（面试时按这个讲）

```text
cheap（每次改代码）
  pytest scorers + harness offline
  + dialogue/tool/memory/fuzz mock
  + perf schema + dashboard 重建
      → 不花钱，防回归

full（发版前 / portfolio）
  harness live 调研抽样
  + /api/chat live（报告意图、澄清、禁误触发）
  + chat P95（API 可用时；jobs 用 EVAL_PERF_JOBS=1）
      → 小额 token，验真链路

nightly / portfolio（质量基准）
  SimpleQA：报告是否答对事实（CORRECT/INCORRECT/NOT_ATTEMPTED → accuracy/F1）
  Hallucination：报告是否忠实于检索上下文（hallucination_rate）
  + dashboard / regression_queue 回流
      → 可写进简历的质量数字
```

## 被测对象怎么对应

| 对象 | 测什么 | 对应套件 |
|------|--------|----------|
| A 调研 Agent | 检索成文、引用、事实、幻觉 | harness + SimpleQA + hallucination |
| B Chat Agent | 意图、工具选择、澄清、拒答 | dialogue/tool cheap + live chat |
| C 记忆/隔离 | 槽位、跨轮、session soft-pass | memory_eval |

## 简历可写指标（以 `PORTFOLIO_METRICS.md` 为准）

从 `evals/results/PORTFOLIO_METRICS.md` 抄最新值。本机 2026-08-10 **n=10** 样例：

- Cheap / full harness / live chat：**PASS**（live chat 3/3）
- Chat P95（live，n=10）：**≈ 1.6–2.4s**（阈值 8s，PASS）
- Job P95（live，并发 2）：**≈ 70s**（阈值 180s，PASS；Redis+ARQ）
- SimpleQA：**accuracy / F1 = 70%**（7/10 CORRECT），成本 ≈ **$0.47**
- Hallucination（MAJOR）：**50%**（5/10；severity: MAJOR 5 / MINOR 1 / NONE 4），成本 ≈ **$0.53**
  - judge=`lite` + **multi-source evidence pack** + 仅计 MAJOR（虚构实体/数字/错误归因）

**表述注意：** 写清 `n`、日期、模型与 judge 设定；勿暗示全量 4k SimpleQA。早期 90% 幻觉率来自 `str(list)` 截断导致 judge 只见 1 篇文档——已修复。

## 面试官常问 → 怎么答

**Q: 你怎么保证 Agent 没乱编？**  
A: 两层——离线 citation/language harness；nightly 用检索上下文做 faithfulness judge，出 hallucination_rate。

**Q: 对话里会不会误开报告任务？**  
A: cheap `tool_eval`/`dialogue_eval` 断言 forbid/must tools；full 再打 live `/api/chat`。

**Q: SSE 这种歧义怎么测？**  
A: `resolve_report_intent` 进 dialogue cheap；期望 `clarify` 而不是直接 create_report。

**Q: 和只跑 SimpleQA 有什么不同？**  
A: 上游 SimpleQA 只覆盖报告事实性；项目二并列加了 Chat 工具链与记忆门禁，并统一 `run_gates`/`run_portfolio`。

**Q: 指标能复现吗？**  
A: case JSONL + `*_latest.json` 落盘；SimpleQA 用本地 CSV；抽样用 `--seed` / `EVAL_SAMPLE_SEED`（默认 42）+ `--sample-mode stratified|random`，结果里带 `sample_seed` / `sample_mode` / `strata_counts`。

**Q: n=100 是随机还是分层？**  
A: 默认 **topic 比例分层**（非均匀随机）；幻觉母集 70 条在 n≥70 时全量跑，并按 risk_bucket 分桶；工具场景不混进 SimpleQA。

## 与开源上游的关系

上游仓库自带 SimpleQA CSV + hallucination 查询集，**没有**对话/工具/记忆支柱。  
本项目：复用上游质量集做 nightly，自建 Project-2 支柱做产品回归。
