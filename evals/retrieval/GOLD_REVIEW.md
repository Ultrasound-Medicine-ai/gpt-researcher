# Retrieval Gold Candidate Review

状态：20 条均为 `unreviewed_candidate`，不是正式 Gold。划分使用 `seed=42`；Holdout 不参与后续参数调整。

## ret-cand-001

- Query：Redis Sentinel 与 Cluster 分别解决什么高可用问题？
- Query Type：exact_keyword
- Split：holdout_candidate
- Candidate Parent：`95ecede2-62fb-472a-9336-377e1baf2887`
- Candidate Child：`56a3328a-9fb7-4f58-a63f-6558fcc36368`
- 对应原文：Cluster 与 Sentinel 实现自动分片与故障转移，并对应不同规模的高可用部署。
- [ ] Query是否合理
- [ ] Relevant Child是否正确
- [ ] 是否遗漏其他Relevant Child
- 人工备注：

## ret-cand-002

- Query：Redis 的 RDB 与 AOF 如何在恢复速度和数据安全之间取舍？
- Query Type：exact_keyword
- Split：main_candidate
- Candidate Parent：`a7ce79f8-a6ac-4e14-a43c-d072a596331f`
- Candidate Child：`86e847c8-39ac-4db0-bcca-82f09da230b9`
- 对应原文：RDB 适合灾难恢复与备份，AOF 提供更高数据安全性，两者可以独立或混合使用。
- [ ] Query是否合理
- [ ] Relevant Child是否正确
- [ ] 是否遗漏其他Relevant Child
- 人工备注：

## ret-cand-003

- Query：Pydantic v2、Starlette 和 Uvicorn 在 FastAPI 技术栈中各承担什么职责？
- Query Type：exact_keyword
- Split：main_candidate
- Candidate Parent：`70c6b596-64b7-409f-ba3e-27c358ae180e`
- Candidate Child：`c27b33ba-5843-4e16-ab14-f5e3ba581533`
- 对应原文：Pydantic 负责验证与序列化，Starlette 提供 ASGI 基础能力，Uvicorn/Hypercorn 提供服务器实现。
- [ ] Query是否合理
- [ ] Relevant Child是否正确
- [ ] 是否遗漏其他Relevant Child
- 人工备注：

## ret-cand-004

- Query：FastAPI 最小示例应如何安装、编写入口并用 Uvicorn 启动？
- Query Type：exact_keyword
- Split：holdout_candidate
- Candidate Parent：`0e55d2d4-5530-4562-b089-8dac816a9ffa`
- Candidate Child：`c491b5d4-2703-42af-b6e6-9ee5c22dcd6b`
- 对应原文：安装 fastapi/uvicorn，创建 main.py 路由，再执行 `uvicorn main:app --reload`。
- [ ] Query是否合理
- [ ] Relevant Child是否正确
- [ ] 是否遗漏其他Relevant Child
- 人工备注：

## ret-cand-005

- Query：SortedSet 与 GeoHash 分别适合实现哪些实时业务？
- Query Type：exact_keyword
- Split：main_candidate
- Candidate Parent：`5120803d-df6f-429a-bef5-9f9ab9e91897`
- Candidate Child：`6cd5fc86-a472-49ca-979b-48f058a8cf6a`
- 对应原文：SortedSet 用于实时排行榜；GeoHash 支持附近的人和周边门店检索。
- [ ] Query是否合理
- [ ] Relevant Child是否正确
- [ ] 是否遗漏其他Relevant Child
- 人工备注：

## ret-cand-006

- Query：为什么内存优先的数据存储可以同时改善响应时间并降低基础设施成本？
- Query Type：semantic_paraphrase
- Split：main_candidate
- Candidate Parent：`463aafd4-c38c-4bf3-9825-e2910ea55ccd`
- Candidate Child：`fc94b007-c26e-4d89-8e57-0b7dcb6a4c34`
- 对应原文：Redis 的亚毫秒延迟提升吞吐量，并减少流量与服务器实例数量。
- [ ] Query是否合理
- [ ] Relevant Child是否正确
- [ ] 是否遗漏其他Relevant Child
- 人工备注：

## ret-cand-007

- Query：哪种 Python API 框架适合高并发 AI 后端，并能依靠类型注解自动校验请求？
- Query Type：semantic_paraphrase
- Split：main_candidate
- Candidate Parent：`bc05ed81-6312-42aa-93b9-e5f81c15a0d4`、`70c6b596-64b7-409f-ba3e-27c358ae180e`
- Candidate Child：`d4db5fca-4e84-43ef-8582-3280a8f4eaf1`、`c27b33ba-5843-4e16-ab14-f5e3ba581533`
- 对应原文：FastAPI 适用于微服务和 AI/LLM 接口，支持异步及类型注解驱动的请求校验。
- [ ] Query是否合理
- [ ] Relevant Child是否正确
- [ ] 是否遗漏其他Relevant Child
- 人工备注：

## ret-cand-008

- Query：轻量任务分发与超大规模日志流应分别选择 Redis 还是 Kafka？
- Query Type：semantic_paraphrase
- Split：holdout_candidate
- Candidate Parent：`c2833832-2b7e-4727-95e4-0434c3c71c16`、`d3d031b6-3f67-4383-bfa5-97fc0f8070b6`
- Candidate Child：`17a28b48-54f1-4800-a05c-984f06a47f4f`、`bb05e34c-8730-4e02-a9ce-801f65fe94ff`
- 对应原文：Redis 适合轻量队列和实时推送；超大规模日志流更适合 Kafka 等专业组件。
- [ ] Query是否合理
- [ ] Relevant Child是否正确
- [ ] 是否遗漏其他Relevant Child
- 人工备注：

## ret-cand-009

- Query：需要处理延时任务和百万级消息推送时，Redis 提供了哪些数据结构？
- Query Type：semantic_paraphrase
- Split：holdout_candidate
- Candidate Parent：`d3d031b6-3f67-4383-bfa5-97fc0f8070b6`
- Candidate Child：`bb05e34c-8730-4e02-a9ce-801f65fe94ff`
- 对应原文：List 可用于异步任务与延时调度；Stream 支持高峰消息流与实时消费。
- [ ] Query是否合理
- [ ] Relevant Child是否正确
- [ ] 是否遗漏其他Relevant Child
- 人工备注：

## ret-cand-010

- Query：团队在 FastAPI 与 Django REST Framework 之间选型时，应如何权衡性能、学习成本和生态完整性？
- Query Type：semantic_paraphrase
- Split：main_candidate
- Candidate Parent：`35ffb936-91a1-4933-8967-7b90502b91f3`
- Candidate Child：`47195385-ab4d-474f-87d1-2ee0f571cf3f`
- 对应原文：FastAPI 异步原生且适合高性能 API；DRF 学习概念更多但具有 Django 全栈生态。
- [ ] Query是否合理
- [ ] Relevant Child是否正确
- [ ] 是否遗漏其他Relevant Child
- 人工备注：

## ret-cand-011

- Query：Redis 参考资料如何同时支撑 BSD 商业合规和降低应用运行成本的论点？
- Query Type：cross_chunk_boundary
- Split：main_candidate
- Candidate Parent：`6c73ff0b-df2d-449c-b428-0d3dcd1f761f`
- Candidate Child：`377fedf6-0abd-430d-b55e-7e683d679776`、`47dbb13d-e291-4108-84d3-f6814c04fad2`
- 对应原文：两个连续引用 Child 覆盖 BSD 再发布条件、IBM 成本收益和后续运维材料。
- [ ] Query是否合理
- [ ] Relevant Child是否正确
- [ ] 是否遗漏其他Relevant Child
- 人工备注：

## ret-cand-012

- Query：FastAPI 入门材料中，社区教程与官方 First Steps 文档如何衔接？
- Query Type：cross_chunk_boundary
- Split：main_candidate
- Candidate Parent：`fe9f1cac-5faf-470a-84c6-4d6aa3ef8cd1`
- Candidate Child：`fb05715e-9232-494a-b89e-6d3d5f18de51`、`13006bf2-5efa-4c83-be5d-be6221d48080`
- 对应原文：连续引用片段先列社区教程，再进入 fastapi.tiangolo.com 官方 First Steps。
- [ ] Query是否合理
- [ ] Relevant Child是否正确
- [ ] 是否遗漏其他Relevant Child
- 人工备注：

## ret-cand-013

- Query：哪些相邻证据分别支持 FastAPI 官方入门能力和 2026 年与 DRF 的框架比较？
- Query Type：cross_chunk_boundary
- Split：main_candidate
- Candidate Parent：`fe9f1cac-5faf-470a-84c6-4d6aa3ef8cd1`
- Candidate Child：`13006bf2-5efa-4c83-be5d-be6221d48080`、`46650f72-0274-4df1-9f06-9ca6f29d62e6`
- 对应原文：前一 Child 包含官方教程，后一 Child 包含 FastAPI/DRF 2026 对比资料。
- [ ] Query是否合理
- [ ] Relevant Child是否正确
- [ ] 是否遗漏其他Relevant Child
- 人工备注：

## ret-cand-014

- Query：Redis 的安装运维资料与 List/Stream 消息场景证据为何需要跨相邻片段读取？
- Query Type：cross_chunk_boundary
- Split：main_candidate
- Candidate Parent：`6c73ff0b-df2d-449c-b428-0d3dcd1f761f`
- Candidate Child：`377fedf6-0abd-430d-b55e-7e683d679776`、`47dbb13d-e291-4108-84d3-f6814c04fad2`
- 对应原文：第一段结尾讨论 Redis/RDM 安装，下一段延续来源并引出 List/Stream 场景。
- [ ] Query是否合理
- [ ] Relevant Child是否正确
- [ ] 是否遗漏其他Relevant Child
- 人工备注：

## ret-cand-015

- Query：从官方教程过渡到第三方性能比较时，需要联合查看哪两个 FastAPI 引用片段？
- Query Type：cross_chunk_boundary
- Split：main_candidate
- Candidate Parent：`fe9f1cac-5faf-470a-84c6-4d6aa3ef8cd1`
- Candidate Child：`13006bf2-5efa-4c83-be5d-be6221d48080`、`46650f72-0274-4df1-9f06-9ca6f29d62e6`
- 对应原文：相邻 Child 分别覆盖官方教程和外部性能、框架比较资料。
- [ ] Query是否合理
- [ ] Relevant Child是否正确
- [ ] 是否遗漏其他Relevant Child
- 人工备注：

## ret-cand-016

- Query：Redis 从单线程执行与持久化机制，如何进一步演进到自动故障转移和分片？
- Query Type：multi_section_synthesis
- Split：main_candidate
- Candidate Parent：`a7ce79f8-a6ac-4e14-a43c-d072a596331f`、`95ecede2-62fb-472a-9336-377e1baf2887`
- Candidate Child：`86e847c8-39ac-4db0-bcca-82f09da230b9`、`56a3328a-9fb7-4f58-a63f-6558fcc36368`
- 对应原文：架构章节说明事件模型和 RDB/AOF；高可用章节说明 Sentinel、Cluster 和故障转移。
- [ ] Query是否合理
- [ ] Relevant Child是否正确
- [ ] 是否遗漏其他Relevant Child
- 人工备注：

## ret-cand-017

- Query：Redis 如何分别支撑热点缓存、异步消息和实时地理排行榜三类业务？
- Query Type：multi_section_synthesis
- Split：holdout_candidate
- Candidate Parent：`af98a992-001d-4d01-98f0-f35fe08449ee`、`d3d031b6-3f67-4383-bfa5-97fc0f8070b6`、`5120803d-df6f-429a-bef5-9f9ab9e91897`
- Candidate Child：`e7129dd9-cb4e-44eb-a512-759186db242f`、`bb05e34c-8730-4e02-a9ce-801f65fe94ff`、`6cd5fc86-a472-49ca-979b-48f058a8cf6a`
- 对应原文：三个章节分别覆盖热点缓存、List/Stream 消息处理、SortedSet 排行榜及 GeoHash 地理检索。
- [ ] Query是否合理
- [ ] Relevant Child是否正确
- [ ] 是否遗漏其他Relevant Child
- 人工备注：

## ret-cand-018

- Query：FastAPI 的底层组件、自动校验能力和最小启动流程如何组成完整开发路径？
- Query Type：multi_section_synthesis
- Split：main_candidate
- Candidate Parent：`70c6b596-64b7-409f-ba3e-27c358ae180e`、`0e55d2d4-5530-4562-b089-8dac816a9ffa`
- Candidate Child：`c27b33ba-5843-4e16-ab14-f5e3ba581533`、`c491b5d4-2703-42af-b6e6-9ee5c22dcd6b`
- 对应原文：架构章节介绍 Pydantic/Starlette/Uvicorn；示例章节给出安装、路由和启动命令。
- [ ] Query是否合理
- [ ] Relevant Child是否正确
- [ ] 是否遗漏其他Relevant Child
- 人工备注：

## ret-cand-019

- Query：为什么 FastAPI 适合轻量高并发接口，而 DRF 更适合依赖 Django 全栈生态的项目？
- Query Type：multi_section_synthesis
- Split：main_candidate
- Candidate Parent：`bc05ed81-6312-42aa-93b9-e5f81c15a0d4`、`35ffb936-91a1-4933-8967-7b90502b91f3`
- Candidate Child：`d4db5fca-4e84-43ef-8582-3280a8f4eaf1`、`47195385-ab4d-474f-87d1-2ee0f571cf3f`
- 对应原文：概述章节定位 FastAPI 为轻量 API 框架；对比章节讨论异步性能、学习曲线与 Django 生态。
- [ ] Query是否合理
- [ ] Relevant Child是否正确
- [ ] 是否遗漏其他Relevant Child
- 人工备注：

## ret-cand-020

- Query：请综合说明 Redis 的数据结构能力、持久化选择以及高可用部署模式。
- Query Type：multi_section_synthesis
- Split：main_candidate
- Candidate Parent：`be446464-3cdc-4737-9680-41d39c7a452a`、`a7ce79f8-a6ac-4e14-a43c-d072a596331f`、`95ecede2-62fb-472a-9336-377e1baf2887`
- Candidate Child：`5f1949f0-f2b6-48c4-91a0-c0bfc0f5fb5c`、`86e847c8-39ac-4db0-bcca-82f09da230b9`、`56a3328a-9fb7-4f58-a63f-6558fcc36368`
- 对应原文：三个章节分别覆盖 Redis 数据结构、RDB/AOF 和主从/Sentinel/Cluster 高可用模式。
- [ ] Query是否合理
- [ ] Relevant Child是否正确
- [ ] 是否遗漏其他Relevant Child
- 人工备注：
