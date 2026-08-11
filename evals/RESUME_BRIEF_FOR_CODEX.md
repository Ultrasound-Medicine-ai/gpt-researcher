# 给 Codex 写简历用的项目说明书（项目一 + 项目二）

> 用途：把本文完整贴给 Codex，请它生成中文简历条目。  
> 两个项目是**同一产品的不同职责**：项目一 = 产品能力；项目二 = 评测 / 发布门禁 / 质量指标。  
> **对照基线**：开源能力快照在 `F:\agent\gpt-researcher - 副本`；当前实现在 `F:\agent\gpt-researcher`。  
> 简历**不要**用「二次开发」当项目标签；能力归属以目录 diff 为准（见 `evals/PRODUCT.md`）。

---

## 写简历时的硬约束（必须遵守）

1. **不要**把项目一、二合成一个项目；保持两个独立项目条目。
2. **项目一标题/首句不要写「二次开发」**；写「研究 Agent SaaS / 产品工程化」等。可在技术栈或面试里提引擎来源，但不作简历主标签。
3. **要写 MCP，但归属要诚实**：MCP UI/核心在开源基线副本中已存在（`MCPSelector.tsx` 与现网哈希一致）；简历写「支持 MCP 接入」，**不要**写成你从零实现 MCP。
4. **不要**写「Trusted Pipeline / 可信成文管线已上线」。默认关闭，主叙事禁止写。
5. **不要**写 Celery；异步队列是 **Redis + ARQ**。
6. **不要**写具体云厂商/内部算力品牌名；评测侧写 **LLM-as-Judge（多模型评估）** 即可。
7. **不要**把质量三支柱合成「总准确率 / overall accuracy」。
8. 幻觉数字必须写成 **「MAJOR 级错误检出率」**；**不要**写成「模型幻觉率 65.7%」。
9. SimpleQA：**基准集 4326**；对外质量 **topic 分层 n=100（seed=42）**。
10. 产品 JSONL：**68 条（active 65 / blocked 3）**。
11. 性能数字主放项目二；项目一可轻量复用 Chat/Job P95。
12. 语气：偏工程落地与可验证指标；避免空话堆砌。

---

# 项目一：多用户研究 Agent SaaS（产品）

## 1. 项目定位（以 diff 为准，禁止臆测「原项目痛点」）

打造**可多用户使用的研究 Agent SaaS**。  
开源基线（副本）已有：WebSocket 调研、Chat、MCP、上游 SimpleQA/幻觉评测、基础 Compose。  
你相对基线补齐的主线：异步可恢复 Job、Visitor 隔离、Postgres/pgvector/RAG、意图澄清、Chat 开独立报告、Worker/基础设施等。

**不要**在没对照基线时写「原项目只有一次性长连接」等绝对化句子；应写「补齐异步 Job / 隔离 / RAG 持久化」这类可核对增量。

## 2. 你实际做了什么（能力清单）

### 2.1 双通道：Chat + 独立 Research Job
- **Chat（`/api/chat`）**：短问答、快搜（`quick_search`）、以及工具调用「创建独立调研报告」（`create_research_report`）。
- **Research Job**：长任务异步执行，不依赖浏览器保持长连接。
- 前端可按 `job_id` / session **刷新恢复**（localStorage 存活跃 Job）。

### 2.2 异步可靠性（Redis + ARQ）
- API 入队 → Redis/ARQ → 独立 Worker 执行研究与成文 → 报告落库/落盘 → Job 标记 completed。
- 已验收能力（E2E）：
  - 关浏览器后任务继续跑；
  - 刷新后按 job_id 恢复状态；
  - API 重启不影响 Worker 在途任务；
  - **先持久化报告，再标记 completed**。
- 无 Redis 时可降级（进程内回退），完整 SaaS 路径走 Compose：Postgres / Redis / Worker。

### 2.3 多用户 / 访客隔离
- Visitor Cookie 身份（签名 token）；
- Job / 报告带 `user_id` / `tenant_id`；
- **跨用户读取 Job 被拒绝**（有 release gate 单测覆盖）。

### 2.4 检索与知识（RAG / 来源策略）
- PostgreSQL + **pgvector**：研究抓取分块向量化，供后续 Chat/报告检索增强；
- 来源策略：`web` / `local` / `hybrid`；
- 默认知识策略倾向 **`local_first`**（本地/知识库优先，时效不足再补 Web）；
- 检索侧有 **Tavily API Key 池轮换**，缓解单 key 额度打尽。

### 2.5 MCP 扩展（基线已有，可写「支持」）
- 开源基线已有 `MCPSelector` + `gpt_researcher/mcp`（与现网 UI 文件哈希一致）；
- 现网 Job/WS 继续下发 `mcp_enabled` / `mcp_configs` / `mcp_strategy`；
- 简历：写产品支持 MCP；勿写「我实现了 MCP」。

### 2.6 意图澄清（产品行为）
- 提交报告任务前可做意图解析（`resolve_report_intent`）；
- 典型：用户说「调研 SSE」且上下文弱 → **先澄清**（技术 SSE vs 上交所），而不是直接开错报告；
- 已消歧（如写明 Server-Sent Events）则可直接 proceed。

### 2.7 报告可追溯（主路径，可写）
- 确定性 **编号引用** `[n]`；
- 参考文献带 **原文片段**（excerpt），便于核对「引用是否对得上」；
- 导出 **Markdown / PDF / DOCX**；中文 PDF 嵌入 CJK 字体。

### 2.8 明确不要写进项目一主叙事
- Trusted Report Pipeline：**默认关闭，未作为线上主路径**。
- 「二次开发」字样：不要当标题/首句。
- LangGraph Multi-Agents：非主卖点时可省略；**MCP 要写**。

## 3. 技术栈（项目一）

- 前端：Next.js、React、TypeScript、Tailwind
- 后端：Python、FastAPI、WebSocket（进度/日志可选）+ HTTP 轮询 Job
- 数据与队列：PostgreSQL、pgvector、Redis、ARQ、MinIO（可选）
- 扩展：MCP（多 Server 配置接入外部工具/数据源）
- 研究引擎：规划子问题 → 检索 → 抓取 → 成文（含 MCP 可选增强）
- 部署：Docker Compose（API + Worker + 依赖服务）
- 检索：Tavily 等（可写「Web 检索 + Key 轮换」）

## 4. 可写性能佐证（与项目二同源实测）

- Chat P95 ≈ **1.6–2.4s**（门禁 &lt;8s）
- 短研究 Job 端到端 P95 ≈ **70s**（门禁 &lt;180s；压测并发对齐全局槽位，约 2）

## 5. 建议简历强调的「为什么难 / 为什么有价值」

- 把同步长连接调研改成 **可恢复异步 Job**（产品可用性）；
- Chat 工具与长任务边界清晰（快搜 vs 开报告）；
- 多用户隔离 + 任务归属；
- 歧义意图防误触发；
- 引用可核对（编号 + 原文片段）。

## 6. 项目一推荐标题

- `多用户研究 Agent SaaS`
- 或 `研究型 AI Agent：异步任务 / RAG / MCP / 多用户隔离`

---

# 项目二：研究 Agent 评测体系与发布门禁

## 1. 项目定位

为**项目一同一套产品**搭建可复现的分层评测与发布护栏，回答三个问题：
1. 改代码会不会把对话/工具/记忆搞坏？（cheap）
2. 发版前 live 链路与延迟是否达标？（full + P95）
3. 报告事实性与忠实度如何、能否复现？（nightly / portfolio，三支柱分账）

上游开源评测偏「研究报告质量」；项目二补齐 **对话 / 工具链 / 记忆 / Fuzz / Perf / 看板回流**。

## 2. 分层门禁（cheap / full / nightly）

| 层 | 目的 | 内容概要 | 耗时量级 |
|----|------|----------|----------|
| **cheap** | CI / 合并前护栏，尽量不烧 token | pytest + harness offline + dialogue/tool/memory/fuzz mock + perf schema + dashboard | 通常 &lt;1min（本机约 15s） |
| **full** | 发版前验真 | live 研究抽样、live chat、Chat/Job P95 | 约 2–5 min（API 正常） |
| **nightly / portfolio** | 出质量数字 | SimpleQA + 幻觉评测 + 产品 JSONL 汇总 | n=10 约 20–40min；n=100 过夜级 |

入口脚本：`evals/run_gates.py`、`evals/run_portfolio.py`。

## 3. 质量「三支柱分账」（禁止合成总准确率）

### A — 事实性（SimpleQA）
- 基准集：**4326** samples（上游 CSV）
- 对外质量：按 `metadata.topic` **比例分层抽样 n=100**，`seed=42`，`sample_mode=stratified`
- 结果（已跑完）：**accuracy ≈ 81.5%**，F1 ≈ 0.78，correct_rate 75%（100 graded）
- 面试口径：约八成事实答对（在分层样本上），不是「全库 4326 都测了」

### B — 忠实度 / 幻觉（Hallucination）
- 集合：**70** 条人工构造高风险开放题（非「模型随机抽题」）
- 请求 n≥70 时 **全量**跑完（effective_n=70）
- Judge：多源 evidence pack + **MAJOR-only** + **LLM-as-Judge**
- 结果：**MAJOR 级错误检出率 ≈ 65.7%**（46/70）
- 按 risk_bucket 分桶报告（如 fresh_news / howto_technical / pricing_compare 等）
- **正确表述**：在高难度忠实度集合上，评测系统能检出 MAJOR 不忠实；**不是**「产品有 65.7% 幻觉」

### C — 产品行为（自建 JSONL）
- 支柱：dialogue / tool / memory / fuzz / perf / harness / live chat
- 规模：**68** 条（**65** active / **3** blocked）
- blocked 显式隔离已知未交付能力（如 chat 内 PDF 知识库检索未上线）
- cheap 为 mock/契约测试（意图澄清、工具选择、禁工具、超时降级、记忆槽位、Fuzz ASR/指代）

另有 pytest **40+**（引用、语言、planning、分层抽样、产品用例底线、p95 helper 等）。

## 4. 性能门禁（可写数字）

| 项 | 门禁阈值 | 实测 |
|----|----------|------|
| `/api/chat` P95 | &lt; 8s | ≈ 1.6–2.4s PASS |
| 研究 Job 端到端 P95 | &lt; 180s | ≈ 70s PASS |
| 压测设定 | Chat 并发 2–5；Job 并发 2 | 对齐全局并发槽位 |

## 5. 失败闭环 / 可观测

- Dashboard：`DASHBOARD.md` / `dashboard.html` / `trace_index.json`
- `regression_queue.jsonl`：失败与弱点回流
- Fuzz → `weaknesses.jsonl` → promote 晋升为正式用例
- 抽样可复现：`--seed` / `EVAL_SAMPLE_SEED`（默认 42）

## 6. 技术栈（项目二）

Python、pytest、JSONL harness、FastAPI 契约评测、Redis+ARQ（Perf/Job）、LLM-as-Judge、CI cheap gate、指标看板脚本。

## 7. 项目二推荐标题

- `研究 Agent 评测体系与发布门禁`
- 或 `Agent 全链路分层评测（对话/工具/记忆/事实/忠实度/性能）`

## 8. 面试 30 秒串联（两项目关系）

项目一做产品：异步可恢复调研、Chat 工具、RAG、隔离、澄清、引用。  
项目二做可发布：CI cheap 防回归；发版前验 live 与 P95；夜间用分层 SimpleQA（n=100）与高风险幻觉全量 70 出质量数字，事实与 MAJOR 检出分账，失败进队列可晋升。

---

# 给 Codex 的生成指令（可原样附加）

请根据上文，生成：

1. **项目一**标准简历条目（标题 + 1 句背景 + 4–6 条 bullet + 技术栈一行）
2. **项目二**标准简历条目（同上，必须含可核实数字）
3. 各给一个 **精简版**（2–4 行）
4. 各给一个 **面试 30 秒口述稿**

要求：
- 中文；偏校招/社招后端或 LLM 应用工程师风格
- 数字必须与上文一致，不得编造 DAU、准确率提升百分比等未给出的指标
- 项目一禁止写「二次开发」标签；要写 MCP；禁止写 Trusted Pipeline 已上线
- 项目二禁止合成总准确率；幻觉写 MAJOR 检出率
- 输出直接可粘贴进简历，不要额外解释过程
