# Retrieval Gold 80 V2 人工审核

> 前 20 条为不可修改的 Frozen Pilot Gold；candidate-021 至 candidate-080 为重新生成的 Evidence-first Candidate。
> 旧版 60 条 Candidate 保留在 `retrieval_gold_candidates_80.jsonl` 作为 failed draft，本文件不复用其证据。
> 新 Candidate 只使用已人工审核的正文 Evidence，并仍需逐条人工确认；不得用于正式 Recall/MRR。

## pilot-001
- 状态：Frozen Pilot Gold
- Query：浏览器通过 SSE 断线重连时，服务端和客户端依靠哪些事件字段恢复消息位置？
- Query Type：exact_keyword
- Topic Group / Proposed Split：`sse` / `holdout`
- Relevant Parent：`2df4c511-b356-406e-bf69-ec32a60a0df0`
- Relevant Child：`7bd73b02-717e-434d-81a1-e4ba85440a91`
- 对应原文 1：SSE 使用 text/event-stream，事件包含 data、event、id，并通过 Last-Event-ID 与自动重连恢复数据流。
- 标注理由：该 Child 集中定义 SSE 事件格式、连接方式和断线恢复机制。
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- 人工备注：

## pilot-002
- 状态：Frozen Pilot Gold
- Query：生产环境配置 HPA 时，需要重点设置哪些参数，CPU 目标利用率通常处于什么区间？
- Query Type：exact_keyword
- Topic Group / Proposed Split：`hpa_vpa` / `main`
- Relevant Parent：`c8bc8370-b646-4176-9a5a-d8ecacd5a481`
- Relevant Child：`a7b8d05f-5168-418f-aa73-423eebe6ad1d`
- 对应原文 1：HPA 目标 CPU 利用率通常为 60%～80%，同时需要设置最小/最大副本数和扩缩容冷却时间。
- 标注理由：该 Child 唯一同时包含三个 HPA 生产配置参数。
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- 人工备注：

## pilot-003
- 状态：Frozen Pilot Gold
- Query：VPA 的 Off、Initial、Auto 三种模式分别会不会自动修改现有 Pod？
- Query Type：exact_keyword
- Topic Group / Proposed Split：`hpa_vpa` / `main`
- Relevant Parent：`dc8d324b-3112-44ad-8899-d2ff73ac3142`
- Relevant Child：`0253321d-f9a4-4121-bdce-58fd767991bc`
- 对应原文 1：Off 仅提供建议，Initial 只作用于新 Pod，Auto 会自动更新配置但可能触发 Pod 重启。
- 标注理由：该 Child 明确定义 VPA 三种模式及其更新行为。
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- 人工备注：

## pilot-004
- 状态：Frozen Pilot Gold
- Query：用 Redis 建库存锁时，如何用随机标识、NX 和 PX 组合成一条原子加锁命令？
- Query Type：exact_keyword
- Topic Group / Proposed Split：`redis_lock` / `main`
- Relevant Parent：`16b311ed-3ce5-4de2-8588-b436fd9ca99e`
- Relevant Child：`dbbd479f-7ba9-4f4c-88cd-ae95be7b084b`
- 对应原文 1：示例使用 SET lock:stock:1001 random-value NX PX 30000；NX 保证不存在时写入，PX 设置过期时间。
- 标注理由：该 Child 包含完整原子命令、随机 value 和过期参数语义。
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- 人工备注：

## pilot-005
- 状态：Frozen Pilot Gold
- Query：Cache-Aside、Read-Through 与 Write-Through 的数据读写责任分别落在哪一层？
- Query Type：exact_keyword
- Topic Group / Proposed Split：`cache_patterns` / `main`
- Relevant Parent：`cab0e2c7-7d80-4184-b184-4d6b198fb6e4`
- Relevant Child：`4637bbd5-b09f-4552-9b54-c8f5cf012e33`、`c64e20e7-7125-402e-bb71-c7f016f02aee`
- 对应原文 1：Cache-Aside 由应用读取数据库并填充缓存；Read-Through 和 Write-Through 将读取或写入责任交给缓存抽象层。
- 标注理由：两个连续 Child 分别定义 Cache-Aside 以及 Read/Write-Through，缺一无法完成比较。
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- 人工备注：

## pilot-006
- 状态：Frozen Pilot Gold
- Query：业务只需要服务器持续推送文本通知时，为什么 SSE 往往比 WebSocket 更省实现成本？
- Query Type：semantic_paraphrase
- Topic Group / Proposed Split：`sse` / `holdout`
- Relevant Parent：`69e43496-0751-4f64-a371-e815f63bc9f6`、`faddb4f2-2482-485b-b7ba-99a1787ad79c`
- Relevant Child：`6ef6dedc-f0d5-474f-886d-939ecf564ad5`、`0fb1b787-3f59-43d0-9f35-5303da075c85`
- 对应原文 1：SSE 复用 HTTP 基础设施且无需帧解析和心跳，适合单向文本推送；双向指令或二进制流仍需 WebSocket。
- 标注理由：优势 Child 与限制 Child 共同支持适用前提和不适用边界。
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- 人工备注：

## pilot-007
- 状态：Frozen Pilot Gold
- Query：同时启用水平和垂直扩缩容时，为什么都盯着 CPU 会造成抖动，应怎样拆分指标？
- Query Type：semantic_paraphrase
- Topic Group / Proposed Split：`hpa_vpa` / `main`
- Relevant Parent：`eefff46b-4abc-4400-88fb-a705b8a8c182`
- Relevant Child：`c6f3e1f8-cfc5-4b56-852c-a778864d99e1`
- 对应原文 1：VPA 修改单 Pod CPU 请求会影响 HPA 的副本计算；建议 HPA 基于 CPU、VPA 基于内存等不同指标。
- 标注理由：该 Child 直接解释冲突因果及分离指标的协调方案。
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- 人工备注：

## pilot-008
- 状态：Frozen Pilot Gold
- Query：为什么 FastAPI 能减少接口参数错误，同时保持适合高并发后端的执行模型？
- Query Type：semantic_paraphrase
- Topic Group / Proposed Split：`fastapi` / `holdout`
- Relevant Parent：`817487ad-38d1-456d-8c36-1000e15365f9`、`64f9e670-272a-4ac0-9735-fc9837bb0147`
- Relevant Child：`a19f034a-ab26-4f53-97be-7a7b28cc6f52`、`3e7aa036-d7eb-4d93-ba6e-ea98f6847a57`
- 对应原文 1：FastAPI 以 Starlette 处理异步请求、Pydantic 执行数据验证；ASGI 架构和严格类型校验提升并发与开发可靠性。
- 标注理由：架构与性能位于两个 Parent，联合解释异步执行和错误减少。
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- 人工备注：

## pilot-009
- 状态：Frozen Pilot Gold
- Query：某个热 Key 流量突然集中并导致缓存击穿时，可以从哪些方向降低数据库压力？
- Query Type：semantic_paraphrase
- Topic Group / Proposed Split：`redis_hot_key` / `main`
- Relevant Parent：`8562f1c8-f1d3-42e8-b19c-3c4c4e392854`
- Relevant Child：`e6f7faf0-07a5-4412-936d-b4e94b20f1bc`、`9c38c6cb-d7b6-471f-9c28-2727544858ac`
- 对应原文 1：热 Key 会造成分片 CPU/带宽倾斜与缓存击穿；可拆分数据、采用本地缓存，并设计限流、熔断和降级。
- 标注理由：问题没有复用原文术语，两个连续 Child 分别覆盖风险与缓解措施。
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- 人工备注：

## pilot-010
- 状态：Frozen Pilot Gold
- Query：Redis 没有依赖多工作线程仍能获得高吞吐，关键的软件和 I/O 设计是什么？
- Query Type：semantic_paraphrase
- Topic Group / Proposed Split：`redis_architecture` / `main`
- Relevant Parent：`e454c186-fb75-4945-bc2e-d6f3894bd350`、`9808e98b-f72e-4664-95aa-097801d12443`、`d0168209-76ff-4454-9405-95db5110c49d`
- Relevant Child：`d4121f65-aaf7-4e4e-b49f-9f08cee13d7f`、`7bce1e61-ee7d-479b-916a-4853022919de`、`990c8e05-be6a-4808-90e4-bfad6a98da21`
- 对应原文 1：纯内存、非阻塞 I/O、epoll 多路复用和单线程事件模型减少锁竞争及上下文切换。
- 标注理由：三个 Parent 分别解释执行原理、I/O 多路复用和避免锁/切换开销。
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- 人工备注：

## pilot-011
- 状态：Frozen Pilot Gold
- Query：从用户感知到数值区间，怎样判断网络延迟是否会影响游戏、视频会议和网页浏览？
- Query Type：cross_chunk_boundary
- Topic Group / Proposed Split：`network_performance` / `holdout`
- Relevant Parent：`4312929b-2b65-4b3b-9780-f372774352fc`
- Relevant Child：`3e63533d-7343-49c9-9144-c09d06483e12`、`bbf08b13-d43d-4b9b-97fd-ae471cf73df2`、`1faa2ec4-de5a-42eb-837e-526305a00b04`
- 对应原文 1：连续片段先解释毫秒延迟对交互体验的影响，再给出良好延迟标准及游戏、通话、浏览和视频的体验分级。
- 标注理由：阈值说明与不同业务体验表跨越三个连续 Child，单一 Child 无法完整回答。
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- 人工备注：

## pilot-012
- 状态：Frozen Pilot Gold
- Query：排查网络卡顿时，网页测速、ping、traceroute 和 iPerf 分别适合观察哪些网络现象？
- Query Type：cross_chunk_boundary
- Topic Group / Proposed Split：`network_performance` / `holdout`
- Relevant Parent：`b868aae6-1c92-43e7-ba9c-c2a17d78e9fe`
- Relevant Child：`6349368f-8faa-4806-ad0c-478b263a24bb`、`0b71d03e-c66a-4fdf-8039-e679f6772ed7`、`81429dc4-9796-4dac-97e7-e98a8d0baf90`
- 对应原文 1：网页测速提供连接基线；traceroute 展示各跳路径；持续链路工具观察丢包；iPerf 测试局域网设备间吞吐。
- 标注理由：工具定位能力分布在同 Parent 的三个连续 Child。
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- 人工备注：

## pilot-013
- 状态：Frozen Pilot Gold
- Query：一次缓存读取到一次同步写入，Cache-Aside、Read-Through 和 Write-Through 的完整流程有什么差别？
- Query Type：cross_chunk_boundary
- Topic Group / Proposed Split：`cache_patterns` / `main`
- Relevant Parent：`cab0e2c7-7d80-4184-b184-4d6b198fb6e4`
- Relevant Child：`4637bbd5-b09f-4552-9b54-c8f5cf012e33`、`c64e20e7-7125-402e-bb71-c7f016f02aee`、`b2cf4ad2-19d5-4a62-aaa1-0f06834642ce`
- 对应原文 1：三个连续片段依次说明旁路缓存读取、Read-Through 责任转移、Write-Through 同步写入及更新顺序问题。
- 标注理由：问题要求完整读写流程，相关定义和写入分析跨三个 Child。
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- 人工备注：

## pilot-014
- 状态：Frozen Pilot Gold
- Query：采用“先更新数据库再删缓存”后，极端并发仍可能怎样读到旧值，又如何用 binlog 和重试收敛？
- Query Type：cross_chunk_boundary
- Topic Group / Proposed Split：`cache_consistency` / `main`
- Relevant Parent：`1dca64e0-586d-48b8-85ef-ee3485a637f9`
- Relevant Child：`f0e4adc6-83b1-47c9-8aee-df5b578c16bf`、`126e7851-9146-4c9b-a8b3-a6ad0f674eec`、`da4c9ffd-140f-4491-aebf-606ec2dc737e`
- 对应原文 1：连续片段覆盖写库删缓存方案、读写线程交错产生旧缓存的小概率窗口，以及 Canal 订阅 binlog、消息队列重试删除。
- 标注理由：异常窗口、概率分析和最终一致补偿分别位于三个连续 Child。
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- 人工备注：

## pilot-015
- 状态：Frozen Pilot Gold
- Query：热 Key 从压垮单分片到击穿数据库的链路是什么，如何治理并提前发现？
- Query Type：cross_chunk_boundary
- Topic Group / Proposed Split：`redis_hot_key` / `main`
- Relevant Parent：`8562f1c8-f1d3-42e8-b19c-3c4c4e392854`
- Relevant Child：`e6f7faf0-07a5-4412-936d-b4e94b20f1bc`、`9c38c6cb-d7b6-471f-9c28-2727544858ac`、`5715943c-d7f0-4545-a9d7-1e69e6d348b7`
- 对应原文 1：三个连续片段依次描述分片资源倾斜和缓存击穿、拆分/降级与抓包统计，以及通过节点 CPU、带宽告警发现热点。
- 标注理由：风险、治理、检测分布在同 Parent 的三个 Child，必须联合标注。
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- 人工备注：

## pilot-016
- 状态：Frozen Pilot Gold
- Query：生产集群应如何分别配置 HPA 与 VPA，并避免两套控制器互相干扰？
- Query Type：multi_parent_synthesis
- Topic Group / Proposed Split：`hpa_vpa` / `main`
- Relevant Parent：`6f5603fe-c213-4aa7-aab4-71807769d72e`、`29a841de-29c4-4cef-a505-5538c4fc6c7f`、`eefff46b-4abc-4400-88fb-a705b8a8c182`、`c8bc8370-b646-4176-9a5a-d8ecacd5a481`、`dc8d324b-3112-44ad-8899-d2ff73ac3142`
- Relevant Child：`5a84c9fe-d0e2-4b60-b663-0fd823840284`、`4ce5d77d-cc81-406f-b23e-2bdf244edd18`、`c6f3e1f8-cfc5-4b56-852c-a778864d99e1`、`a7b8d05f-5168-418f-aa73-423eebe6ad1d`、`0253321d-f9a4-4121-bdce-58fd767991bc`
- 对应原文 1：HPA 调整副本，VPA 调整资源请求；生产配置还涉及指标隔离、CPU 阈值、冷却时间和 VPA 更新模式。
- 标注理由：任务横跨 HPA、VPA、冲突协调和两套配置共五个 Parent。
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- 人工备注：

## pilot-017
- 状态：Frozen Pilot Gold
- Query：从底层组件到工程收益，FastAPI 为什么适合作为机器学习服务的 API 层？
- Query Type：multi_parent_synthesis
- Topic Group / Proposed Split：`fastapi` / `holdout`
- Relevant Parent：`817487ad-38d1-456d-8c36-1000e15365f9`、`64f9e670-272a-4ac0-9735-fc9837bb0147`、`a9043b59-b8a7-4227-8e70-8051ddd51f22`、`156b220b-cf6f-4986-804e-73754954e741`
- Relevant Child：`a19f034a-ab26-4f53-97be-7a7b28cc6f52`、`3e7aa036-d7eb-4d93-ba6e-ea98f6847a57`、`af997fce-c3ce-442b-accd-dc790211fbc9`、`275e9feb-ebf1-46c6-8bf4-9199244f2136`
- 对应原文 1：Starlette/Pydantic 提供异步和校验，ASGI 带来高并发，OpenAPI 自动化降低联调成本，应用章节明确覆盖模型部署。
- 标注理由：架构、性能、标准化和应用场景位于四个不同 Parent。
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- 人工备注：

## pilot-018
- 状态：Frozen Pilot Gold
- Query：设计实时文本推送方案时，应怎样结合 SSE 的协议机制、替代方案、典型用途与局限做选型？
- Query Type：multi_parent_synthesis
- Topic Group / Proposed Split：`sse` / `holdout`
- Relevant Parent：`2df4c511-b356-406e-bf69-ec32a60a0df0`、`bbc63975-1526-4f56-b6e4-73002fd85513`、`d629c5af-47b9-4eca-9cbf-3cd9e07941b8`、`faddb4f2-2482-485b-b7ba-99a1787ad79c`
- Relevant Child：`7bd73b02-717e-434d-81a1-e4ba85440a91`、`3400f795-6752-47a1-819c-fc33f6733ef7`、`21f27a0c-c30a-4396-acd1-0e62088da327`、`0fb1b787-3f59-43d0-9f35-5303da075c85`
- 对应原文 1：四个章节分别说明 SSE 事件流协议、与 WebSocket/长轮询比较、AI/监控等场景，以及单向、兼容性和二进制限制。
- 标注理由：完整选型需要协议、比较、场景和限制四个 Parent。
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- 人工备注：

## pilot-019
- 状态：Frozen Pilot Gold
- Query：请从数据能力、单机性能、I/O/事件模型和高可用机制解释 Redis 的核心技术特点。
- Query Type：multi_parent_synthesis
- Topic Group / Proposed Split：`redis_architecture` / `main`
- Relevant Parent：`7628aa83-d4c2-4678-83b0-9e19001f9906`、`0abf7d70-2bff-4be9-be89-10f7f08d29e6`、`9808e98b-f72e-4664-95aa-097801d12443`、`e454c186-fb75-4945-bc2e-d6f3894bd350`
- Relevant Child：`1a763fce-c3ae-4b78-aff5-d2473ef3805e`、`45d707dc-27c2-4db0-ad7c-c7f7f6dbc432`、`7bce1e61-ee7d-479b-916a-4853022919de`、`d4121f65-aaf7-4e4e-b49f-9f08cee13d7f`
- 对应原文 1：Redis 支持多种数据结构、持久化和高可用；基准展示读写吞吐；非阻塞 I/O、多路复用和单线程事件模型解释性能来源。
- 标注理由：能力、基准、I/O 和内部原理来自四个 Parent。
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- 人工备注：

## pilot-020
- 状态：Frozen Pilot Gold
- Query：一个可用于生产的 Redis 分布式锁，需要同时满足哪些语义并处理超时和节点故障？
- Query Type：multi_parent_synthesis
- Topic Group / Proposed Split：`redis_lock` / `main`
- Relevant Parent：`81a99a66-19a8-4f48-a65e-2e53d2d22e51`、`16b311ed-3ce5-4de2-8588-b436fd9ca99e`、`9e0cf715-ea15-49ea-8142-d0464d6e9b70`、`fc889dc3-14f0-482a-9fe7-25fc15e92ca6`
- Relevant Child：`3751880e-f729-4df3-824e-dffb38f97fbe`、`dbbd479f-7ba9-4f4c-88cd-ae95be7b084b`、`1fa17e4e-8f23-4d54-8049-430f999fbb0e`、`e6dd8ca0-f495-4e6f-af0a-e85d1e3dd6e6`
- 对应原文 1：锁需要互斥、高可用、防死锁与可重入；SET NX PX 完成原子加锁；Watch Dog 处理提前过期；集群、哨兵或 Redlock 应对单点故障。
- 标注理由：需求、原子实现、超时续约和节点故障分别位于四个 Parent。
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- [x] Frozen，不可修改
- 人工备注：

## candidate-021
- 状态：Candidate / 待人工审核
- Query：SSE 断线后，Last-Event-ID 需要和事件里的哪个字段配合才能续传？
- Query Type：exact_keyword
- Topic Group / Proposed Split：`sse` / `holdout`
- Relevant Parent：`2df4c511-b356-406e-bf69-ec32a60a0df0`
- Relevant Child：`7bd73b02-717e-434d-81a1-e4ba85440a91`
- 对应原文 1：SSE 使用 text/event-stream，事件包含 data、event、id，并通过 Last-Event-ID 与自动重连恢复数据流。
- 标注理由：Evidence-first：仅复用 frozen pilot-001 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-022
- 状态：Candidate / 待人工审核
- Query：text/event-stream 的 data、event、id 三个字段中，哪个用于标记消息位置？
- Query Type：exact_keyword
- Topic Group / Proposed Split：`sse` / `holdout`
- Relevant Parent：`2df4c511-b356-406e-bf69-ec32a60a0df0`
- Relevant Child：`7bd73b02-717e-434d-81a1-e4ba85440a91`
- 对应原文 1：SSE 使用 text/event-stream，事件包含 data、event、id，并通过 Last-Event-ID 与自动重连恢复数据流。
- 标注理由：Evidence-first：仅复用 frozen pilot-001 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-023
- 状态：Candidate / 待人工审核
- Query：EventSource 自动重连时，服务端怎样知道应该从哪条 SSE 消息继续发送？
- Query Type：exact_keyword
- Topic Group / Proposed Split：`sse` / `holdout`
- Relevant Parent：`2df4c511-b356-406e-bf69-ec32a60a0df0`
- Relevant Child：`7bd73b02-717e-434d-81a1-e4ba85440a91`
- 对应原文 1：SSE 使用 text/event-stream，事件包含 data、event、id，并通过 Last-Event-ID 与自动重连恢复数据流。
- 标注理由：Evidence-first：仅复用 frozen pilot-001 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-024
- 状态：Candidate / 待人工审核
- Query：HPA 的 target CPU utilization 在生产环境通常设置在什么区间？
- Query Type：exact_keyword
- Topic Group / Proposed Split：`hpa_vpa` / `main`
- Relevant Parent：`c8bc8370-b646-4176-9a5a-d8ecacd5a481`
- Relevant Child：`a7b8d05f-5168-418f-aa73-423eebe6ad1d`
- 对应原文 1：HPA 目标 CPU 利用率通常为 60%～80%，同时需要设置最小/最大副本数和扩缩容冷却时间。
- 标注理由：Evidence-first：仅复用 frozen pilot-002 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-025
- 状态：Candidate / 待人工审核
- Query：HPA 除了 minReplicas 和 maxReplicas 外，哪个时间参数用于避免频繁扩缩容？
- Query Type：exact_keyword
- Topic Group / Proposed Split：`hpa_vpa` / `main`
- Relevant Parent：`c8bc8370-b646-4176-9a5a-d8ecacd5a481`
- Relevant Child：`a7b8d05f-5168-418f-aa73-423eebe6ad1d`
- 对应原文 1：HPA 目标 CPU 利用率通常为 60%～80%，同时需要设置最小/最大副本数和扩缩容冷却时间。
- 标注理由：Evidence-first：仅复用 frozen pilot-002 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-026
- 状态：Candidate / 待人工审核
- Query：配置 HPA 时，目标 CPU 利用率、副本边界和冷却时间分别解决什么问题？
- Query Type：exact_keyword
- Topic Group / Proposed Split：`hpa_vpa` / `main`
- Relevant Parent：`c8bc8370-b646-4176-9a5a-d8ecacd5a481`
- Relevant Child：`a7b8d05f-5168-418f-aa73-423eebe6ad1d`
- 对应原文 1：HPA 目标 CPU 利用率通常为 60%～80%，同时需要设置最小/最大副本数和扩缩容冷却时间。
- 标注理由：Evidence-first：仅复用 frozen pilot-002 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-027
- 状态：Candidate / 待人工审核
- Query：VPA 的 Off、Initial、Auto 三种 updateMode 对已有 Pod 的影响有什么区别？
- Query Type：exact_keyword
- Topic Group / Proposed Split：`hpa_vpa` / `main`
- Relevant Parent：`dc8d324b-3112-44ad-8899-d2ff73ac3142`
- Relevant Child：`0253321d-f9a4-4121-bdce-58fd767991bc`
- 对应原文 1：Off 仅提供建议，Initial 只作用于新 Pod，Auto 会自动更新配置但可能触发 Pod 重启。
- 标注理由：Evidence-first：仅复用 frozen pilot-003 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-028
- 状态：Candidate / 待人工审核
- Query：VPA 的 Initial 模式为何不会回头修改正在运行的 Pod？
- Query Type：exact_keyword
- Topic Group / Proposed Split：`hpa_vpa` / `main`
- Relevant Parent：`dc8d324b-3112-44ad-8899-d2ff73ac3142`
- Relevant Child：`0253321d-f9a4-4121-bdce-58fd767991bc`
- 对应原文 1：Off 仅提供建议，Initial 只作用于新 Pod，Auto 会自动更新配置但可能触发 Pod 重启。
- 标注理由：Evidence-first：仅复用 frozen pilot-003 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-029
- 状态：Candidate / 待人工审核
- Query：VPA 设为 Auto 后，资源建议落地时为什么可能触发 Pod 重启？
- Query Type：exact_keyword
- Topic Group / Proposed Split：`hpa_vpa` / `main`
- Relevant Parent：`dc8d324b-3112-44ad-8899-d2ff73ac3142`
- Relevant Child：`0253321d-f9a4-4121-bdce-58fd767991bc`
- 对应原文 1：Off 仅提供建议，Initial 只作用于新 Pod，Auto 会自动更新配置但可能触发 Pod 重启。
- 标注理由：Evidence-first：仅复用 frozen pilot-003 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-030
- 状态：Candidate / 待人工审核
- Query：Redis 加库存锁时，SET lock:stock:1001 random-value NX PX 30000 中 NX 和 PX 分别保证什么？
- Query Type：exact_keyword
- Topic Group / Proposed Split：`redis_lock` / `main`
- Relevant Parent：`16b311ed-3ce5-4de2-8588-b436fd9ca99e`
- Relevant Child：`dbbd479f-7ba9-4f4c-88cd-ae95be7b084b`
- 对应原文 1：示例使用 SET lock:stock:1001 random-value NX PX 30000；NX 保证不存在时写入，PX 设置过期时间。
- 标注理由：Evidence-first：仅复用 frozen pilot-004 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-031
- 状态：Candidate / 待人工审核
- Query：同一条 Redis SET 命令同时带 NX 与 PX 时，这两个参数分别表达什么语义？
- Query Type：exact_keyword
- Topic Group / Proposed Split：`redis_lock` / `main`
- Relevant Parent：`16b311ed-3ce5-4de2-8588-b436fd9ca99e`
- Relevant Child：`dbbd479f-7ba9-4f4c-88cd-ae95be7b084b`
- 对应原文 1：示例使用 SET lock:stock:1001 random-value NX PX 30000；NX 保证不存在时写入，PX 设置过期时间。
- 标注理由：Evidence-first：仅复用 frozen pilot-004 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-032
- 状态：Candidate / 待人工审核
- Query：Redis 原子加锁示例中，lock key、random-value、NX 和 PX 30000 分别是什么组成部分？
- Query Type：exact_keyword
- Topic Group / Proposed Split：`redis_lock` / `main`
- Relevant Parent：`16b311ed-3ce5-4de2-8588-b436fd9ca99e`
- Relevant Child：`dbbd479f-7ba9-4f4c-88cd-ae95be7b084b`
- 对应原文 1：示例使用 SET lock:stock:1001 random-value NX PX 30000；NX 保证不存在时写入，PX 设置过期时间。
- 标注理由：Evidence-first：仅复用 frozen pilot-004 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-033
- 状态：Candidate / 待人工审核
- Query：Cache-Aside 发生缓存未命中时，应用层和数据库各负责哪一步？
- Query Type：exact_keyword
- Topic Group / Proposed Split：`cache_patterns` / `main`
- Relevant Parent：`cab0e2c7-7d80-4184-b184-4d6b198fb6e4`
- Relevant Child：`4637bbd5-b09f-4552-9b54-c8f5cf012e33`、`c64e20e7-7125-402e-bb71-c7f016f02aee`
- 对应原文 1：Cache-Aside 由应用读取数据库并填充缓存；Read-Through 和 Write-Through 将读取或写入责任交给缓存抽象层。
- 标注理由：Evidence-first：仅复用 frozen pilot-005 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-034
- 状态：Candidate / 待人工审核
- Query：Read-Through 与 Write-Through 把读取或写入责任从应用转移到了哪里？
- Query Type：exact_keyword
- Topic Group / Proposed Split：`cache_patterns` / `main`
- Relevant Parent：`cab0e2c7-7d80-4184-b184-4d6b198fb6e4`
- Relevant Child：`4637bbd5-b09f-4552-9b54-c8f5cf012e33`、`c64e20e7-7125-402e-bb71-c7f016f02aee`
- 对应原文 1：Cache-Aside 由应用读取数据库并填充缓存；Read-Through 和 Write-Through 将读取或写入责任交给缓存抽象层。
- 标注理由：Evidence-first：仅复用 frozen pilot-005 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-035
- 状态：Candidate / 待人工审核
- Query：对 Cache-Aside、Read-Through、Write-Through 而言，谁负责填充缓存和同步写入？
- Query Type：exact_keyword
- Topic Group / Proposed Split：`cache_patterns` / `main`
- Relevant Parent：`cab0e2c7-7d80-4184-b184-4d6b198fb6e4`
- Relevant Child：`4637bbd5-b09f-4552-9b54-c8f5cf012e33`、`c64e20e7-7125-402e-bb71-c7f016f02aee`
- 对应原文 1：Cache-Aside 由应用读取数据库并填充缓存；Read-Through 和 Write-Through 将读取或写入责任交给缓存抽象层。
- 标注理由：Evidence-first：仅复用 frozen pilot-005 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-036
- 状态：Candidate / 待人工审核
- Query：浏览器只接收服务端文本通知且不需要回传指令时，为什么会优先考虑 SSE，何时改用 WebSocket？
- Query Type：semantic_paraphrase
- Topic Group / Proposed Split：`sse` / `holdout`
- Relevant Parent：`69e43496-0751-4f64-a371-e815f63bc9f6`、`faddb4f2-2482-485b-b7ba-99a1787ad79c`
- Relevant Child：`6ef6dedc-f0d5-474f-886d-939ecf564ad5`、`0fb1b787-3f59-43d0-9f35-5303da075c85`
- 对应原文 1：SSE 复用 HTTP 基础设施且无需帧解析和心跳，适合单向文本推送；双向指令或二进制流仍需 WebSocket。
- 标注理由：Evidence-first：仅复用 frozen pilot-006 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-037
- 状态：Candidate / 待人工审核
- Query：单向消息流复用 HTTP 时，SSE 相比 WebSocket 少了哪些协议处理负担？
- Query Type：semantic_paraphrase
- Topic Group / Proposed Split：`sse` / `holdout`
- Relevant Parent：`69e43496-0751-4f64-a371-e815f63bc9f6`、`faddb4f2-2482-485b-b7ba-99a1787ad79c`
- Relevant Child：`6ef6dedc-f0d5-474f-886d-939ecf564ad5`、`0fb1b787-3f59-43d0-9f35-5303da075c85`
- 对应原文 1：SSE 复用 HTTP 基础设施且无需帧解析和心跳，适合单向文本推送；双向指令或二进制流仍需 WebSocket。
- 标注理由：Evidence-first：仅复用 frozen pilot-006 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-038
- 状态：Candidate / 待人工审核
- Query：如果需求变成双向命令或二进制数据，原先的 SSE 方案为什么不再合适？
- Query Type：semantic_paraphrase
- Topic Group / Proposed Split：`sse` / `holdout`
- Relevant Parent：`69e43496-0751-4f64-a371-e815f63bc9f6`、`faddb4f2-2482-485b-b7ba-99a1787ad79c`
- Relevant Child：`6ef6dedc-f0d5-474f-886d-939ecf564ad5`、`0fb1b787-3f59-43d0-9f35-5303da075c85`
- 对应原文 1：SSE 复用 HTTP 基础设施且无需帧解析和心跳，适合单向文本推送；双向指令或二进制流仍需 WebSocket。
- 标注理由：Evidence-first：仅复用 frozen pilot-006 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-039
- 状态：Candidate / 待人工审核
- Query：VPA 提高单 Pod 的 CPU request 后，为什么可能让 HPA 的副本计算来回波动？
- Query Type：semantic_paraphrase
- Topic Group / Proposed Split：`hpa_vpa` / `main`
- Relevant Parent：`eefff46b-4abc-4400-88fb-a705b8a8c182`
- Relevant Child：`c6f3e1f8-cfc5-4b56-852c-a778864d99e1`
- 对应原文 1：VPA 修改单 Pod CPU 请求会影响 HPA 的副本计算；建议 HPA 基于 CPU、VPA 基于内存等不同指标。
- 标注理由：Evidence-first：仅复用 frozen pilot-007 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-040
- 状态：Candidate / 待人工审核
- Query：让 HPA 看 CPU、VPA 看内存，怎样减少两个 autoscaler 相互干扰？
- Query Type：semantic_paraphrase
- Topic Group / Proposed Split：`hpa_vpa` / `main`
- Relevant Parent：`eefff46b-4abc-4400-88fb-a705b8a8c182`
- Relevant Child：`c6f3e1f8-cfc5-4b56-852c-a778864d99e1`
- 对应原文 1：VPA 修改单 Pod CPU 请求会影响 HPA 的副本计算；建议 HPA 基于 CPU、VPA 基于内存等不同指标。
- 标注理由：Evidence-first：仅复用 frozen pilot-007 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-041
- 状态：Candidate / 待人工审核
- Query：同一个 CPU 指标被 HPA 和 VPA 同时驱动时，配置为什么容易不稳定？
- Query Type：semantic_paraphrase
- Topic Group / Proposed Split：`hpa_vpa` / `main`
- Relevant Parent：`eefff46b-4abc-4400-88fb-a705b8a8c182`
- Relevant Child：`c6f3e1f8-cfc5-4b56-852c-a778864d99e1`
- 对应原文 1：VPA 修改单 Pod CPU 请求会影响 HPA 的副本计算；建议 HPA 基于 CPU、VPA 基于内存等不同指标。
- 标注理由：Evidence-first：仅复用 frozen pilot-007 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-042
- 状态：Candidate / 待人工审核
- Query：FastAPI 如何借助 Starlette 和 Pydantic 同时处理异步请求与入参校验？
- Query Type：semantic_paraphrase
- Topic Group / Proposed Split：`fastapi` / `holdout`
- Relevant Parent：`817487ad-38d1-456d-8c36-1000e15365f9`、`64f9e670-272a-4ac0-9735-fc9837bb0147`
- Relevant Child：`a19f034a-ab26-4f53-97be-7a7b28cc6f52`、`3e7aa036-d7eb-4d93-ba6e-ea98f6847a57`
- 对应原文 1：FastAPI 以 Starlette 处理异步请求、Pydantic 执行数据验证；ASGI 架构和严格类型校验提升并发与开发可靠性。
- 标注理由：Evidence-first：仅复用 frozen pilot-008 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-043
- 状态：Candidate / 待人工审核
- Query：ASGI 执行模型配合严格类型验证，为什么适合并发 API 服务？
- Query Type：semantic_paraphrase
- Topic Group / Proposed Split：`fastapi` / `holdout`
- Relevant Parent：`817487ad-38d1-456d-8c36-1000e15365f9`、`64f9e670-272a-4ac0-9735-fc9837bb0147`
- Relevant Child：`a19f034a-ab26-4f53-97be-7a7b28cc6f52`、`3e7aa036-d7eb-4d93-ba6e-ea98f6847a57`
- 对应原文 1：FastAPI 以 Starlette 处理异步请求、Pydantic 执行数据验证；ASGI 架构和严格类型校验提升并发与开发可靠性。
- 标注理由：Evidence-first：仅复用 frozen pilot-008 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-044
- 状态：Candidate / 待人工审核
- Query：为模型推理接口选择 FastAPI 时，异步底座和数据验证各解决了什么工程问题？
- Query Type：semantic_paraphrase
- Topic Group / Proposed Split：`fastapi` / `holdout`
- Relevant Parent：`817487ad-38d1-456d-8c36-1000e15365f9`、`64f9e670-272a-4ac0-9735-fc9837bb0147`
- Relevant Child：`a19f034a-ab26-4f53-97be-7a7b28cc6f52`、`3e7aa036-d7eb-4d93-ba6e-ea98f6847a57`
- 对应原文 1：FastAPI 以 Starlette 处理异步请求、Pydantic 执行数据验证；ASGI 架构和严格类型校验提升并发与开发可靠性。
- 标注理由：Evidence-first：仅复用 frozen pilot-008 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-045
- 状态：Candidate / 待人工审核
- Query：单个热 Key 为什么会先挤占分片 CPU、带宽，随后把压力传到数据库？
- Query Type：semantic_paraphrase
- Topic Group / Proposed Split：`redis_hot_key` / `main`
- Relevant Parent：`8562f1c8-f1d3-42e8-b19c-3c4c4e392854`
- Relevant Child：`e6f7faf0-07a5-4412-936d-b4e94b20f1bc`、`9c38c6cb-d7b6-471f-9c28-2727544858ac`
- 对应原文 1：热 Key 会造成分片 CPU/带宽倾斜与缓存击穿；可拆分数据、采用本地缓存，并设计限流、熔断和降级。
- 标注理由：Evidence-first：仅复用 frozen pilot-009 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-046
- 状态：Candidate / 待人工审核
- Query：面对热点缓存键，拆分数据、本地缓存、限流和熔断各在缓解哪类压力？
- Query Type：semantic_paraphrase
- Topic Group / Proposed Split：`redis_hot_key` / `main`
- Relevant Parent：`8562f1c8-f1d3-42e8-b19c-3c4c4e392854`
- Relevant Child：`e6f7faf0-07a5-4412-936d-b4e94b20f1bc`、`9c38c6cb-d7b6-471f-9c28-2727544858ac`
- 对应原文 1：热 Key 会造成分片 CPU/带宽倾斜与缓存击穿；可拆分数据、采用本地缓存，并设计限流、熔断和降级。
- 标注理由：Evidence-first：仅复用 frozen pilot-009 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-047
- 状态：Candidate / 待人工审核
- Query：缓存击穿由热 Key 引发时，怎样把热点治理与降级策略组合起来？
- Query Type：semantic_paraphrase
- Topic Group / Proposed Split：`redis_hot_key` / `main`
- Relevant Parent：`8562f1c8-f1d3-42e8-b19c-3c4c4e392854`
- Relevant Child：`e6f7faf0-07a5-4412-936d-b4e94b20f1bc`、`9c38c6cb-d7b6-471f-9c28-2727544858ac`
- 对应原文 1：热 Key 会造成分片 CPU/带宽倾斜与缓存击穿；可拆分数据、采用本地缓存，并设计限流、熔断和降级。
- 标注理由：Evidence-first：仅复用 frozen pilot-009 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-048
- 状态：Candidate / 待人工审核
- Query：Redis 的吞吐主要来自哪些设计，而不是依赖大量工作线程？
- Query Type：semantic_paraphrase
- Topic Group / Proposed Split：`redis_architecture` / `main`
- Relevant Parent：`e454c186-fb75-4945-bc2e-d6f3894bd350`、`9808e98b-f72e-4664-95aa-097801d12443`、`d0168209-76ff-4454-9405-95db5110c49d`
- Relevant Child：`d4121f65-aaf7-4e4e-b49f-9f08cee13d7f`、`7bce1e61-ee7d-479b-916a-4853022919de`、`990c8e05-be6a-4808-90e4-bfad6a98da21`
- 对应原文 1：纯内存、非阻塞 I/O、epoll 多路复用和单线程事件模型减少锁竞争及上下文切换。
- 标注理由：Evidence-first：仅复用 frozen pilot-010 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-049
- 状态：Candidate / 待人工审核
- Query：纯内存、非阻塞 I/O 与 epoll 多路复用怎样减少 Redis 的执行开销？
- Query Type：semantic_paraphrase
- Topic Group / Proposed Split：`redis_architecture` / `main`
- Relevant Parent：`e454c186-fb75-4945-bc2e-d6f3894bd350`、`9808e98b-f72e-4664-95aa-097801d12443`、`d0168209-76ff-4454-9405-95db5110c49d`
- Relevant Child：`d4121f65-aaf7-4e4e-b49f-9f08cee13d7f`、`7bce1e61-ee7d-479b-916a-4853022919de`、`990c8e05-be6a-4808-90e4-bfad6a98da21`
- 对应原文 1：纯内存、非阻塞 I/O、epoll 多路复用和单线程事件模型减少锁竞争及上下文切换。
- 标注理由：Evidence-first：仅复用 frozen pilot-010 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-050
- 状态：Candidate / 待人工审核
- Query：单线程事件循环为什么没有阻碍 Redis 获得较高吞吐？
- Query Type：semantic_paraphrase
- Topic Group / Proposed Split：`redis_architecture` / `main`
- Relevant Parent：`e454c186-fb75-4945-bc2e-d6f3894bd350`、`9808e98b-f72e-4664-95aa-097801d12443`、`d0168209-76ff-4454-9405-95db5110c49d`
- Relevant Child：`d4121f65-aaf7-4e4e-b49f-9f08cee13d7f`、`7bce1e61-ee7d-479b-916a-4853022919de`、`990c8e05-be6a-4808-90e4-bfad6a98da21`
- 对应原文 1：纯内存、非阻塞 I/O、epoll 多路复用和单线程事件模型减少锁竞争及上下文切换。
- 标注理由：Evidence-first：仅复用 frozen pilot-010 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-051
- 状态：Candidate / 待人工审核
- Query：评估网络延迟时，毫秒数与游戏、视频会议、网页浏览体验应如何对应起来？
- Query Type：cross_chunk_boundary
- Topic Group / Proposed Split：`network_performance` / `holdout`
- Relevant Parent：`4312929b-2b65-4b3b-9780-f372774352fc`
- Relevant Child：`3e63533d-7343-49c9-9144-c09d06483e12`、`bbf08b13-d43d-4b9b-97fd-ae471cf73df2`、`1faa2ec4-de5a-42eb-837e-526305a00b04`
- 对应原文 1：连续片段先解释毫秒延迟对交互体验的影响，再给出良好延迟标准及游戏、通话、浏览和视频的体验分级。
- 标注理由：Evidence-first：仅复用 frozen pilot-011 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-052
- 状态：Candidate / 待人工审核
- Query：同一条 RTT 指标为什么会对在线游戏、通话和普通网页产生不同影响？
- Query Type：cross_chunk_boundary
- Topic Group / Proposed Split：`network_performance` / `holdout`
- Relevant Parent：`4312929b-2b65-4b3b-9780-f372774352fc`
- Relevant Child：`3e63533d-7343-49c9-9144-c09d06483e12`、`bbf08b13-d43d-4b9b-97fd-ae471cf73df2`、`1faa2ec4-de5a-42eb-837e-526305a00b04`
- 对应原文 1：连续片段先解释毫秒延迟对交互体验的影响，再给出良好延迟标准及游戏、通话、浏览和视频的体验分级。
- 标注理由：Evidence-first：仅复用 frozen pilot-011 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-053
- 状态：Candidate / 待人工审核
- Query：需要向用户解释网络“卡”的程度时，怎样同时给出延迟区间和典型应用体验？
- Query Type：cross_chunk_boundary
- Topic Group / Proposed Split：`network_performance` / `holdout`
- Relevant Parent：`4312929b-2b65-4b3b-9780-f372774352fc`
- Relevant Child：`3e63533d-7343-49c9-9144-c09d06483e12`、`bbf08b13-d43d-4b9b-97fd-ae471cf73df2`、`1faa2ec4-de5a-42eb-837e-526305a00b04`
- 对应原文 1：连续片段先解释毫秒延迟对交互体验的影响，再给出良好延迟标准及游戏、通话、浏览和视频的体验分级。
- 标注理由：Evidence-first：仅复用 frozen pilot-011 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-054
- 状态：Candidate / 待人工审核
- Query：用户觉得网页只是变慢、游戏却明显卡顿时，怎样用同一延迟指标解释两种体验差别？
- Query Type：cross_chunk_boundary
- Topic Group / Proposed Split：`network_performance` / `holdout`
- Relevant Parent：`4312929b-2b65-4b3b-9780-f372774352fc`
- Relevant Child：`3e63533d-7343-49c9-9144-c09d06483e12`、`bbf08b13-d43d-4b9b-97fd-ae471cf73df2`、`1faa2ec4-de5a-42eb-837e-526305a00b04`
- 对应原文 1：连续片段先解释毫秒延迟对交互体验的影响，再给出良好延迟标准及游戏、通话、浏览和视频的体验分级。
- 标注理由：Evidence-first：仅复用 frozen pilot-011 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-055
- 状态：Candidate / 待人工审核
- Query：网络质量报告为什么要同时保留毫秒延迟值和应用体验分级，而不能只给一个 RTT 数字？
- Query Type：cross_chunk_boundary
- Topic Group / Proposed Split：`network_performance` / `holdout`
- Relevant Parent：`4312929b-2b65-4b3b-9780-f372774352fc`
- Relevant Child：`3e63533d-7343-49c9-9144-c09d06483e12`、`bbf08b13-d43d-4b9b-97fd-ae471cf73df2`、`1faa2ec4-de5a-42eb-837e-526305a00b04`
- 对应原文 1：连续片段先解释毫秒延迟对交互体验的影响，再给出良好延迟标准及游戏、通话、浏览和视频的体验分级。
- 标注理由：Evidence-first：仅复用 frozen pilot-011 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-056
- 状态：Candidate / 待人工审核
- Query：游戏对低延迟更敏感、视频和网页容忍度不同的情况下，应怎样说明当前网络质量？
- Query Type：cross_chunk_boundary
- Topic Group / Proposed Split：`network_performance` / `holdout`
- Relevant Parent：`4312929b-2b65-4b3b-9780-f372774352fc`
- Relevant Child：`3e63533d-7343-49c9-9144-c09d06483e12`、`bbf08b13-d43d-4b9b-97fd-ae471cf73df2`、`1faa2ec4-de5a-42eb-837e-526305a00b04`
- 对应原文 1：连续片段先解释毫秒延迟对交互体验的影响，再给出良好延迟标准及游戏、通话、浏览和视频的体验分级。
- 标注理由：Evidence-first：仅复用 frozen pilot-011 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-057
- 状态：Candidate / 待人工审核
- Query：比较三种缓存模式时，Cache-Aside 的读流程、Read-Through 的责任转移和 Write-Through 的写流程各是什么？
- Query Type：cross_chunk_boundary
- Topic Group / Proposed Split：`cache_patterns` / `main`
- Relevant Parent：`cab0e2c7-7d80-4184-b184-4d6b198fb6e4`
- Relevant Child：`4637bbd5-b09f-4552-9b54-c8f5cf012e33`、`c64e20e7-7125-402e-bb71-c7f016f02aee`、`b2cf4ad2-19d5-4a62-aaa1-0f06834642ce`
- 对应原文 1：三个连续片段依次说明旁路缓存读取、Read-Through 责任转移、Write-Through 同步写入及更新顺序问题。
- 标注理由：Evidence-first：仅复用 frozen pilot-013 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-058
- 状态：Candidate / 待人工审核
- Query：从一次读缓存到一次写数据库，Cache-Aside、Read-Through、Write-Through 的处理顺序有哪些关键差异？
- Query Type：cross_chunk_boundary
- Topic Group / Proposed Split：`cache_patterns` / `main`
- Relevant Parent：`cab0e2c7-7d80-4184-b184-4d6b198fb6e4`
- Relevant Child：`4637bbd5-b09f-4552-9b54-c8f5cf012e33`、`c64e20e7-7125-402e-bb71-c7f016f02aee`、`b2cf4ad2-19d5-4a62-aaa1-0f06834642ce`
- 对应原文 1：三个连续片段依次说明旁路缓存读取、Read-Through 责任转移、Write-Through 同步写入及更新顺序问题。
- 标注理由：Evidence-first：仅复用 frozen pilot-013 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-059
- 状态：Candidate / 待人工审核
- Query：为什么说明缓存模式不能只看读路径，还要同时说明 Write-Through 的同步写入与更新顺序？
- Query Type：cross_chunk_boundary
- Topic Group / Proposed Split：`cache_patterns` / `main`
- Relevant Parent：`cab0e2c7-7d80-4184-b184-4d6b198fb6e4`
- Relevant Child：`4637bbd5-b09f-4552-9b54-c8f5cf012e33`、`c64e20e7-7125-402e-bb71-c7f016f02aee`、`b2cf4ad2-19d5-4a62-aaa1-0f06834642ce`
- 对应原文 1：三个连续片段依次说明旁路缓存读取、Read-Through 责任转移、Write-Through 同步写入及更新顺序问题。
- 标注理由：Evidence-first：仅复用 frozen pilot-013 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-060
- 状态：Candidate / 待人工审核
- Query：“先更新数据库再删缓存”在并发读写下怎样留下旧值窗口，binlog 订阅和重试删除如何补偿？
- Query Type：cross_chunk_boundary
- Topic Group / Proposed Split：`cache_consistency` / `main`
- Relevant Parent：`1dca64e0-586d-48b8-85ef-ee3485a637f9`
- Relevant Child：`f0e4adc6-83b1-47c9-8aee-df5b578c16bf`、`126e7851-9146-4c9b-a8b3-a6ad0f674eec`、`da4c9ffd-140f-4491-aebf-606ec2dc737e`
- 对应原文 1：连续片段覆盖写库删缓存方案、读写线程交错产生旧缓存的小概率窗口，以及 Canal 订阅 binlog、消息队列重试删除。
- 标注理由：Evidence-first：仅复用 frozen pilot-014 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-061
- 状态：Candidate / 待人工审核
- Query：缓存先删后写之外，为什么还要分析写库删缓存的交错时序与 Canal 重试？
- Query Type：cross_chunk_boundary
- Topic Group / Proposed Split：`cache_consistency` / `main`
- Relevant Parent：`1dca64e0-586d-48b8-85ef-ee3485a637f9`
- Relevant Child：`f0e4adc6-83b1-47c9-8aee-df5b578c16bf`、`126e7851-9146-4c9b-a8b3-a6ad0f674eec`、`da4c9ffd-140f-4491-aebf-606ec2dc737e`
- 对应原文 1：连续片段覆盖写库删缓存方案、读写线程交错产生旧缓存的小概率窗口，以及 Canal 订阅 binlog、消息队列重试删除。
- 标注理由：Evidence-first：仅复用 frozen pilot-014 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-062
- 状态：Candidate / 待人工审核
- Query：要解释缓存最终一致性，怎样把旧缓存产生条件、binlog 监听和异步删缓存连成完整流程？
- Query Type：cross_chunk_boundary
- Topic Group / Proposed Split：`cache_consistency` / `main`
- Relevant Parent：`1dca64e0-586d-48b8-85ef-ee3485a637f9`
- Relevant Child：`f0e4adc6-83b1-47c9-8aee-df5b578c16bf`、`126e7851-9146-4c9b-a8b3-a6ad0f674eec`、`da4c9ffd-140f-4491-aebf-606ec2dc737e`
- 对应原文 1：连续片段覆盖写库删缓存方案、读写线程交错产生旧缓存的小概率窗口，以及 Canal 订阅 binlog、消息队列重试删除。
- 标注理由：Evidence-first：仅复用 frozen pilot-014 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-063
- 状态：Candidate / 待人工审核
- Query：热 Key 导致单分片倾斜并引发缓存击穿后，治理措施和监控信号分别应该看什么？
- Query Type：cross_chunk_boundary
- Topic Group / Proposed Split：`redis_hot_key` / `main`
- Relevant Parent：`8562f1c8-f1d3-42e8-b19c-3c4c4e392854`
- Relevant Child：`e6f7faf0-07a5-4412-936d-b4e94b20f1bc`、`9c38c6cb-d7b6-471f-9c28-2727544858ac`、`5715943c-d7f0-4545-a9d7-1e69e6d348b7`
- 对应原文 1：三个连续片段依次描述分片资源倾斜和缓存击穿、拆分/降级与抓包统计，以及通过节点 CPU、带宽告警发现热点。
- 标注理由：Evidence-first：仅复用 frozen pilot-015 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-064
- 状态：Candidate / 待人工审核
- Query：从热点访问到数据库被打穿，中间的风险链路、缓解手段和 CPU/带宽告警如何对应？
- Query Type：cross_chunk_boundary
- Topic Group / Proposed Split：`redis_hot_key` / `main`
- Relevant Parent：`8562f1c8-f1d3-42e8-b19c-3c4c4e392854`
- Relevant Child：`e6f7faf0-07a5-4412-936d-b4e94b20f1bc`、`9c38c6cb-d7b6-471f-9c28-2727544858ac`、`5715943c-d7f0-4545-a9d7-1e69e6d348b7`
- 对应原文 1：三个连续片段依次描述分片资源倾斜和缓存击穿、拆分/降级与抓包统计，以及通过节点 CPU、带宽告警发现热点。
- 标注理由：Evidence-first：仅复用 frozen pilot-015 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-065
- 状态：Candidate / 待人工审核
- Query：处理热 Key 时，为什么不能只做限流，还要结合数据拆分、降级和节点资源监控？
- Query Type：cross_chunk_boundary
- Topic Group / Proposed Split：`redis_hot_key` / `main`
- Relevant Parent：`8562f1c8-f1d3-42e8-b19c-3c4c4e392854`
- Relevant Child：`e6f7faf0-07a5-4412-936d-b4e94b20f1bc`、`9c38c6cb-d7b6-471f-9c28-2727544858ac`、`5715943c-d7f0-4545-a9d7-1e69e6d348b7`
- 对应原文 1：三个连续片段依次描述分片资源倾斜和缓存击穿、拆分/降级与抓包统计，以及通过节点 CPU、带宽告警发现热点。
- 标注理由：Evidence-first：仅复用 frozen pilot-015 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-066
- 状态：Candidate / 待人工审核
- Query：为突发流量服务同时配置 HPA 和 VPA 时，副本调整、资源 request、指标分离、CPU 阈值和 updateMode 应怎样协同？
- Query Type：multi_parent_synthesis
- Topic Group / Proposed Split：`hpa_vpa` / `main`
- Relevant Parent：`6f5603fe-c213-4aa7-aab4-71807769d72e`、`29a841de-29c4-4cef-a505-5538c4fc6c7f`、`eefff46b-4abc-4400-88fb-a705b8a8c182`、`c8bc8370-b646-4176-9a5a-d8ecacd5a481`、`dc8d324b-3112-44ad-8899-d2ff73ac3142`
- Relevant Child：`5a84c9fe-d0e2-4b60-b663-0fd823840284`、`4ce5d77d-cc81-406f-b23e-2bdf244edd18`、`c6f3e1f8-cfc5-4b56-852c-a778864d99e1`、`a7b8d05f-5168-418f-aa73-423eebe6ad1d`、`0253321d-f9a4-4121-bdce-58fd767991bc`
- 对应原文 1：HPA 调整副本，VPA 调整资源请求；生产配置还涉及指标隔离、CPU 阈值、冷却时间和 VPA 更新模式。
- 标注理由：Evidence-first：仅复用 frozen pilot-016 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-067
- 状态：Candidate / 待人工审核
- Query：需要兼顾弹性与资源利用率时，HPA/VPA 的职责边界、冲突规避和生产参数如何一起设计？
- Query Type：multi_parent_synthesis
- Topic Group / Proposed Split：`hpa_vpa` / `main`
- Relevant Parent：`6f5603fe-c213-4aa7-aab4-71807769d72e`、`29a841de-29c4-4cef-a505-5538c4fc6c7f`、`eefff46b-4abc-4400-88fb-a705b8a8c182`、`c8bc8370-b646-4176-9a5a-d8ecacd5a481`、`dc8d324b-3112-44ad-8899-d2ff73ac3142`
- Relevant Child：`5a84c9fe-d0e2-4b60-b663-0fd823840284`、`4ce5d77d-cc81-406f-b23e-2bdf244edd18`、`c6f3e1f8-cfc5-4b56-852c-a778864d99e1`、`a7b8d05f-5168-418f-aa73-423eebe6ad1d`、`0253321d-f9a4-4121-bdce-58fd767991bc`
- 对应原文 1：HPA 调整副本，VPA 调整资源请求；生产配置还涉及指标隔离、CPU 阈值、冷却时间和 VPA 更新模式。
- 标注理由：Evidence-first：仅复用 frozen pilot-016 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-068
- 状态：Candidate / 待人工审核
- Query：HPA 与 VPA 联用的方案中，怎样把副本扩缩、单 Pod 资源、不同指标和 VPA 模式组合为可执行配置？
- Query Type：multi_parent_synthesis
- Topic Group / Proposed Split：`hpa_vpa` / `main`
- Relevant Parent：`6f5603fe-c213-4aa7-aab4-71807769d72e`、`29a841de-29c4-4cef-a505-5538c4fc6c7f`、`eefff46b-4abc-4400-88fb-a705b8a8c182`、`c8bc8370-b646-4176-9a5a-d8ecacd5a481`、`dc8d324b-3112-44ad-8899-d2ff73ac3142`
- Relevant Child：`5a84c9fe-d0e2-4b60-b663-0fd823840284`、`4ce5d77d-cc81-406f-b23e-2bdf244edd18`、`c6f3e1f8-cfc5-4b56-852c-a778864d99e1`、`a7b8d05f-5168-418f-aa73-423eebe6ad1d`、`0253321d-f9a4-4121-bdce-58fd767991bc`
- 对应原文 1：HPA 调整副本，VPA 调整资源请求；生产配置还涉及指标隔离、CPU 阈值、冷却时间和 VPA 更新模式。
- 标注理由：Evidence-first：仅复用 frozen pilot-016 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-069
- 状态：Candidate / 待人工审核
- Query：给机器学习服务搭建 API 层时，Starlette/Pydantic、ASGI 并发、OpenAPI 自动化和模型部署场景怎样共同影响 FastAPI 选型？
- Query Type：multi_parent_synthesis
- Topic Group / Proposed Split：`fastapi` / `holdout`
- Relevant Parent：`817487ad-38d1-456d-8c36-1000e15365f9`、`64f9e670-272a-4ac0-9735-fc9837bb0147`、`a9043b59-b8a7-4227-8e70-8051ddd51f22`、`156b220b-cf6f-4986-804e-73754954e741`
- Relevant Child：`a19f034a-ab26-4f53-97be-7a7b28cc6f52`、`3e7aa036-d7eb-4d93-ba6e-ea98f6847a57`、`af997fce-c3ce-442b-accd-dc790211fbc9`、`275e9feb-ebf1-46c6-8bf4-9199244f2136`
- 对应原文 1：Starlette/Pydantic 提供异步和校验，ASGI 带来高并发，OpenAPI 自动化降低联调成本，应用章节明确覆盖模型部署。
- 标注理由：Evidence-first：仅复用 frozen pilot-017 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-070
- 状态：Candidate / 待人工审核
- Query：比较 API 框架是否适合模型服务时，如何同时考察异步请求处理、数据校验、接口文档和部署适配？
- Query Type：multi_parent_synthesis
- Topic Group / Proposed Split：`fastapi` / `holdout`
- Relevant Parent：`817487ad-38d1-456d-8c36-1000e15365f9`、`64f9e670-272a-4ac0-9735-fc9837bb0147`、`a9043b59-b8a7-4227-8e70-8051ddd51f22`、`156b220b-cf6f-4986-804e-73754954e741`
- Relevant Child：`a19f034a-ab26-4f53-97be-7a7b28cc6f52`、`3e7aa036-d7eb-4d93-ba6e-ea98f6847a57`、`af997fce-c3ce-442b-accd-dc790211fbc9`、`275e9feb-ebf1-46c6-8bf4-9199244f2136`
- 对应原文 1：Starlette/Pydantic 提供异步和校验，ASGI 带来高并发，OpenAPI 自动化降低联调成本，应用章节明确覆盖模型部署。
- 标注理由：Evidence-first：仅复用 frozen pilot-017 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-071
- 状态：Candidate / 待人工审核
- Query：FastAPI 面向 ML 推理服务的价值，为什么不能只看吞吐，还要结合验证机制、OpenAPI 和应用场景？
- Query Type：multi_parent_synthesis
- Topic Group / Proposed Split：`fastapi` / `holdout`
- Relevant Parent：`817487ad-38d1-456d-8c36-1000e15365f9`、`64f9e670-272a-4ac0-9735-fc9837bb0147`、`a9043b59-b8a7-4227-8e70-8051ddd51f22`、`156b220b-cf6f-4986-804e-73754954e741`
- Relevant Child：`a19f034a-ab26-4f53-97be-7a7b28cc6f52`、`3e7aa036-d7eb-4d93-ba6e-ea98f6847a57`、`af997fce-c3ce-442b-accd-dc790211fbc9`、`275e9feb-ebf1-46c6-8bf4-9199244f2136`
- 对应原文 1：Starlette/Pydantic 提供异步和校验，ASGI 带来高并发，OpenAPI 自动化降低联调成本，应用章节明确覆盖模型部署。
- 标注理由：Evidence-first：仅复用 frozen pilot-017 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-072
- 状态：Candidate / 待人工审核
- Query：设计实时文本推送时，SSE 的事件协议、与 WebSocket/长轮询的取舍、适用场景和限制应如何一起判断？
- Query Type：multi_parent_synthesis
- Topic Group / Proposed Split：`sse` / `holdout`
- Relevant Parent：`2df4c511-b356-406e-bf69-ec32a60a0df0`、`bbc63975-1526-4f56-b6e4-73002fd85513`、`d629c5af-47b9-4eca-9cbf-3cd9e07941b8`、`faddb4f2-2482-485b-b7ba-99a1787ad79c`
- Relevant Child：`7bd73b02-717e-434d-81a1-e4ba85440a91`、`3400f795-6752-47a1-819c-fc33f6733ef7`、`21f27a0c-c30a-4396-acd1-0e62088da327`、`0fb1b787-3f59-43d0-9f35-5303da075c85`
- 对应原文 1：四个章节分别说明 SSE 事件流协议、与 WebSocket/长轮询比较、AI/监控等场景，以及单向、兼容性和二进制限制。
- 标注理由：Evidence-first：仅复用 frozen pilot-018 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-073
- 状态：Candidate / 待人工审核
- Query：如果产品要推送 AI 生成进度和监控通知，怎样依据 SSE 的重连机制、替代方案和二进制限制做决策？
- Query Type：multi_parent_synthesis
- Topic Group / Proposed Split：`sse` / `holdout`
- Relevant Parent：`2df4c511-b356-406e-bf69-ec32a60a0df0`、`bbc63975-1526-4f56-b6e4-73002fd85513`、`d629c5af-47b9-4eca-9cbf-3cd9e07941b8`、`faddb4f2-2482-485b-b7ba-99a1787ad79c`
- Relevant Child：`7bd73b02-717e-434d-81a1-e4ba85440a91`、`3400f795-6752-47a1-819c-fc33f6733ef7`、`21f27a0c-c30a-4396-acd1-0e62088da327`、`0fb1b787-3f59-43d0-9f35-5303da075c85`
- 对应原文 1：四个章节分别说明 SSE 事件流协议、与 WebSocket/长轮询比较、AI/监控等场景，以及单向、兼容性和二进制限制。
- 标注理由：Evidence-first：仅复用 frozen pilot-018 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-074
- 状态：Candidate / 待人工审核
- Query：选择 SSE 之前，为什么必须同时核对事件格式、典型用途、双向通信需求和客户端兼容性？
- Query Type：multi_parent_synthesis
- Topic Group / Proposed Split：`sse` / `holdout`
- Relevant Parent：`2df4c511-b356-406e-bf69-ec32a60a0df0`、`bbc63975-1526-4f56-b6e4-73002fd85513`、`d629c5af-47b9-4eca-9cbf-3cd9e07941b8`、`faddb4f2-2482-485b-b7ba-99a1787ad79c`
- Relevant Child：`7bd73b02-717e-434d-81a1-e4ba85440a91`、`3400f795-6752-47a1-819c-fc33f6733ef7`、`21f27a0c-c30a-4396-acd1-0e62088da327`、`0fb1b787-3f59-43d0-9f35-5303da075c85`
- 对应原文 1：四个章节分别说明 SSE 事件流协议、与 WebSocket/长轮询比较、AI/监控等场景，以及单向、兼容性和二进制限制。
- 标注理由：Evidence-first：仅复用 frozen pilot-018 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-075
- 状态：Candidate / 待人工审核
- Query：评估 Redis 的技术特性时，数据结构与持久化、读写性能、非阻塞 I/O 和单线程事件模型应怎样结合解释？
- Query Type：multi_parent_synthesis
- Topic Group / Proposed Split：`redis_architecture` / `main`
- Relevant Parent：`7628aa83-d4c2-4678-83b0-9e19001f9906`、`0abf7d70-2bff-4be9-be89-10f7f08d29e6`、`9808e98b-f72e-4664-95aa-097801d12443`、`e454c186-fb75-4945-bc2e-d6f3894bd350`
- Relevant Child：`1a763fce-c3ae-4b78-aff5-d2473ef3805e`、`45d707dc-27c2-4db0-ad7c-c7f7f6dbc432`、`7bce1e61-ee7d-479b-916a-4853022919de`、`d4121f65-aaf7-4e4e-b49f-9f08cee13d7f`
- 对应原文 1：Redis 支持多种数据结构、持久化和高可用；基准展示读写吞吐；非阻塞 I/O、多路复用和单线程事件模型解释性能来源。
- 标注理由：Evidence-first：仅复用 frozen pilot-019 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-076
- 状态：Candidate / 待人工审核
- Query：为什么 Redis 的能力画像既要看数据能力与高可用，也要看基准吞吐和 epoll 驱动的事件循环？
- Query Type：multi_parent_synthesis
- Topic Group / Proposed Split：`redis_architecture` / `main`
- Relevant Parent：`7628aa83-d4c2-4678-83b0-9e19001f9906`、`0abf7d70-2bff-4be9-be89-10f7f08d29e6`、`9808e98b-f72e-4664-95aa-097801d12443`、`e454c186-fb75-4945-bc2e-d6f3894bd350`
- Relevant Child：`1a763fce-c3ae-4b78-aff5-d2473ef3805e`、`45d707dc-27c2-4db0-ad7c-c7f7f6dbc432`、`7bce1e61-ee7d-479b-916a-4853022919de`、`d4121f65-aaf7-4e4e-b49f-9f08cee13d7f`
- 对应原文 1：Redis 支持多种数据结构、持久化和高可用；基准展示读写吞吐；非阻塞 I/O、多路复用和单线程事件模型解释性能来源。
- 标注理由：Evidence-first：仅复用 frozen pilot-019 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-077
- 状态：Candidate / 待人工审核
- Query：从产品能力到性能机制，如何把 Redis 的数据类型、持久化、I/O 多路复用和单线程模型放在同一结论里？
- Query Type：multi_parent_synthesis
- Topic Group / Proposed Split：`redis_architecture` / `main`
- Relevant Parent：`7628aa83-d4c2-4678-83b0-9e19001f9906`、`0abf7d70-2bff-4be9-be89-10f7f08d29e6`、`9808e98b-f72e-4664-95aa-097801d12443`、`e454c186-fb75-4945-bc2e-d6f3894bd350`
- Relevant Child：`1a763fce-c3ae-4b78-aff5-d2473ef3805e`、`45d707dc-27c2-4db0-ad7c-c7f7f6dbc432`、`7bce1e61-ee7d-479b-916a-4853022919de`、`d4121f65-aaf7-4e4e-b49f-9f08cee13d7f`
- 对应原文 1：Redis 支持多种数据结构、持久化和高可用；基准展示读写吞吐；非阻塞 I/O、多路复用和单线程事件模型解释性能来源。
- 标注理由：Evidence-first：仅复用 frozen pilot-019 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-078
- 状态：Candidate / 待人工审核
- Query：设计生产级 Redis 锁时，互斥/可重入语义、SET NX PX、Watch Dog 续约和集群故障处理怎样共同约束方案？
- Query Type：multi_parent_synthesis
- Topic Group / Proposed Split：`redis_lock` / `main`
- Relevant Parent：`81a99a66-19a8-4f48-a65e-2e53d2d22e51`、`16b311ed-3ce5-4de2-8588-b436fd9ca99e`、`9e0cf715-ea15-49ea-8142-d0464d6e9b70`、`fc889dc3-14f0-482a-9fe7-25fc15e92ca6`
- Relevant Child：`3751880e-f729-4df3-824e-dffb38f97fbe`、`dbbd479f-7ba9-4f4c-88cd-ae95be7b084b`、`1fa17e4e-8f23-4d54-8049-430f999fbb0e`、`e6dd8ca0-f495-4e6f-af0a-e85d1e3dd6e6`
- 对应原文 1：锁需要互斥、高可用、防死锁与可重入；SET NX PX 完成原子加锁；Watch Dog 处理提前过期；集群、哨兵或 Redlock 应对单点故障。
- 标注理由：Evidence-first：仅复用 frozen pilot-020 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-079
- 状态：Candidate / 待人工审核
- Query：Redis 锁在业务超时和节点故障下要可靠工作，为什么需要同时考虑原子加锁、自动续期和哨兵或 Redlock？
- Query Type：multi_parent_synthesis
- Topic Group / Proposed Split：`redis_lock` / `main`
- Relevant Parent：`81a99a66-19a8-4f48-a65e-2e53d2d22e51`、`16b311ed-3ce5-4de2-8588-b436fd9ca99e`、`9e0cf715-ea15-49ea-8142-d0464d6e9b70`、`fc889dc3-14f0-482a-9fe7-25fc15e92ca6`
- Relevant Child：`3751880e-f729-4df3-824e-dffb38f97fbe`、`dbbd479f-7ba9-4f4c-88cd-ae95be7b084b`、`1fa17e4e-8f23-4d54-8049-430f999fbb0e`、`e6dd8ca0-f495-4e6f-af0a-e85d1e3dd6e6`
- 对应原文 1：锁需要互斥、高可用、防死锁与可重入；SET NX PX 完成原子加锁；Watch Dog 处理提前过期；集群、哨兵或 Redlock 应对单点故障。
- 标注理由：Evidence-first：仅复用 frozen pilot-020 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：

## candidate-080
- 状态：Candidate / 待人工审核
- Query：从锁的正确性到可用性，如何组合所有权语义、过期保护、Watch Dog 和多节点部署？
- Query Type：multi_parent_synthesis
- Topic Group / Proposed Split：`redis_lock` / `main`
- Relevant Parent：`81a99a66-19a8-4f48-a65e-2e53d2d22e51`、`16b311ed-3ce5-4de2-8588-b436fd9ca99e`、`9e0cf715-ea15-49ea-8142-d0464d6e9b70`、`fc889dc3-14f0-482a-9fe7-25fc15e92ca6`
- Relevant Child：`3751880e-f729-4df3-824e-dffb38f97fbe`、`dbbd479f-7ba9-4f4c-88cd-ae95be7b084b`、`1fa17e4e-8f23-4d54-8049-430f999fbb0e`、`e6dd8ca0-f495-4e6f-af0a-e85d1e3dd6e6`
- 对应原文 1：锁需要互斥、高可用、防死锁与可重入；SET NX PX 完成原子加锁；Watch Dog 处理提前过期；集群、哨兵或 Redlock 应对单点故障。
- 标注理由：Evidence-first：仅复用 frozen pilot-020 中已人工确认的正文证据；每个 Child 对 Query 的明确子事实提供必要支撑，待对新增 Query 做人工复核。
- [ ] Query 是否合理
- [ ] Relevant Child 是否直接且必要
- [ ] 是否遗漏其他 Relevant Child
- 人工备注：
