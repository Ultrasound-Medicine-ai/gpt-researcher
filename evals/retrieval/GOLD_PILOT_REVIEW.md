# Retrieval Gold Pilot 人工审核

> 20 条 Candidate 已完成人工语义审核：16 条直接通过，4 条修正 Query；0 条废弃。
> 所有 `Relevant Child` 的完整性仍待 omission review 人工确认；不得据此报告 Recall、MRR 或 Evidence Recall。
> 后续 Main/Holdout 必须以 `topic_group` 为最小划分单位。

## pilot-001
- Query：浏览器通过 SSE 断线重连时，服务端和客户端依靠哪些事件字段恢复消息位置？
- Query Type：exact_keyword
- Topic Group：`sse`
- Candidate Parent：`2df4c511-b356-406e-bf69-ec32a60a0df0`
- Candidate Child：`7bd73b02-717e-434d-81a1-e4ba85440a91`
- 对应原文：SSE 使用 text/event-stream，事件包含 data、event、id，并通过 Last-Event-ID 与自动重连恢复数据流。
- 候选理由：该 Child 集中定义 SSE 事件格式、连接方式和断线恢复机制。
- 人工审核：直接通过。人工审核：Candidate Gold 无需修改。
- [x] Query 是否合理
- [x] Relevant Child 是否正确
- [ ] 是否遗漏其他 Relevant Child（待完整 corpus omission check）
- 人工备注：

## pilot-002
- Query：生产环境配置 HPA 时，需要重点设置哪些参数，CPU 目标利用率通常处于什么区间？
- Query Type：exact_keyword
- Topic Group：`hpa_vpa`
- Candidate Parent：`c8bc8370-b646-4176-9a5a-d8ecacd5a481`
- Candidate Child：`a7b8d05f-5168-418f-aa73-423eebe6ad1d`
- 对应原文：HPA 目标 CPU 利用率通常为 60%～80%，同时需要设置最小/最大副本数和扩缩容冷却时间。
- 候选理由：该 Child 唯一同时包含三个 HPA 生产配置参数。
- 人工审核：修正 Query 后通过。证据只给出 CPU 60%～80%；副本上下限和冷却时间仅要求配置，未给出具体数值。
- [x] Query 是否合理
- [x] Relevant Child 是否正确
- [ ] 是否遗漏其他 Relevant Child（待完整 corpus omission check）
- 人工备注：

## pilot-003
- Query：VPA 的 Off、Initial、Auto 三种模式分别会不会自动修改现有 Pod？
- Query Type：exact_keyword
- Topic Group：`hpa_vpa`
- Candidate Parent：`dc8d324b-3112-44ad-8899-d2ff73ac3142`
- Candidate Child：`0253321d-f9a4-4121-bdce-58fd767991bc`
- 对应原文：Off 仅提供建议，Initial 只作用于新 Pod，Auto 会自动更新配置但可能触发 Pod 重启。
- 候选理由：该 Child 明确定义 VPA 三种模式及其更新行为。
- 人工审核：直接通过。人工审核：Candidate Gold 无需修改。
- [x] Query 是否合理
- [x] Relevant Child 是否正确
- [ ] 是否遗漏其他 Relevant Child（待完整 corpus omission check）
- 人工备注：

## pilot-004
- Query：用 Redis 建库存锁时，如何用随机标识、NX 和 PX 组合成一条原子加锁命令？
- Query Type：exact_keyword
- Topic Group：`redis_lock`
- Candidate Parent：`16b311ed-3ce5-4de2-8588-b436fd9ca99e`
- Candidate Child：`dbbd479f-7ba9-4f4c-88cd-ae95be7b084b`
- 对应原文：示例使用 SET lock:stock:1001 random-value NX PX 30000；NX 保证不存在时写入，PX 设置过期时间。
- 候选理由：该 Child 包含完整原子命令、随机 value 和过期参数语义。
- 人工审核：直接通过。人工审核：Candidate Gold 无需修改。
- [x] Query 是否合理
- [x] Relevant Child 是否正确
- [ ] 是否遗漏其他 Relevant Child（待完整 corpus omission check）
- 人工备注：

## pilot-005
- Query：Cache-Aside、Read-Through 与 Write-Through 的数据读写责任分别落在哪一层？
- Query Type：exact_keyword
- Topic Group：`cache_patterns`
- Candidate Parent：`cab0e2c7-7d80-4184-b184-4d6b198fb6e4`
- Candidate Child：`4637bbd5-b09f-4552-9b54-c8f5cf012e33`、`c64e20e7-7125-402e-bb71-c7f016f02aee`
- 对应原文：Cache-Aside 由应用读取数据库并填充缓存；Read-Through 和 Write-Through 将读取或写入责任交给缓存抽象层。
- 候选理由：两个连续 Child 分别定义 Cache-Aside 以及 Read/Write-Through，缺一无法完成比较。
- 人工审核：直接通过。人工审核：Candidate Gold 无需修改。
- [x] Query 是否合理
- [x] Relevant Child 是否正确
- [ ] 是否遗漏其他 Relevant Child（待完整 corpus omission check）
- 人工备注：

## pilot-006
- Query：业务只需要服务器持续推送文本通知时，为什么 SSE 往往比 WebSocket 更省实现成本？
- Query Type：semantic_paraphrase
- Topic Group：`sse`
- Candidate Parent：`69e43496-0751-4f64-a371-e815f63bc9f6`、`faddb4f2-2482-485b-b7ba-99a1787ad79c`
- Candidate Child：`6ef6dedc-f0d5-474f-886d-939ecf564ad5`、`0fb1b787-3f59-43d0-9f35-5303da075c85`
- 对应原文：SSE 复用 HTTP 基础设施且无需帧解析和心跳，适合单向文本推送；双向指令或二进制流仍需 WebSocket。
- 候选理由：优势 Child 与限制 Child 共同支持适用前提和不适用边界。
- 人工审核：直接通过。人工审核：Candidate Gold 无需修改。
- [x] Query 是否合理
- [x] Relevant Child 是否正确
- [ ] 是否遗漏其他 Relevant Child（待完整 corpus omission check）
- 人工备注：

## pilot-007
- Query：同时启用水平和垂直扩缩容时，为什么都盯着 CPU 会造成抖动，应怎样拆分指标？
- Query Type：semantic_paraphrase
- Topic Group：`hpa_vpa`
- Candidate Parent：`eefff46b-4abc-4400-88fb-a705b8a8c182`
- Candidate Child：`c6f3e1f8-cfc5-4b56-852c-a778864d99e1`
- 对应原文：VPA 修改单 Pod CPU 请求会影响 HPA 的副本计算；建议 HPA 基于 CPU、VPA 基于内存等不同指标。
- 候选理由：该 Child 直接解释冲突因果及分离指标的协调方案。
- 人工审核：直接通过。人工审核：Candidate Gold 无需修改。
- [x] Query 是否合理
- [x] Relevant Child 是否正确
- [ ] 是否遗漏其他 Relevant Child（待完整 corpus omission check）
- 人工备注：

## pilot-008
- Query：为什么 FastAPI 能减少接口参数错误，同时保持适合高并发后端的执行模型？
- Query Type：semantic_paraphrase
- Topic Group：`fastapi`
- Candidate Parent：`817487ad-38d1-456d-8c36-1000e15365f9`、`64f9e670-272a-4ac0-9735-fc9837bb0147`
- Candidate Child：`a19f034a-ab26-4f53-97be-7a7b28cc6f52`、`3e7aa036-d7eb-4d93-ba6e-ea98f6847a57`
- 对应原文：FastAPI 以 Starlette 处理异步请求、Pydantic 执行数据验证；ASGI 架构和严格类型校验提升并发与开发可靠性。
- 候选理由：架构与性能位于两个 Parent，联合解释异步执行和错误减少。
- 人工审核：直接通过。人工审核：Candidate Gold 无需修改。
- [x] Query 是否合理
- [x] Relevant Child 是否正确
- [ ] 是否遗漏其他 Relevant Child（待完整 corpus omission check）
- 人工备注：

## pilot-009
- Query：某个热 Key 流量突然集中并导致缓存击穿时，可以从哪些方向降低数据库压力？
- Query Type：semantic_paraphrase
- Topic Group：`redis_hot_key`
- Candidate Parent：`8562f1c8-f1d3-42e8-b19c-3c4c4e392854`
- Candidate Child：`e6f7faf0-07a5-4412-936d-b4e94b20f1bc`、`9c38c6cb-d7b6-471f-9c28-2727544858ac`
- 对应原文：热 Key 会造成分片 CPU/带宽倾斜与缓存击穿；可拆分数据、采用本地缓存，并设计限流、熔断和降级。
- 候选理由：问题没有复用原文术语，两个连续 Child 分别覆盖风险与缓解措施。
- 人工审核：修正 Query 后通过。证据描述热 Key 与缓存击穿，不应表述为缓存雪崩。
- [x] Query 是否合理
- [x] Relevant Child 是否正确
- [ ] 是否遗漏其他 Relevant Child（待完整 corpus omission check）
- 人工备注：

## pilot-010
- Query：Redis 没有依赖多工作线程仍能获得高吞吐，关键的软件和 I/O 设计是什么？
- Query Type：semantic_paraphrase
- Topic Group：`redis_architecture`
- Candidate Parent：`e454c186-fb75-4945-bc2e-d6f3894bd350`、`9808e98b-f72e-4664-95aa-097801d12443`、`d0168209-76ff-4454-9405-95db5110c49d`
- Candidate Child：`d4121f65-aaf7-4e4e-b49f-9f08cee13d7f`、`7bce1e61-ee7d-479b-916a-4853022919de`、`990c8e05-be6a-4808-90e4-bfad6a98da21`
- 对应原文：纯内存、非阻塞 I/O、epoll 多路复用和单线程事件模型减少锁竞争及上下文切换。
- 候选理由：三个 Parent 分别解释执行原理、I/O 多路复用和避免锁/切换开销。
- 人工审核：直接通过。人工审核：Candidate Gold 无需修改。
- [x] Query 是否合理
- [x] Relevant Child 是否正确
- [ ] 是否遗漏其他 Relevant Child（待完整 corpus omission check）
- 人工备注：

## pilot-011
- Query：从用户感知到数值区间，怎样判断网络延迟是否会影响游戏、视频会议和网页浏览？
- Query Type：cross_chunk_boundary
- Topic Group：`network_performance`
- Candidate Parent：`4312929b-2b65-4b3b-9780-f372774352fc`
- Candidate Child：`3e63533d-7343-49c9-9144-c09d06483e12`、`bbf08b13-d43d-4b9b-97fd-ae471cf73df2`、`1faa2ec4-de5a-42eb-837e-526305a00b04`
- 对应原文：连续片段先解释毫秒延迟对交互体验的影响，再给出良好延迟标准及游戏、通话、浏览和视频的体验分级。
- 候选理由：阈值说明与不同业务体验表跨越三个连续 Child，单一 Child 无法完整回答。
- 人工审核：直接通过。人工审核：Candidate Gold 无需修改。
- [x] Query 是否合理
- [x] Relevant Child 是否正确
- [ ] 是否遗漏其他 Relevant Child（待完整 corpus omission check）
- 人工备注：

## pilot-012
- Query：排查网络卡顿时，网页测速、ping、traceroute 和 iPerf 分别适合观察哪些网络现象？
- Query Type：cross_chunk_boundary
- Topic Group：`network_performance`
- Candidate Parent：`b868aae6-1c92-43e7-ba9c-c2a17d78e9fe`
- Candidate Child：`6349368f-8faa-4806-ad0c-478b263a24bb`、`0b71d03e-c66a-4fdf-8039-e679f6772ed7`、`81429dc4-9796-4dac-97e7-e98a8d0baf90`
- 对应原文：网页测速提供连接基线；traceroute 展示各跳路径；持续链路工具观察丢包；iPerf 测试局域网设备间吞吐。
- 候选理由：工具定位能力分布在同 Parent 的三个连续 Child。
- 人工审核：修正 Query 后通过。已核验：现有 Gold Child 明确包含 ping 与 traceroute；保留 Query 中的 ping。
- [x] Query 是否合理
- [x] Relevant Child 是否正确
- [ ] 是否遗漏其他 Relevant Child（待完整 corpus omission check）
- 人工备注：

## pilot-013
- Query：一次缓存读取到一次同步写入，Cache-Aside、Read-Through 和 Write-Through 的完整流程有什么差别？
- Query Type：cross_chunk_boundary
- Topic Group：`cache_patterns`
- Candidate Parent：`cab0e2c7-7d80-4184-b184-4d6b198fb6e4`
- Candidate Child：`4637bbd5-b09f-4552-9b54-c8f5cf012e33`、`c64e20e7-7125-402e-bb71-c7f016f02aee`、`b2cf4ad2-19d5-4a62-aaa1-0f06834642ce`
- 对应原文：三个连续片段依次说明旁路缓存读取、Read-Through 责任转移、Write-Through 同步写入及更新顺序问题。
- 候选理由：问题要求完整读写流程，相关定义和写入分析跨三个 Child。
- 人工审核：直接通过。人工审核：Candidate Gold 无需修改。
- [x] Query 是否合理
- [x] Relevant Child 是否正确
- [ ] 是否遗漏其他 Relevant Child（待完整 corpus omission check）
- 人工备注：

## pilot-014
- Query：采用“先更新数据库再删缓存”后，极端并发仍可能怎样读到旧值，又如何用 binlog 和重试收敛？
- Query Type：cross_chunk_boundary
- Topic Group：`cache_consistency`
- Candidate Parent：`1dca64e0-586d-48b8-85ef-ee3485a637f9`
- Candidate Child：`f0e4adc6-83b1-47c9-8aee-df5b578c16bf`、`126e7851-9146-4c9b-a8b3-a6ad0f674eec`、`da4c9ffd-140f-4491-aebf-606ec2dc737e`
- 对应原文：连续片段覆盖写库删缓存方案、读写线程交错产生旧缓存的小概率窗口，以及 Canal 订阅 binlog、消息队列重试删除。
- 候选理由：异常窗口、概率分析和最终一致补偿分别位于三个连续 Child。
- 人工审核：直接通过。人工审核：Candidate Gold 无需修改。
- [x] Query 是否合理
- [x] Relevant Child 是否正确
- [ ] 是否遗漏其他 Relevant Child（待完整 corpus omission check）
- 人工备注：

## pilot-015
- Query：热 Key 从压垮单分片到击穿数据库的链路是什么，如何治理并提前发现？
- Query Type：cross_chunk_boundary
- Topic Group：`redis_hot_key`
- Candidate Parent：`8562f1c8-f1d3-42e8-b19c-3c4c4e392854`
- Candidate Child：`e6f7faf0-07a5-4412-936d-b4e94b20f1bc`、`9c38c6cb-d7b6-471f-9c28-2727544858ac`、`5715943c-d7f0-4545-a9d7-1e69e6d348b7`
- 对应原文：三个连续片段依次描述分片资源倾斜和缓存击穿、拆分/降级与抓包统计，以及通过节点 CPU、带宽告警发现热点。
- 候选理由：风险、治理、检测分布在同 Parent 的三个 Child，必须联合标注。
- 人工审核：直接通过。人工审核：Candidate Gold 无需修改。
- [x] Query 是否合理
- [x] Relevant Child 是否正确
- [ ] 是否遗漏其他 Relevant Child（待完整 corpus omission check）
- 人工备注：

## pilot-016
- Query：生产集群应如何分别配置 HPA 与 VPA，并避免两套控制器互相干扰？
- Query Type：multi_parent_synthesis
- Topic Group：`hpa_vpa`
- Candidate Parent：`6f5603fe-c213-4aa7-aab4-71807769d72e`、`29a841de-29c4-4cef-a505-5538c4fc6c7f`、`eefff46b-4abc-4400-88fb-a705b8a8c182`、`c8bc8370-b646-4176-9a5a-d8ecacd5a481`、`dc8d324b-3112-44ad-8899-d2ff73ac3142`
- Candidate Child：`5a84c9fe-d0e2-4b60-b663-0fd823840284`、`4ce5d77d-cc81-406f-b23e-2bdf244edd18`、`c6f3e1f8-cfc5-4b56-852c-a778864d99e1`、`a7b8d05f-5168-418f-aa73-423eebe6ad1d`、`0253321d-f9a4-4121-bdce-58fd767991bc`
- 对应原文：HPA 调整副本，VPA 调整资源请求；生产配置还涉及指标隔离、CPU 阈值、冷却时间和 VPA 更新模式。
- 候选理由：任务横跨 HPA、VPA、冲突协调和两套配置共五个 Parent。
- 人工审核：直接通过。人工审核：Candidate Gold 无需修改。
- [x] Query 是否合理
- [x] Relevant Child 是否正确
- [ ] 是否遗漏其他 Relevant Child（待完整 corpus omission check）
- 人工备注：

## pilot-017
- Query：从底层组件到工程收益，FastAPI 为什么适合作为机器学习服务的 API 层？
- Query Type：multi_parent_synthesis
- Topic Group：`fastapi`
- Candidate Parent：`817487ad-38d1-456d-8c36-1000e15365f9`、`64f9e670-272a-4ac0-9735-fc9837bb0147`、`a9043b59-b8a7-4227-8e70-8051ddd51f22`、`156b220b-cf6f-4986-804e-73754954e741`
- Candidate Child：`a19f034a-ab26-4f53-97be-7a7b28cc6f52`、`3e7aa036-d7eb-4d93-ba6e-ea98f6847a57`、`af997fce-c3ce-442b-accd-dc790211fbc9`、`275e9feb-ebf1-46c6-8bf4-9199244f2136`
- 对应原文：Starlette/Pydantic 提供异步和校验，ASGI 带来高并发，OpenAPI 自动化降低联调成本，应用章节明确覆盖模型部署。
- 候选理由：架构、性能、标准化和应用场景位于四个不同 Parent。
- 人工审核：直接通过。人工审核：Candidate Gold 无需修改。
- [x] Query 是否合理
- [x] Relevant Child 是否正确
- [ ] 是否遗漏其他 Relevant Child（待完整 corpus omission check）
- 人工备注：

## pilot-018
- Query：设计实时文本推送方案时，应怎样结合 SSE 的协议机制、替代方案、典型用途与局限做选型？
- Query Type：multi_parent_synthesis
- Topic Group：`sse`
- Candidate Parent：`2df4c511-b356-406e-bf69-ec32a60a0df0`、`bbc63975-1526-4f56-b6e4-73002fd85513`、`d629c5af-47b9-4eca-9cbf-3cd9e07941b8`、`faddb4f2-2482-485b-b7ba-99a1787ad79c`
- Candidate Child：`7bd73b02-717e-434d-81a1-e4ba85440a91`、`3400f795-6752-47a1-819c-fc33f6733ef7`、`21f27a0c-c30a-4396-acd1-0e62088da327`、`0fb1b787-3f59-43d0-9f35-5303da075c85`
- 对应原文：四个章节分别说明 SSE 事件流协议、与 WebSocket/长轮询比较、AI/监控等场景，以及单向、兼容性和二进制限制。
- 候选理由：完整选型需要协议、比较、场景和限制四个 Parent。
- 人工审核：直接通过。人工审核：Candidate Gold 无需修改。
- [x] Query 是否合理
- [x] Relevant Child 是否正确
- [ ] 是否遗漏其他 Relevant Child（待完整 corpus omission check）
- 人工备注：

## pilot-019
- Query：请从数据能力、单机性能、I/O/事件模型和高可用机制解释 Redis 的核心技术特点。
- Query Type：multi_parent_synthesis
- Topic Group：`redis_architecture`
- Candidate Parent：`7628aa83-d4c2-4678-83b0-9e19001f9906`、`0abf7d70-2bff-4be9-be89-10f7f08d29e6`、`9808e98b-f72e-4664-95aa-097801d12443`、`e454c186-fb75-4945-bc2e-d6f3894bd350`
- Candidate Child：`1a763fce-c3ae-4b78-aff5-d2473ef3805e`、`45d707dc-27c2-4db0-ad7c-c7f7f6dbc432`、`7bce1e61-ee7d-479b-916a-4853022919de`、`d4121f65-aaf7-4e4e-b49f-9f08cee13d7f`
- 对应原文：Redis 支持多种数据结构、持久化和高可用；基准展示读写吞吐；非阻塞 I/O、多路复用和单线程事件模型解释性能来源。
- 候选理由：能力、基准、I/O 和内部原理来自四个 Parent。
- 人工审核：修正 Query 后通过。证据支持高可用，不足以支持“扩展方式”。
- [x] Query 是否合理
- [x] Relevant Child 是否正确
- [ ] 是否遗漏其他 Relevant Child（待完整 corpus omission check）
- 人工备注：

## pilot-020
- Query：一个可用于生产的 Redis 分布式锁，需要同时满足哪些语义并处理超时和节点故障？
- Query Type：multi_parent_synthesis
- Topic Group：`redis_lock`
- Candidate Parent：`81a99a66-19a8-4f48-a65e-2e53d2d22e51`、`16b311ed-3ce5-4de2-8588-b436fd9ca99e`、`9e0cf715-ea15-49ea-8142-d0464d6e9b70`、`fc889dc3-14f0-482a-9fe7-25fc15e92ca6`
- Candidate Child：`3751880e-f729-4df3-824e-dffb38f97fbe`、`dbbd479f-7ba9-4f4c-88cd-ae95be7b084b`、`1fa17e4e-8f23-4d54-8049-430f999fbb0e`、`e6dd8ca0-f495-4e6f-af0a-e85d1e3dd6e6`
- 对应原文：锁需要互斥、高可用、防死锁与可重入；SET NX PX 完成原子加锁；Watch Dog 处理提前过期；集群、哨兵或 Redlock 应对单点故障。
- 候选理由：需求、原子实现、超时续约和节点故障分别位于四个 Parent。
- 人工审核：直接通过。人工审核：Candidate Gold 无需修改。
- [x] Query 是否合理
- [x] Relevant Child 是否正确
- [ ] 是否遗漏其他 Relevant Child（待完整 corpus omission check）
- 人工备注：
