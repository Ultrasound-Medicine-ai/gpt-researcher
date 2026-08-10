# 异步 ResearchJob Docker E2E 验收报告

- 日期：2026-08-09
- 环境：Windows + Docker Desktop，Python 3.12 容器
- 被测链路：API → PostgreSQL → Redis/ARQ → 独立 Worker → 报告持久化 → 静态附件
- 测试 Job：`50c9c4c6-47cf-4210-a154-da26bbe275b4`
- 测试 Session：`58e36203-cb94-415a-9d01-021ca551cdb7`

## 结论

异步报告主链路通过本轮上线前 E2E：数据库迁移、API、Redis、Worker 均正常；任务在客户端不保持连接时继续执行；按 `job_id` 可恢复；API 重启不影响 Worker；报告先写入 PostgreSQL，再将 Job 标记为 `completed`。

本轮同时发现并修复了三项容器部署问题：宿主机数据库变量污染容器连接、Worker 输出目录未挂载共享卷、中文 PDF 缺少 CJK 字体。

## 健康检查

`GET /health/ready` 返回 HTTP 200：

| 检查项 | 结果 | 证据 |
|---|---|---|
| PostgreSQL | PASS | `ok` |
| Redis | PASS | `ok` |
| Alembic migration | PASS | revision `001` |
| ARQ queue | PASS | `ok` |
| 独立 Worker | PASS | Worker 启动并注册 `run_research_job` |

## 四项 E2E

| 验收项 | 结果 | 实测证据 |
|---|---|---|
| 关浏览器后任务继续 | PASS | 提交后不维持 SSE/WS 或轮询连接，Job 仍从 `queued` 推进到 `running/researching/writing/finalizing/completed` |
| 刷新后按 `job_id` 恢复 | PASS | 使用同一 `job_id` 重新 GET，返回原 Session、状态、阶段、心跳和结果 |
| API 重启不影响 Worker | PASS | Job 运行时执行 API 容器重启；重启后 `/health/ready` 为 200，原 Job 心跳继续更新并最终完成 |
| 报告保存成功才 completed | PASS | Report `timestamp=1786248410385`；Job `finished_at=1786248410428`，报告比完成状态早约 43ms；checkpoint 含 `report_persisted=true` |

Job 实际运行约 169 秒，`attempt=1`，最终 `status=completed`，报告正文长度 11,443 字符，引用来源 8 个。

## 附件验收

首轮发现 Worker 从 `/usr/src/app/backend` 启动，导致相对路径 `outputs/` 写入容器临时层，API 和宿主机无法读取。已将 ARQ 启动目录改为 `/usr/src/app`，使其写入共享挂载 `/usr/src/app/outputs`。

修复后恢复并验证以下文件：

| 文件 | 大小 | HTTP |
|---|---:|---:|
| Markdown | 11,443 bytes | 200 |
| PDF | 416,367 bytes，6 页 | 200 |
| DOCX | 42,329 bytes | 200 |

中文 PDF 已嵌入 `Noto Sans CJK` 字体，字体检查结果为 `cjk_font=true`。

## 自动化测试

在一次性 Python 3.12 测试容器中执行：

- `tests/test_async_research_jobs.py`
- `tests/test_job_enqueue_policy.py`
- `tests/test_research_job_reliability.py`

结果：`50 passed`，耗时 0.76 秒。存在一个 pytest 配置项版本告警，不影响测试结果。

## 本轮修复

1. Docker 构建上下文由约 500MB 降到 24.74MB，并排除 `.env`、前端缓存、运行时输出和本地虚拟环境。
2. Alembic/健康检查支持把旧 `postgresql+psycopg2://` 归一化为 `postgresql+psycopg://`；异步 API 归一化为 `postgresql+asyncpg://`。
3. Compose 使用 `DOCKER_DATABASE_URL` / `DOCKER_REDIS_URL`，避免宿主机 `localhost` 连接串泄漏到容器网络。
4. Worker 从应用根目录启动，报告附件进入 API/Worker 共享输出卷。
5. 镜像加入 `fonts-noto-cjk`，修复中文 PDF 方框字。

## 剩余观察项

1. 测试请求设置 `total_words=300`，但报告正文仍达到 11,443 字符；长度约束当前不是硬限制，会增加延迟和模型额度消耗。
2. `max_search_results=2` 最终得到 8 个来源，说明该参数可能按查询而非整场任务限制，需要明确口径并增加总量上限。
3. Job 完成后 `status=completed`，但 `stage` 保留为 `finalizing`；不影响当前 UI 终态判断，但建议统一为明确的终态阶段。
4. 本轮直接 HTTP E2E 的中文任务在 Windows PowerShell 提交端显示为问号；浏览器 JSON 请求应为 UTF-8，仍建议补一条前端中文烟测。

## 发布判断

异步 Job 基础可靠性门禁：**PASS**。

建议下一步优先增加“报告字数/搜索总量硬预算”，然后再做并发、取消、超时和僵尸任务压测；否则大模型切换和额度轮换只能提高可用性，不能解决单份报告过长导致的慢与贵。
