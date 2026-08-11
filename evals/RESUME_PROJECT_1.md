# 项目一｜多用户研究 Agent SaaS

**项目背景：** 面向调研与报告生成场景，设计多用户研究 Agent 产品。用户可通过自然语言发起快搜或独立调研任务，系统完成任务规划、检索抓取、报告生成与引用整理，并支持后续追问和报告导出。

**主要工作：**

1. **长任务产品化：** 将 Chat 快搜与长篇调研解耦；Chat 可创建独立 Research Job，后端通过 Redis + ARQ Worker 异步执行。任务状态持久化，支持阶段进度展示、取消、刷新后按 `job_id` 恢复，以及浏览器关闭后继续执行。
2. **可靠任务链路：** 建立“创建任务—PostgreSQL 落库—并发占槽—ARQ 入队—Worker 执行—报告持久化—完成标记”流程；配套 Dispatcher、心跳与 Reaper 处理待调度、僵死任务和槽位回收，并通过幂等键、并发上限与日预算控制资源使用。
3. **知识检索与报告追溯：** 基于 PostgreSQL + pgvector 构建 RAG，支持将上传文档、研究报告、聊天与抓取内容入库；提供 web / local / hybrid 来源策略和知识优先检索。报告采用编号引用并保留来源原文片段，支持 Markdown、PDF、DOCX 导出。
4. **多用户与交互闭环：** 设计 Visitor 与账号体系，按用户隔离 Job、报告、会话与文档，阻止跨用户访问；提交报告前进行意图预检，对歧义问题先澄清再入队。前端以 Next.js + TypeScript 实现 Research / Chat 切换、任务进度、历史报告与多轮追问。
5. **外部能力接入：** 产品支持按需配置多 MCP Server，将外部工具与数据源接入调研链路；对连接方式进行安全约束，默认拒绝用户侧高风险 stdio 配置。

**技术栈：** Next.js、React、TypeScript、Python、FastAPI、PostgreSQL、pgvector、Redis、ARQ、MinIO、MCP、Docker Compose。

---

## 精简版

**多用户研究 Agent SaaS**：设计面向调研与报告生成的全栈产品，将 Chat 快搜与异步 Research Job 解耦；通过 Redis + ARQ 执行长任务，支持刷新恢复与浏览器关闭后继续运行。基于 PostgreSQL + pgvector 持久化文档、报告与对话内容，实现 RAG、按用户数据隔离、意图澄清、MCP 扩展及可核对引用的多格式报告导出。
