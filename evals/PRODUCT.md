# 项目一：多用户研究 Agent SaaS — 完整功能叙述

> 面向简历 / Codex：只描述**当前产品能力**，不使用「二次开发」表述。  
> 与 [PORTFOLIO.md](./PORTFOLIO.md)（项目二评测）成对。  
> Trusted Report Pipeline 默认关闭，下文不作为主路径能力。

---

## 一、产品定位

**多用户研究 Agent SaaS**：用户用自然语言发起调研与追问，系统完成检索、抓取、成文，并产出可导出、可核对引用的研究报告。产品同时提供：

1. **对话通道（Chat）**——快搜、澄清、开独立报告；  
2. **异步调研 Job**——长任务不依赖浏览器长连接，可刷新恢复；  
3. **知识与隔离**——按用户持久化文档/报告向量，Visitor 身份隔离；  
4. **可扩展工具面**——可选 MCP 接入外部工具与数据源。

运行形态（Docker Compose）：PostgreSQL（pgvector）· Redis · MinIO · API（FastAPI）· research-worker（ARQ）· Next.js 前端。

默认主路径：异步 Research Job（HTTP 创建 + 轮询）；WebSocket 启动研究默认关闭。

---

## 二、用户可见功能（完整）

### 2.1 首页与布局

- 首页支持 **Research / Chat** 模式切换。
- 默认 **Copilot** 布局；另有移动端布局与研究详情页。
- 研究偏好保存在浏览器（报告类型、来源、语气、字数、语言、MCP 等）。

### 2.2 异步调研 Job（主调研路径）

用户提交调研任务后：

1. 前端 `POST` 创建 Job；  
2. 约每 1.5s 轮询 Job 状态；  
3. 展示阶段：排队 / 规划 / 检索抓取 / 撰写 / 收尾落库等；  
4. 活跃 Job 写入本地存储，**刷新页面可按 job_id 恢复**；  
5. **关闭浏览器不中断 Worker**；  
6. 支持取消；完成后进入报告页，可继续 Chat 追问。

报告详情页可按 session 观察侧边报告 Job。

### 2.3 Chat（对话）

Chat 具备工具调用能力：

| 工具 | 作用 |
|------|------|
| `quick_search` | 实时 Web 快搜（依赖检索 Key；无 Key 则不可用） |
| `create_research_report` | 创建**独立**异步调研报告（不是把长文直接塞进对话） |

开报告前流程：

1. 确保 Visitor 身份（`/api/auth/me`）；  
2. 意图预检（`/api/research/intent`）——若歧义则先澄清；  
3. 通过后再 `POST /api/jobs/research` 入队。

可按 `session_id` / 报告上下文做多轮追问；报告与聊天内容可进入知识检索范围。

### 2.4 研究设置

| 设置项 | 能力 |
|--------|------|
| 报告类型 | 如 Summary 等短报告路径（另有进阶类型入口，非 SaaS 主叙事可弱化） |
| 研究来源 | `web` / `local` / `hybrid` |
| 语气 | Objective / Formal / Analytical |
| 字数档位 | 如 600 / 1200 / 2500 / 4000 |
| 报告语言 | 中文 / 英文 |
| 域名过滤 | 可选限制检索域名 |
| 文档上传 | 上传到本地文档目录并 **ingest 进 RAG** |
| MCP | 多 Server 配置；默认关闭，按需启用 |
| 布局 | Copilot 等 |

### 2.5 MCP 扩展

- 前端可配置多个 MCP Server（名称、连接方式等）。
- 配置随 Job / 研究请求下发到引擎。
- 安全：默认拒绝用户侧 stdio MCP（防命令执行风险），优先允许 http/sse/websocket 类连接。
- 用途：把外部工具与数据源接入调研链路。

### 2.6 历史与侧栏

- 本地历史 + 服务端按报告 ID 拉取合并。
- 侧栏展示历史调研；研究报告区含问题、正文、来源、日志、导出入口等。

### 2.7 报告导出与引用展示

- 导出：**Markdown / PDF / DOCX**（及资源链接能力）。
- 引用：编号引用 `[n]`；参考文献可带 **原文片段（excerpt）**。
- 中文 PDF 支持嵌入 CJK 字体，避免方框字。

### 2.8 账号（可选）

- 首次可用 Visitor，不强制注册。
- 支持注册 / 登录；登录后可将访客数据迁移到正式账号。
- 登出清理会话身份。

---

## 三、后端与平台能力（完整）

### 3.1 身份与隔离

- 签名 HttpOnly Visitor Cookie。
- 生产环境不信任客户端随意伪造用户头（测试开关除外）。
- Job / Report / Chat / 文档块均按 `user_id`（及 tenant）过滤；**跨用户访问返回不可见/拒绝**。
- 单用户单租户 MVP：`tenant_id` 与用户对齐。

### 3.2 核心 API 面

| 域 | 能力 |
|----|------|
| Health | live / ready（Postgres、Redis、迁移、模型配置等） |
| Auth | me / register / login / logout |
| Chat | 通用聊天；按报告会话聊天；可 ingest |
| Intent | 调研意图预检（proceed / clarify） |
| Jobs | 创建 / 查询 / 取消 / 事件 / 重新调度 |
| Reports | 列表与读写删；Postgres 优先持久化 |
| Upload | 上传、列表、删除；触发 RAG ingest |
| WS | 仍保留；**默认禁止用 WS 启动研究** |

创建 Job 依赖 Redis + 数据库就绪；否则拒绝并提示基础设施不可用。

### 3.3 异步 Job 引擎（可靠性）

完整链路：

```
创建 Job → PG 落库 → 占并发槽 → ARQ 入队
  → Worker 执行（规划→检索→抓取→成文）
  → 先持久化报告/来源 → 再标记 completed
```

配套机制：

- **Dispatcher**：认领 `pending_dispatch` 并入队（防丢调度）；  
- **Reaper**：回收僵死 Job、释放槽位；  
- **心跳 / stale** 检测；  
- **幂等键**：同用户重复提交可去重；  
- **并发槽**：每用户 / 全局上限；超限 **429** + Retry-After；  
- **日预算 / 单 Job 资源上限**（搜索次数、LLM 次数、字数等，可配）；  
- 入队失败保持待调度，由 Dispatcher 恢复，而非直接失败；  
- 完成后将报告与来源片段 ingest，供后续 Chat RAG。

### 3.4 RAG / 知识库

- 模型：Document / DocumentChunk（父子分块 + pgvector embedding）。
- Ingest 来源：上传文件、研究报告、聊天、抓取内容等。
- 检索：向量检索 + 过滤；可重排；组装上下文。
- Web 证据包：可结构化沉淀 Web 证据。
- **知识策略**：
  - UI 来源：`web` / `local` / `hybrid`；  
  - Chat 开报告默认倾向 **`local_first`**（先本地/知识库，时效不足或证据不足再 Web）；  
  - 仅历史报告块不足以支撑「纯本地」时会 fail-open 到 Web，避免空报告。
- 上传安全：体积与数量上限。
- 检索 Key：支持多 Key 池轮换（如 Tavily）。
- MinIO：可选对象存储，产物按租户前缀隔离。

### 3.5 意图澄清

- 基于用户近期报告标题、聊天信号与任务文本做规划提示。
- 对歧义缩写（典型：**SSE** = Server-Sent Events vs 上交所）在弱上下文时返回 **clarify**（选项/追问）。
- 已消歧或上下文足够则 **proceed**。
- 前端开报告前调用；服务端亦有安全网，避免卡死入队。

### 3.6 安全加固（产品级）

- SSRF：过滤不安全的 source/document URL。  
- MCP：拒绝危险的用户 stdio 配置（可配例外）。  
- 密码：注册使用哈希存储。  
- 访客→注册的数据迁移覆盖 sessions / jobs / documents / chunks 等。

### 3.7 研究引擎能力（产品内贯通）

- 规划子问题 → 多路检索 → 网页/文档抓取 → 整合 → 成文。  
- 与 Job 参数打通：来源策略、知识策略、MCP、规划提示、字数、语言、语气、域名过滤等。

---

## 四、明确「有但非默认主路径」的能力

写简历/对外叙述时建议弱化或注明默认关闭：

| 项 | 说明 |
|----|------|
| Trusted Report Pipeline | 代码存在，**默认关闭** |
| WebSocket 启动研究 | 默认关闭，主路径为 HTTP Job |
| 进程内 Job 回退 | 非完整 SaaS 部署用，Compose 默认关 |
| MCP | **产品支持**，UI 默认关，用户开启后生效 |
| Multi-Agents / Deep Research / HumanFeedback UI | 仓库或 UI 残留入口，**不是**异步 Job SaaS 主卖点 |
| 图片生成 | 默认关 |
| Discord bot 等 | Compose profile，非默认栈 |

---

## 五、简历可用浓缩版（无「二次开发」）

**项目一 · 多用户研究 Agent SaaS**  
面向调研与报告生成，提供可多用户使用的研究 Agent 产品：对话与长任务解耦，知识可持久化，报告可导出可核对。  
- **双通道：** Chat 支持快搜与创建独立调研报告；长任务经 Redis + ARQ Worker 异步执行，关浏览器可继续，刷新按 `job_id` 恢复。  
- **知识与检索：** PostgreSQL + pgvector；上传/报告/聊天可入库；支持 web / local / hybrid，开报告默认知识优先（`local_first`）。  
- **MCP：** 可配置多 Server，将外部工具与数据源接入调研链路（按需启用，连接方式做安全约束）。  
- **意图与隔离：** 歧义缩写提交前澄清；Visitor / 账号身份隔离，禁止跨用户访问 Job 与报告。  
- **交付：** 编号引用 + 原文片段；导出 Markdown / PDF / DOCX（中文 PDF 支持 CJK）；健康检查与并发/日预算门禁。  
*技术栈：Next.js / TypeScript / FastAPI / PostgreSQL+pgvector / Redis+ARQ / MCP / MinIO / Docker*

---

## 六、面试 60 秒版（功能向）

这是一个研究 Agent SaaS：用户可以在对话里快搜，也可以一键开一条异步调研任务；任务在 Worker 里跑，关页、刷新都能续上。文档和报告会进 Postgres/pgvector，后续追问可以知识库优先再补网上资料。设置里能配 MCP 接外部工具。碰到像 SSE 这种歧义词会先问清楚再开跑。用户数据按身份隔离。报告带编号引用和原文片段，并支持导出 Word/PDF。评测与发布门禁在项目二单独做。
