# Final 40 Retrieval Gold — New Candidate Review

> Frozen Pilot 20 条保持不变。以下仅为基于 Batch1 A/B 人工清洁证据生成的新增 20 条 Candidate；尚未冻结，未运行指标。

## Frozen Pilot

- Count: 20
- Status: frozen / unchanged

## candidate-021

Query Type: exact_keyword
Query: Redis 分布式锁释放时，requestId 校验和 Lua 脚本各负责什么？
Candidate Parent: 754b5be9-e39e-41ca-a38a-853052846b1c
Candidate Child: a3d8f9ec-9e3c-4b75-9d23-c6f423bc9911

Supporting evidence:
- Child a3d8f9ec-9e3c-4b75-9d23-c6f423bc9911 (Parent 754b5be9-e39e-41ca-a38a-853052846b1c, index 0): 解锁应校验 requestId；Lua 将 GET 校验和 DEL 合并为原子操作

Necessity rationale: 该 Child 同时说明 requestId 所有权校验与 Lua 原子释放，缺少它无法回答两个动作的关系。

人工审核：
[ ] Query是否合理
[ ] Relevant Child是否正确且必要
[ ] 是否遗漏其他 Relevant Child
人工备注：

## candidate-022

Query Type: exact_keyword
Query: Redis 2.6 对 Lua 和 redis-cli --eval 提供了哪些支持？
Candidate Parent: 8528ba93-fbb3-4f8a-b321-ebef5cf08c48
Candidate Child: 44b091a9-9303-455f-b3d4-82b7a4ebea80

Supporting evidence:
- Child 44b091a9-9303-455f-b3d4-82b7a4ebea80 (Parent 8528ba93-fbb3-4f8a-b321-ebef5cf08c48, index 0): Redis 2.6 支持 Lua；键过期精度支持毫秒；从节点支持只读；redis-cli 支持 --eval

Necessity rationale: 该 Child 直接给出 Redis 2.6 的 Lua 支持及 redis-cli --eval 能力。

人工审核：
[ ] Query是否合理
[ ] Relevant Child是否正确且必要
[ ] 是否遗漏其他 Relevant Child
人工备注：

## candidate-023

Query Type: exact_keyword
Query: Redisson 未指定 leaseTime 时，watchdog timeout 与锁等待重试机制如何关联？
Candidate Parent: d6ec4f7e-6ffb-4576-8719-85a80fa3a6e6
Candidate Child: 9b76a641-e132-42a7-99cd-d8449e424457

Supporting evidence:
- Child 9b76a641-e132-42a7-99cd-d8449e424457 (Parent d6ec4f7e-6ffb-4576-8719-85a80fa3a6e6, index 0): Redisson 使用线程标识和重入计数维护可重入锁；获取失败时返回 TTL 进入等待/重试流程；未显式指定 leaseTime 时文中给出默认 watchdog timeout

Necessity rationale: 该 Child 直接说明线程标识/重入计数、失败后的 TTL 等待，以及未显式指定 leaseTime 时的 watchdog timeout。

人工审核：
[ ] Query是否合理
[ ] Relevant Child是否正确且必要
[ ] 是否遗漏其他 Relevant Child
人工备注：

## candidate-024

Query Type: exact_keyword
Query: 排查 Redis 热 Key 或大 Key 时，bigkeys、memkeys、hotkeys 的用途如何区分？
Candidate Parent: 9714a0b5-0be5-4e3d-819e-2fc16ed0667b
Candidate Child: 8d4e0f65-1c79-4b7c-9f1a-5544eff04adf

Supporting evidence:
- Child 8d4e0f65-1c79-4b7c-9f1a-5544eff04adf (Parent 9714a0b5-0be5-4e3d-819e-2fc16ed0667b, index 0): Top Key 与离线全量分析的能力差异；bigkeys、memkeys、hotkeys 的用途差异

Necessity rationale: 该 Child 直接比较三类工具的用途。

人工审核：
[ ] Query是否合理
[ ] Relevant Child是否正确且必要
[ ] 是否遗漏其他 Relevant Child
人工备注：

## candidate-025

Query Type: exact_keyword
Query: Redisson 如何用 Hash、线程标识和 PEXPIRE 实现可重入锁？
Candidate Parent: 6b71fc8b-c55d-4a39-8eb3-b58d13f27908
Candidate Child: da1668e8-f06e-4181-b382-1feedc6d4187

Supporting evidence:
- Child da1668e8-f06e-4181-b382-1feedc6d4187 (Parent 6b71fc8b-c55d-4a39-8eb3-b58d13f27908, index 0): Redisson 可使用 Hash 中线程标识和计数实现可重入；Lua 同时维护计数和 PEXPIRE

Necessity rationale: 该 Child 直接说明可重入计数、线程标识与 PEXPIRE 的协作方式。

人工审核：
[ ] Query是否合理
[ ] Relevant Child是否正确且必要
[ ] 是否遗漏其他 Relevant Child
人工备注：

## candidate-026

Query Type: semantic_paraphrase
Query: 为什么并发写入时，即使采用删除缓存的顺序，仍可能把旧数据重新写进缓存？
Candidate Parent: 1dca64e0-586d-48b8-85ef-ee3485a637f9
Candidate Child: c8bb7bc9-148d-484b-8640-2c75872ffc94

Supporting evidence:
- Child c8bb7bc9-148d-484b-8640-2c75872ffc94 (Parent 1dca64e0-586d-48b8-85ef-ee3485a637f9, index 0): 并发更新数据库和缓存可能产生旧缓存覆盖新值；先删缓存再更新数据库存在读请求回填旧值窗口

Necessity rationale: 该 Child 说明读请求在删缓存与更新数据库间回填旧值的竞争窗口。

人工审核：
[ ] Query是否合理
[ ] Relevant Child是否正确且必要
[ ] 是否遗漏其他 Relevant Child
人工备注：

## candidate-027

Query Type: semantic_paraphrase
Query: 分布式锁把资源粒度设得过大，会怎样影响系统吞吐？
Candidate Parent: a1ab4335-d0fd-4e6b-9a8b-396b2bf16d60
Candidate Child: c3c1c313-3662-4dc7-bff6-309e3b9e45d1

Supporting evidence:
- Child c3c1c313-3662-4dc7-bff6-309e3b9e45d1 (Parent a1ab4335-d0fd-4e6b-9a8b-396b2bf16d60, index 0): 锁粒度过粗会降低并发；可按资源 ID 或分段方式细化锁；网络分区可能产生锁状态冲突

Necessity rationale: 该 Child 说明粗粒度锁降低并发，以及按资源 ID 或分段细化的方式。

人工审核：
[ ] Query是否合理
[ ] Relevant Child是否正确且必要
[ ] 是否遗漏其他 Relevant Child
人工备注：

## candidate-028

Query Type: semantic_paraphrase
Query: 单个 Redis Key 被大量访问时，为什么加机器通常不能自然消除热点？
Candidate Parent: 326cee13-9500-44e9-ace9-59c572173565
Candidate Child: 6e0f67c6-e44e-4597-823e-51ac8009e18e

Supporting evidence:
- Child 6e0f67c6-e44e-4597-823e-51ac8009e18e (Parent 326cee13-9500-44e9-ace9-59c572173565, index 0): 单一热 Key 会形成单实例热点；单纯扩容不能自动分散同一个 Key 的请求；可通过业务预估、客户端、代理层和 Redis 工具发现热 Key

Necessity rationale: 该 Child 直接解释同一 Key 的请求不会因普通扩容自动分散。

人工审核：
[ ] Query是否合理
[ ] Relevant Child是否正确且必要
[ ] 是否遗漏其他 Relevant Child
人工备注：

## candidate-029

Query Type: semantic_paraphrase
Query: Redis 大 Key 与热 Key 分别可能给集群资源带来什么压力？
Candidate Parent: f4329fc8-5cee-490a-916d-e8652922c191
Candidate Child: ac37d2dc-d755-422a-aa63-baa5d302b2ce

Supporting evidence:
- Child ac37d2dc-d755-422a-aa63-baa5d302b2ce (Parent f4329fc8-5cee-490a-916d-e8652922c191, index 3): 大 Key 可导致 rebalance/迁移失败和命令阻塞；热 Key 可造成单分片 CPU 与带宽压力

Necessity rationale: 该 Child 区分大 Key 的迁移/阻塞风险与热 Key 的单分片 CPU、带宽压力。

人工审核：
[ ] Query是否合理
[ ] Relevant Child是否正确且必要
[ ] 是否遗漏其他 Relevant Child
人工备注：

## candidate-030

Query Type: semantic_paraphrase
Query: 用 ZooKeeper 做锁时，客户端失联后锁为什么能被回收？
Candidate Parent: 3bf8c260-75f2-4e64-a26f-d365868822ef
Candidate Child: fb18e10b-3846-43da-8584-c83729afdfc3

Supporting evidence:
- Child fb18e10b-3846-43da-8584-c83729afdfc3 (Parent 3bf8c260-75f2-4e64-a26f-d365868822ef, index 0): 临时节点随客户端故障自动删除；Curator 提供可重入锁、不可重入锁、读写锁和 MultiLock

Necessity rationale: 该 Child 直接说明临时节点随客户端故障自动删除。

人工审核：
[ ] Query是否合理
[ ] Relevant Child是否正确且必要
[ ] 是否遗漏其他 Relevant Child
人工备注：

## candidate-031

Query Type: cross_chunk_boundary
Query: 设计 Redlock 时，释放锁怎样确认所有者，获取锁又以什么条件判定成功？
Candidate Parent: c6f8fca1-34f4-4b4a-b4b8-cf9de9ca82f8
Candidate Child: da6f4372-fa23-4d84-b2f3-98dd256253f0, b39ddde1-9b8a-46d1-bcfc-23c468c1634f

Supporting evidence:
- Child da6f4372-fa23-4d84-b2f3-98dd256253f0 (Parent c6f8fca1-34f4-4b4a-b4b8-cf9de9ca82f8, index 0): 解锁前必须校验锁持有者；Lua 可原子执行 compare-and-delete；单 Redis 实例存在单点故障风险
- Child b39ddde1-9b8a-46d1-bcfc-23c468c1634f (Parent c6f8fca1-34f4-4b4a-b4b8-cf9de9ca82f8, index 1): Redlock 在多个独立 Redis 实例上申请锁；使用随机唯一 value 标识锁所有者；多数实例成功是获取锁的核心条件

Necessity rationale: 前一 Child 给出 compare-and-delete 所有权校验，后一 Child 给出随机 value 与多数实例成功条件；两者缺一不可。

人工审核：
[ ] Query是否合理
[ ] Relevant Child是否正确且必要
[ ] 是否遗漏其他 Relevant Child
人工备注：

## candidate-032

Query Type: cross_chunk_boundary
Query: 为什么 Redis 主从切换仍可能丢锁？Redlock 在节点数、耗时与通信方式上需要满足哪些条件？
Candidate Parent: 96898c0d-61b5-4916-9173-a56f32759e8a
Candidate Child: 7854e15d-b9bf-4382-917f-be979ebca791, dfef6d0c-18a6-4651-9ad2-4cf3ed6aa4db

Supporting evidence:
- Child 7854e15d-b9bf-4382-917f-be979ebca791 (Parent 96898c0d-61b5-4916-9173-a56f32759e8a, index 0): Redis 主从异步复制可能导致故障切换后锁丢失；Redlock 要求至少 N/2+1 节点成功；获取耗时必须小于锁有效期
- Child dfef6d0c-18a6-4651-9ad2-4cf3ed6aa4db (Parent 96898c0d-61b5-4916-9173-a56f32759e8a, index 1): Redlock 节点可以彼此独立；客户端应保持低延迟通信；可使用多路复用并行发送 SET 请求

Necessity rationale: 前一 Child 给出异步复制风险、法定多数和有效期约束，后一 Child 给出独立节点、低延迟及并行 SET；两段共同构成完整回答。

人工审核：
[ ] Query是否合理
[ ] Relevant Child是否正确且必要
[ ] 是否遗漏其他 Relevant Child
人工备注：

## candidate-033

Query Type: cross_chunk_boundary
Query: 使用 ZooKeeper 管理分布式锁时，临时节点如何表示生命周期，长暂停又为什么仍需要资源层兜底？
Candidate Parent: 7d9a5147-3af8-4c2d-9cf3-4e0023d0ac76
Candidate Child: 3e1c8633-3aba-45ed-b7a8-d8ac46803fae, ca51e67f-0d3e-4452-902c-4ba2cea05965

Supporting evidence:
- Child 3e1c8633-3aba-45ed-b7a8-d8ac46803fae (Parent 7d9a5147-3af8-4c2d-9cf3-4e0023d0ac76, index 1): 文中区分分布式锁的互斥性与操作顺序性；ZooKeeper 可利用临时节点实现锁生命周期管理
- Child ca51e67f-0d3e-4452-902c-4ba2cea05965 (Parent 7d9a5147-3af8-4c2d-9cf3-4e0023d0ac76, index 2): ZooKeeper Session 通过心跳维持临时节点；长进程暂停可能导致 Session 过期及锁丢失；极端情况下分布式锁不能替代资源层一致性兜底

Necessity rationale: 前一 Child 说明临时节点机制，后一 Child 说明心跳、Session 过期与资源一致性边界。

人工审核：
[ ] Query是否合理
[ ] Relevant Child是否正确且必要
[ ] 是否遗漏其他 Relevant Child
人工备注：

## candidate-034

Query Type: cross_chunk_boundary
Query: 发现 Redis 大 Key/热 Key 后，应分别怎样定位、处理和避免高风险删除？
Candidate Parent: 9714a0b5-0be5-4e3d-819e-2fc16ed0667b
Candidate Child: f24fcfdb-a666-43e3-8908-51a4c427aeb3, b450fa80-4dae-4451-80c6-5a5e5ed9cd63

Supporting evidence:
- Child f24fcfdb-a666-43e3-8908-51a4c427aeb3 (Parent 9714a0b5-0be5-4e3d-819e-2fc16ed0667b, index 1): STRLEN/LLEN/HLEN/SCARD/ZCARD/XLEN 可辅助分析不同类型 Key；MONITOR 会消耗资源，不建议长期使用；业务层或 RDB 工具可定位热点/大 Key
- Child b450fa80-4dae-4451-80c6-5a5e5ed9cd63 (Parent 9714a0b5-0be5-4e3d-819e-2fc16ed0667b, index 2): 大 Key 可通过清理、压缩、拆分、转存处理；UNLINK 可异步删除大 Key；热 Key 可通过副本或读写分离缓解，但存在一致性权衡

Necessity rationale: 前一 Child 提供分析命令及 MONITOR 限制，后一 Child 给出大 Key 的 UNLINK 和热 Key 副本方案；两个连续 Child 分别提供定位与处置。

人工审核：
[ ] Query是否合理
[ ] Relevant Child是否正确且必要
[ ] 是否遗漏其他 Relevant Child
人工备注：

## candidate-035

Query Type: cross_chunk_boundary
Query: Redisson 获取锁失败后如何避免忙等，同时又如何在业务未结束时避免锁过期？
Candidate Parent: d6ec4f7e-6ffb-4576-8719-85a80fa3a6e6
Candidate Child: f853d0c7-270a-46da-9eee-4e4d526ee648, fc9f1a15-0a08-45ed-b5bb-08dc214659b4

Supporting evidence:
- Child f853d0c7-270a-46da-9eee-4e4d526ee648 (Parent d6ec4f7e-6ffb-4576-8719-85a80fa3a6e6, index 1): 获取失败后不会简单忙轮询；使用 Pub/Sub 等待锁释放通知；重试受到剩余 waitTime/TTL 限制
- Child fc9f1a15-0a08-45ed-b5bb-08dc214659b4 (Parent d6ec4f7e-6ffb-4576-8719-85a80fa3a6e6, index 2): Redisson 重试通过等待与唤醒避免持续占用 CPU；WatchDog 在业务未完成时周期性续约；正常释放后停止续约，客户端异常后最终由 TTL 释放

Necessity rationale: 前一 Child 给出 Pub/Sub 等待和 waitTime/TTL 限制，后一 Child 给出等待唤醒与 WatchDog 续约；缺一无法完整回答。

人工审核：
[ ] Query是否合理
[ ] Relevant Child是否正确且必要
[ ] 是否遗漏其他 Relevant Child
人工备注：

## candidate-036

Query Type: multi_parent_synthesis
Query: 面对长时间进程暂停，为什么固定租约锁不够安全？资源服务还应如何拒绝过期持有者的写入？
Candidate Parent: 8649c414-cfd1-4a2c-bc6d-45ccf00e7ef9, 7d9a5147-3af8-4c2d-9cf3-4e0023d0ac76
Candidate Child: c4145c16-3a0d-438f-8b4f-4156e0e68206, 1cc83662-096d-4bb9-be35-bc9a7e8b844c

Supporting evidence:
- Child c4145c16-3a0d-438f-8b4f-4156e0e68206 (Parent 8649c414-cfd1-4a2c-bc6d-45ccf00e7ef9, index 0): 进程暂停和网络延迟可能持续很长时间；这类暂停会破坏基于固定租约时间的安全假设；必须结合相邻上下文使用
- Child 1cc83662-096d-4bb9-be35-bc9a7e8b844c (Parent 7d9a5147-3af8-4c2d-9cf3-4e0023d0ac76, index 0): fencing token 要求资源服务器能够拒绝旧 token；文中讨论使用随机锁 value 配合资源侧校验的方案

Necessity rationale: 第一个 Parent 说明长暂停破坏固定租约假设，第二个 Parent 说明 fencing token 与资源侧拒绝旧 token 的兜底。

人工审核：
[ ] Query是否合理
[ ] Relevant Child是否正确且必要
[ ] 是否遗漏其他 Relevant Child
人工备注：

## candidate-037

Query Type: multi_parent_synthesis
Query: 网络延迟排查中，如何结合 Ping 的 RTT/TTL 与 traceroute 的 Hop 路径判断问题位置？
Candidate Parent: 3c0ae026-3b0b-4fa7-8dd2-e78e0b3922af, b868aae6-1c92-43e7-ba9c-c2a17d78e9fe
Candidate Child: 7900c458-dc24-41a4-93c1-3fca0890926b, 79ee9853-ab18-4e37-b727-a87c643ab063

Supporting evidence:
- Child 7900c458-dc24-41a4-93c1-3fca0890926b (Parent 3c0ae026-3b0b-4fa7-8dd2-e78e0b3922af, index 0): Ping 正常结果包含 RTT、TTL 等字段；Unknown host 对应名称解析问题；Destination host unreachable 对应路由问题；Request timed out 可能与不可达或 ICMP 丢弃有关
- Child 79ee9853-ab18-4e37-b727-a87c643ab063 (Parent b868aae6-1c92-43e7-ba9c-c2a17d78e9fe, index 1): Ping 测 RTT 与目标连接稳定性；Traceroute 展示数据包经过的 Hop 路径

Necessity rationale: 两个 Parent 分别提供 Ping 结果字段含义和 traceroute 的路径观测能力，均为诊断步骤所必需。

人工审核：
[ ] Query是否合理
[ ] Relevant Child是否正确且必要
[ ] 是否遗漏其他 Relevant Child
人工备注：

## candidate-038

Query Type: multi_parent_synthesis
Query: 若用 ZooKeeper 代替 Redis 锁，前驱节点监听的获取流程与 Curator 可选锁类型如何配合设计？
Candidate Parent: ecef5995-40fc-46e1-b67b-bd8a2ed1550a, 3bf8c260-75f2-4e64-a26f-d365868822ef
Candidate Child: 398521a8-0d16-4f5d-9575-165f972e6ad5, fb18e10b-3846-43da-8584-c83729afdfc3

Supporting evidence:
- Child 398521a8-0d16-4f5d-9575-165f972e6ad5 (Parent ecef5995-40fc-46e1-b67b-bd8a2ed1550a, index 0): ZooKeeper 使用临时有序节点竞争锁；未获得锁的客户端监听前驱节点；前驱释放后重新判断是否获得锁
- Child fb18e10b-3846-43da-8584-c83729afdfc3 (Parent 3bf8c260-75f2-4e64-a26f-d365868822ef, index 0): 临时节点随客户端故障自动删除；Curator 提供可重入锁、不可重入锁、读写锁和 MultiLock

Necessity rationale: 第一个 Parent 给出有序临时节点和前驱监听流程，第二个 Parent 给出 Curator 支持的锁类型；两者分别回答流程和实现选择。

人工审核：
[ ] Query是否合理
[ ] Relevant Child是否正确且必要
[ ] 是否遗漏其他 Relevant Child
人工备注：

## candidate-039

Query Type: multi_parent_synthesis
Query: 高并发读多写少场景中，读写锁的互斥规则与 Redis 锁提前过期风险分别怎样影响方案选择？
Candidate Parent: 66e4aba4-de05-4609-bdfe-bc2c0396dc5b, e3dc0571-855c-4072-8f34-20a1fe5de99b
Candidate Child: f358f7db-de57-4f73-bd5a-9799f2906cb4, ff651920-a885-4987-a701-a674ef6f6afd

Supporting evidence:
- Child f358f7db-de57-4f73-bd5a-9799f2906cb4 (Parent 66e4aba4-de05-4609-bdfe-bc2c0396dc5b, index 0): 读锁之间可共享；读写、写写需要互斥；分段锁可以降低锁粒度提高并发
- Child ff651920-a885-4987-a701-a674ef6f6afd (Parent e3dc0571-855c-4072-8f34-20a1fe5de99b, index 0): 锁先过期而业务未完成可能导致误删其他客户端的锁；唯一客户端 ID 可标识锁所有权；SET NX EX/PX 与 Lua 解锁用于提高原子性

Necessity rationale: 第一个 Parent 给出读读共享、写互斥规则，第二个 Parent 说明过期后旧客户端误删他人锁的风险；比较两种约束需要两段证据。

人工审核：
[ ] Query是否合理
[ ] Relevant Child是否正确且必要
[ ] 是否遗漏其他 Relevant Child
人工备注：

## candidate-040

Query Type: multi_parent_synthesis
Query: 制定 Redis Key 治理方案时，如何从热点成因、单实例影响以及大 Key 的资源不均三个方面确定优先级？
Candidate Parent: 326cee13-9500-44e9-ace9-59c572173565, 9714a0b5-0be5-4e3d-819e-2fc16ed0667b
Candidate Child: 6e0f67c6-e44e-4597-823e-51ac8009e18e, da28c124-72d6-44b8-9232-0f30c8553b09

Supporting evidence:
- Child 6e0f67c6-e44e-4597-823e-51ac8009e18e (Parent 326cee13-9500-44e9-ace9-59c572173565, index 0): 单一热 Key 会形成单实例热点；单纯扩容不能自动分散同一个 Key 的请求；可通过业务预估、客户端、代理层和 Redis 工具发现热 Key
- Child da28c124-72d6-44b8-9232-0f30c8553b09 (Parent 9714a0b5-0be5-4e3d-819e-2fc16ed0667b, index 3): 大 Key 常由数据过大、成员过多或无效数据累积产生；热 Key 可由突发访问量产生；大 Key 会导致内存和分片资源不均

Necessity rationale: 第一个 Parent 说明同 Key 热点与单实例压力，第二个 Parent 说明大 Key 的成因和内存/分片不均；两者共同支持优先级判断。

人工审核：
[ ] Query是否合理
[ ] Relevant Child是否正确且必要
[ ] 是否遗漏其他 Relevant Child
人工备注：
