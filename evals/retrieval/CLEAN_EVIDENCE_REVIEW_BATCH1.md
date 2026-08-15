# Clean Evidence Review — Batch 1

> 仅包含 Frozen Pilot 未使用的 Child。自动检查仅处理文本长度、抓取噪声与完全重复；不会判定 Gold、相关性或 Evidence 组合。

## Parent 91c8f8a0-6b2f-48d3-aaf8-f0a42ac6532c

Document: 432f4fa9-96de-45ba-b50f-03abbef1c432 — Redis 分布式锁原理简述，控制在500字以内
Section: 参考文献
Parent ID: 91c8f8a0-6b2f-48d3-aaf8-f0a42ac6532c

### Child 1
Child ID: 881ee352-b7c6-4fa1-83c8-e1f802d1f129
Child Index: 0
Estimated Token Count: 423
正文：
<a id="ref-14"></a>**[14]** redis.io — Redis lock: fast distributed locking explained URL: https://redis.io/glossary/redis-lock 原文片段：「Redis lock: fast distributed locking explained 97% believe in it. 4% have built it. New research: State of context engineering. Read the report Resource Center Events & webinars Blog Videos Glossary Resources Architecture Diagrams Demo Center Resource Center Events & webinars Blo...」 <a id="ref-15"></a>**[15]** redis.io — Distributed Locks with Redis | Docs URL: https://redis.io/docs/latest/develop/clients/patterns/distributed-locks 原文片段：「Distributed Locks with Redis | Docs {"categories":["docs","develop","stack","oss","rs","rc","oss","kubernetes","clients"],"description":"A distributed lock pattern with Redis\n","duplicateOf":"head:data-ai-metadata","location":"body","title":"Distributed Locks with Redis","tableO...」 <a id="ref-16"></a>**[16]** redisson.pro — What Is a Redis Lock? | Redisson URL: https://redisson.pro/glossary/redis-lock.html 原文片段：「What Is a Redis Lock? | Redisson What Is a Redis Lock? A Redis lock is a distributed lock that uses Valkey or Redis as the shared coordination point, so that only one process at a time may operate on a giv
自动质量检查：
- navigation_noise: yes
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 2
Child ID: 5224115d-af43-447a-a96f-ae12459c0d9b
Child Index: 1
Estimated Token Count: 280
正文：
Redis lock is a distributed lock that uses Valkey or Redis as the shared coordination point, so that only one process at a time may operate on a given resource — even when those processes run on different servers. The lock...」 <a id="ref-17"></a>**[17]** alibabacloud.com — Implementation Principles and Best Practices of Distributed Lock - Alibaba Cloud Community URL: https://www.alibabacloud.com/blog/implementation-principles-and-best-practices-of-distributed-lock_600811 原文片段：「Implementation Principles and Best Practices of Distributed Lock - Alibaba Cloud Community Community Blog Events Webinars Tutorials Forum Blog Events Webinars Tutorials Forum Create Account Log In × Community Blog Implementation Principles and Best Practices of Distributed Lock I...」 <a id="ref-18"></a>**[18]** zhuanlan.zhihu.com — zhuanlan.zhihu.com URL: https://zhuanlan.zhihu.com/p/745274384
自动质量检查：
- navigation_noise: yes
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent c6f8fca1-34f4-4b4a-b4b8-cf9de9ca82f8

Document: c59026f2-b03f-411d-a9a1-de356de33b32 — Implementing Distributed Locks with Redis Delving into SETNX, Redlock, and Their Controversies | Leapcell
Section: print(f"Another client holds the lock.")
Parent ID: c6f8fca1-34f4-4b4a-b4b8-cf9de9ca82f8

### Child 1
Child ID: da6f4372-fa23-4d84-b2f3-98dd256253f0
Child Index: 0
Estimated Token Count: 347
正文：
Critical Consideration for Release: When releasing the lock, it's crucial to verify that the client attempting to release the lock is indeed the one that acquired it. Otherwise, a client might accidentally (or maliciously) delete a lock held by another client, if its own lock expired and another client re-acquired it during its critical section. The Lua script above correctly handles this by atomically checking the value before deleting. Introducing Redlock Algorithm While a single Redis instance with SET ... NX EX provides reasonable distributed lock semantics for many scenarios, it has a single point of failure. If the Redis instance goes down (and is not immediately recovered or data is lost), all held locks are lost, leading to lost mutual exclusion. This is where Redlock, a distributed lock algorithm designed by Salvatore Tridici (Redis's creator), comes into play. Redlock's Goal: Redlock aims to provide a more robust and fault-tolerant distributed lock across multiple independent Redis instances. The core idea is to ac
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 2
Child ID: b39ddde1-9b8a-46d1-bcfc-23c468c1634f
Child Index: 1
Estimated Token Count: 284
正文：
lock algorithm designed by Salvatore Tridici (Redis's creator), comes into play. Redlock's Goal: Redlock aims to provide a more robust and fault-tolerant distributed lock across multiple independent Redis instances. The core idea is to ac quire locks on a majority of Redis instances rather than just one. Redlock Algorithm Steps: Assume N independent Redis master instances, and the client needs to acquire a lock with a resource_name and a validity_time (how long the lock is considered valid). Generate a Random Value: The client generates a random, unique value (e.g., a large random string or UUID) that will be used as its "signature" for the lock. This value is used to safely release the lock later. Acquire on Instances (Parallel): The client attempts to acquire the lock ( SET resource_name my_rand_value NX PX validity_time_milliseconds ) on
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent 96898c0d-61b5-4916-9173-a56f32759e8a

Document: 21e8b222-9333-40a0-80e4-cec82d5b19cf — Full-Stack-Notes/notes/Redis_分布式锁原理.md at master · heibaiying/Full-Stack-Notes · GitHub
Section: Full-Stack-Notes/notes/Redis_分布式锁原理.md at master · heibaiying/Full-Stack-Notes · GitHub
Parent ID: 96898c0d-61b5-4916-9173-a56f32759e8a

### Child 1
Child ID: 7854e15d-b9bf-4382-917f-be979ebca791
Child Index: 0
Estimated Token Count: 850
正文：
s 分布式锁，而想要保证 Redis 分布式锁是高可用，首先 Redis 得是高可用的，Redis 的高可用模式主要有两种：哨兵模式和集群模式。以下分别进行讨论： 二、哨兵模式与分布式锁 哨兵模式是主从模式的升级版，能够在故障发生时自动进行故障切换，选举出新的主节点。但由于 Redis 的复制机制是异步的，因此在哨兵模式下实现的分布式锁是不可靠的，原因如下： 由于主从之间的复制操作是异步的，当主节点上创建好锁后，此时从节点上的锁可能尚未创建。而如果此时主节点发生了宕机，从节点上将不会创建该分布式锁； 从节点晋升为主节点后，其他进程（或线程）仍然可以在该新主节点创建分布式锁，此时就存在多个进程（或线程）同时进入了临界区，分布式锁就失效了。 因此在哨兵模式下，无法避免锁失效的问题。因此想要实现高可用的分布式锁，可以采取 Redis 的另一个高可用方案 —— Redis 集群模式。 三、集群模式与分布式锁 3.1 RedLock 方案 想要在集群模式下实现分布式锁，Redis 提供了一种称为 RedLock 的方案，假设我们有 N 个 Redis 实例，此时客户端的执行过程如下： 以毫秒为单位记录当前的时间，作为开始时间； 接着采用和单机版相同的方式，依次尝试在每个实例上创建锁。为了避免客户端长时间与某个故障的 Redis 节点通讯而导致阻塞，这里采用快速轮询的方式：假设创建锁时设置的超时时间为 10 秒，则访问每个 Redis 实例的超时时间可能在 5 到 50 毫秒之间，如果在这个时间内还没有建立通信，则尝试连接下一个实例； 如果在至少 N/2+1 个实例上都成功创建了锁。并且 当前时间 - 开始时间 < 锁的超时时间 ，则认为已经获取了锁，锁的有效时间等于 超时时间 - 花费时间 （如果考虑不同 Redis 实例所在服务器的时钟漂移，则还需要减去时钟漂移）； 如果少于 N/2+1 个实例，则认为创建分布式锁失败，此时需要删除这些实例上已创建的锁，以便其他客户端进行创建。 该客户端在失败后，可以等待一个随机的时间后，再次进行重试。 以上就是 RedLock 的实现方案，可以看到主要是由客户端来实现的，并不真正涉及到 Redis 集群相关的功能。因此这里的 N 个 Redis 实例并不要求是一个真正的 Redis 集群，它们彼此之间可以是完全独立的，但由于只需要半数节点获得锁就能真正获得锁，因此其仍然具备容错性和高可用性。后面使用 Redisson
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 2
Child ID: dfef6d0c-18a6-4651-9ad2-4cf3ed6aa4db
Child Index: 1
Estimated Token Count: 219
正文：
此这里的 N 个 Redis 实例并不要求是一个真正的 Redis 集群，它们彼此之间可以是完全独立的，但由于只需要半数节点获得锁就能真正获得锁，因此其仍然具备容错性和高可用性。后面使用 Redisson 来演示 RedLock 时会再次验证这一点。 3.2 低延迟通讯 另外实现 RedLock 方案的客户端与所有 Redis 实例进行通讯时，必须要保证低延迟，而且最好能使用多路复用技术来保证一次性将 SET 命令发送到所有 Redis 节点上，并获取到对应的执行结果。如果网络延迟较高，假设客户端 A 和 B 都在尝试创建锁： SET key 随机数A EX 3 NX
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent 7d9a5147-3af8-4c2d-9cf3-4e0023d0ac76

Document: e33ff6d9-67f2-4b1b-8ff5-0d83ac6de4e9 — Redis Redlock 的争论 - Redis 文档
Section: Redis Redlock 的争论 - Redis 文档
Parent ID: 7d9a5147-3af8-4c2d-9cf3-4e0023d0ac76

### Child 1
Child ID: 1cc83662-096d-4bb9-be35-bc9a7e8b844c
Child Index: 0
Estimated Token Count: 660
正文：
k、Zookeeper 都无能为力 所以，Redis 作者认为 Redlock 在保证时钟正确的基础上，是可以保证正确性的。 质疑 fencing token 机制 Redis 作者对于对方提出的 fecing token 机制，也提出了质疑，主要分为 2 个问题 第一共享资源服务器能拒绝旧 token 这个方案必须要求要操作的「共享资源服务器」有拒绝「旧 token」的能力。 假设共享资源服务器是 MySQL，我们要操作 MySQL，从锁服务拿到一个递增数字的 token， 然后客户端要带着这个 token 去改 MySQL 的某一行，这就需要利用 MySQL 的「事物隔离性」来做。 SQL // 两个客户端必须利用事物和隔离性达到目的 // 注意 token 的判断条件 UPDATE table T SET val = $ new_val WHERE id = $ id AND current_token < $ token 但如果操作的不是 MySQL 而是向磁盘上写一个文件，或发起一个 HTTP 请求，那这个方案就无能为力了，这对要操作的资源服务器，提出了更高的要求。 再者，既然资源服务器都有了「互斥」能力，那还要分布式锁干什么？ 所以，Redis 作者认为这个方案是站不住脚的。 第二 Redlock 已经提供了随机值 Redlock “实现” fecing token 退一步讲，即使 Redlock 没有提供 fecing token 的能力，但 Redlock 已经提供了随机值（就是之前讲的 UUID），利用这个随机值，也可以达到与 fecing token 同样的效果。 客户端使用 Redlock 拿到锁 客户端在操作共享资源之前，先把这个锁的 VALUE，在要操作的共享资源上做标记 客户端处理业务逻辑，最后，在修改共享资源时，判断这个标记是否与之前一样，一样才修改（类似 CAS 的思路） 还是以 MySQL 为例,这个实现如下 客户端使用 Redlock 拿到锁 客户端要修改 MySQL 表中的某一行数据之前，先把锁的 VALUE 更新到这一行的某个字段中（这里假设为 current_token 字段) 客户端处理业务逻辑 客户端修改 MySQL 的这一行数据，把 VALUE 当做 WHERE 条件，再修改 SQL UPDATE table T SET val = $ new_val WHERE id = $ id AND cu
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 2
Child ID: 3e1c8633-3aba-45ed-b7a8-d8ac46803fae
Child Index: 1
Estimated Token Count: 792
正文：
更新到这一行的某个字段中（这里假设为 current_token 字段) 客户端处理业务逻辑 客户端修改 MySQL 的这一行数据，把 VALUE 当做 WHERE 条件，再修改 SQL UPDATE table T SET val = $ new_val WHERE id = $ id AND cu rrent_token = $ redlock_value 可见，这种方案通过依赖 MySQL 的事物机制，也达到对方提到的 fecing token 一样的效果。 操作顺序 对于上述通过 Redlock “实现” fecing token 的设计，网友提出了一个问题：两个客户端通过这种方案，先「标记」再「检查 + 修改」共享资源，那这两个客户端的操作顺序无法保证啊？ 而用 Martin 提到的 fecing token，因为这个 token 是单调递增的数字，资源服务器可以拒绝小的 token 请求，保证了操作的「顺序性」！ Redis 作者对这问题做了不同的解释,我觉得非常有意思，他认为：分布式锁的本质，是为了「互斥」，只要能保证两个客户端在并发时，一个成功，一个失败就好了，不需要关心「顺序性」。 前面 Martin 的质疑中，一直很关心这个顺序性问题，但 Redis 的作者的看法却不同。 综上，Redis 作者的结论： 作者同意对方关于「时钟跳跃」对 Redlock 的影响，但认为时钟跳跃是可以避免的，取决于基础设施和运维。 Redlock 在设计时，充分考虑了 NPC 问题，在 Redlock 步骤 3 之前出现 NPC，可以保证锁的正确性，但在步骤 3 之后发生 NPC，不止是 Redlock 有问题，其它分布式锁服务同样也有问题，所以不在讨论范畴内。 基于 Zookeeper 的分布式锁 Martin 在他的文章中，推荐使用 Zookeeper 实现分布式锁，认为它更安全 Zookeeper 又是如何实现的分布式锁的呢？ 客户端 1 和 2 都尝试创建「临时节点」，例如 /lock 假设客户端 1 先到达，则加锁成功，客户端 2 加锁失败 客户端 1 操作共享资源 客户端 1 删除 /lock 节点，释放锁 Zookeeper 不像 Redis 那样，需要考虑锁的过期时间问题，它是采用了「临时节点」，保证客户端 1 拿到锁后，只要连接不断，就可以一直持有锁。 如果客户端 1 异常崩溃了，那么这个临时节点会自动删除，保证了锁一定会被释放。 关于 Zookeeper 实现分布式锁的具体详情，参考 Zookeeper 实现分布式锁 保持持有锁 客户端 1 创建临时节点后，Zookeeper 是如何保证让这个客户端一直持有锁呢？ 原因就在于，客户端 1 此时会与 Zookeeper 服务器维护一个 Session，这个 Session 会依
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 3
Child ID: ca51e67f-0d3e-4452-902c-4ba2cea05965
Child Index: 2
Estimated Token Count: 855
正文：
情，参考 Zookeeper 实现分布式锁 保持持有锁 客户端 1 创建临时节点后，Zookeeper 是如何保证让这个客户端一直持有锁呢？ 原因就在于，客户端 1 此时会与 Zookeeper 服务器维护一个 Session，这个 Session 会依 赖客户端「定时心跳」来维持连接。 如果 Zookeeper 长时间收不到客户端的心跳，就认为这个 Session 过期了，也会把这个临时节点删除。 Zookeeper 分布式锁下的 NPC 问题 同样的 Zookeeper 的分布式锁也存在 NPC 问题，以进程暂停为例 客户端 1 创建临时节点 /lock 成功，拿到了锁 客户端 1 发生长时间进程暂停 客户端 1 无法给 Zookeeper 发送心跳，Zookeeper 把临时节点「删除」 客户端 2 创建临时节点 /lock 成功，拿到了锁 客户端 1 进程暂停结束，它仍然认为自己持有锁（冲突） 可见，即使是使用 Zookeeper，也无法保证进程暂停、网络延迟异常场景下的安全性。 这就是前面 Redis 作者在反驳的文章中提到的：如果 进程暂停、网络延迟是发生在客户端拿到锁之后，那不止 Redlock 有问题，其它锁服务都有类似的问题。 这里我们可以得出一个结论： 一个分布式锁，在极端情况下，不一定是安全的。 Zookeeper 分布式锁的优缺点 Zookeeper 的优点： 不需要考虑锁的过期时间 watch 机制，加锁失败，可以 watch 等待锁释放，实现乐观锁 但它的劣势是： 性能不如 Redis 部署和运维成本高 客户端与 Zookeeper 的长时间失联，锁被释放问题 到底要不要用 Redlock？ 前面也分析了，Redlock 只有建立在「时钟正确」的前提下，才能正常工作，如果你可以保证这个前提，那么可以拿来使用。 但保证时钟正确，并不是简单 第一，从硬件角度来说，时钟发生偏移是时有发生，无法避免。例如，CPU 温度、机器负载、芯片材料都是有可能导致时钟发生偏移的。 第二，人为错误也是很难完全避免，运维暴力修改时钟，进而影响了系统的正确性 所以，我对 Redlock 的个人看法是，尽量不用它，而且它的性能不如单机版 Redis，部署成本也高，建议优先考虑使用主从 + 哨兵的模式 实现分布式锁 那怎么保证正确性了？ 正确使用分布式锁 从上面我们也了解到，任何分布式锁都无法完全保证正确性，因此分布式锁时建议 在上层使用分布式锁完成「互斥」目的，虽然极端情况下锁会失效，但它可以最大程度把并发请求阻挡在最上层，减轻操作资源层的压力。 但对于要求数据绝对正确的业务，在资源层一定要做好「兜底」，发生极端情况时，也不会对系统造成影响 回到页面顶部
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent b868aae6-1c92-43e7-ba9c-c2a17d78e9fe

Document: 4b506b6c-36fc-464f-9827-52b95bcc1185 — How to Test Network Latency and Diagnose Lag Like a Pro | Premier Broadband
Section: How to Test Network Latency and Diagnose Lag Like a Pro | Premier Broadband
Parent ID: b868aae6-1c92-43e7-ba9c-c2a17d78e9fe

### Child 1
Child ID: 79ee9853-ab18-4e37-b727-a87c643ab063
Child Index: 1
Estimated Token Count: 448
正文：
first half of 2025. It highlighted some huge differences across the US, showing T-Mobile leading mobile 5G with a median latency of 45ms . On the other hand, AT&T Fiber came in as the fixed broadband leader at just 18ms . These numbers, collected from real users, are exactly why fiber providers like Premier Broadband consistently deliver a better experience for anything that can't tolerate lag. You can see all the details in Ookla's comprehensive report . Using Built-In Command-Line Tools When you need to dig a little deeper, your computer's own command-line interface has some seriously powerful tools. They might look a bit old-school, but they provide a level of detail that web-based tests just can't offer. Ping: This is your fundamental latency tester. It sends a tiny data packet to a server and times how long it takes to come back—the round-trip time (RTT) , measured in milliseconds. It’s perfect for checking your live connection stability to a specific destination, like a gaming server or your office VPN. Traceroute (or tracert on Windows): Think of this as a roadmap for your data. It maps out the entire journey from your computer to the server, showing you every single "hop" i
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent c7c8599f-a951-45a3-af66-9003484fc2de

Document: 679327fc-31db-4a8a-8abe-19891309abce — 帮我写一个FastAPI 的报告，要求300字左右
Section: 参考文献
Parent ID: c7c8599f-a951-45a3-af66-9003484fc2de

### Child 1
Child ID: 0727ac9b-a72e-485c-bb0f-e2afbab30777
Child Index: 0
Estimated Token Count: 455
正文：
<a id="ref-11"></a>**[11]** github.com — GitHub - fastapi/fastapi: FastAPI framework, high performance, easy to learn, fast to code, ready for production · GitHub URL: https://github.com/fastapi/fastapi 原文片段：「GitHub - fastapi/fastapi: FastAPI framework, high performance, easy to learn, fast to code, ready for production · GitHub Skip to content You signed in with another tab or window. Reload to refresh your session. You signed out in another tab or window. Reload to refresh your sess...」 <a id="ref-12"></a>**[12]** fastapi.tiangolo.com — 教學 - 使用者指南 - FastAPI URL: https://fastapi.tiangolo.com/zh-hant/tutorial 原文片段：「教學 - 使用者指南 - FastAPI 跳轉至 Deploy on FastAPI Cloud 🚀 FastAPI Conf '26 — Oct 28, 2026, Amsterdam 🎤 Follow @fastapi on X (Twitter) to stay updated Follow FastAPI on LinkedIn to stay updated Subscribe to the FastAPI and friends newsletter 🎉 sponsor sponsor sponsor sponsor sponsor spon...」 <a id="ref-13"></a>**[13]** docs.posit.co — FastAPI – Connect Documentation Version 2026.07.0 URL: https://docs.posit.co/connect/user/fastapi 原文片段：「FastAPI – Connect Documentation Version 2026.07.0 Documentation Version You are viewing version 2026.07.0 . View the latest version . Enhanced A
自动质量检查：
- navigation_noise: yes
- text_complete: yes
- obvious_duplicate: no
- auto_status: unusable_candidate
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 2
Child ID: 04dc005d-210b-4537-ac99-54ebcb5048dc
Child Index: 1
Estimated Token Count: 486
正文：
2026.07.0 Documentation Version You are viewing version 2026.07.0 . View the latest version . Enhanced Advanced FastAPI is a Python ASGI web API framework. FastAPI uses type annotations and Pydantic models to provide input validation and au...」 <a id="ref-14"></a>**[14]** planeks.net — Захищена сторінка URL: https://www.planeks.net/pros-and-cons-of-fastapi 原文片段：「Захищена сторінка захищено adm.tools 134.195.101.74 — 2026-08-09T16:34:41.527Z Щоб переглянути сайт, увімкніть JavaScript у своєму браузері Навіщо включати JavaScript? З вашої IP-адреси було зафіксовано діяльність шкідливих програм. Увімкнення JavaScript дозволить нам переконатис...」 <a id="ref-15"></a>**[15]** codecademy.com — FastAPI vs Flask: Key Differences, Performance, and Use Cases | Codecademy URL: https://www.codecademy.com/article/fastapi-vs-flask-key-differences-performance-and-use-cases 原文片段：「FastAPI vs Flask: Key Differences, Performance, and Use Cases | Codecademy Skip to Content Articles FastAPI vs Flask: Key Differences, Performance, and Use Cases Codecademy Team Share Contents If you are starting to build web apps and APIs in Python, you will hear about Flask and...」 <a id="ref-16"></a>**[16]** geeksforgeek
自动质量检查：
- navigation_noise: yes
- text_complete: yes
- obvious_duplicate: no
- auto_status: unusable_candidate
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 3
Child ID: 7cb50cf1-a34a-413b-a1eb-65b3f63a1e4a
Child Index: 2
Estimated Token Count: 411
正文：
- GeeksforGeeks Courses Tutorials Interview Prep Python Tutorial Data Types Interview Questions Examples Quizzes DSA Python Data Science NumPy Pandas Practice Django Flask Introduction to FastAPI Last Updated : 20 Jun, 2026 FastAPI is a modern Python web f...」 <a id="ref-17"></a>**[17]** yeonwoosung.github.io — Pros and Cons of FastAPI | YeonwooSung's Blog URL: https://yeonwoosung.github.io/posts/pros-and-cons-of-fastapi 原文片段：「Pros and Cons of FastAPI | YeonwooSung's Blog YeonwooSung's Blog As I've always been Home Pros and Cons of FastAPI Post Cancel Pros and Cons of FastAPI Posted Jun 21, 2023 By 1 min read Pros FastAPI is very fast and efficient, making it a great choice for building high-performanc...」 <a id="ref-18"></a>**[18]** dev.to — FastAPI - The Good, the bad and the ugly. - DEV Community URL: https://dev.to/fuadrafid/fastapi-the-good-the-bad-and-the-ugly-20ob 原文片段：「FastAPI - The Good, the bad and the ugly. - DEV Community Add reaction Like Unicorn Exploding Head Raised Hands Fire Jump to Comments Save Boost Copy link Copied to Clipboard Share to X Share to LinkedIn Share to Facebook Share to Mastodon Report Abuse FastAPI is a relatively new...」
自动质量检查：
- navigation_noise: yes
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent 378a9af9-905d-4e11-a769-2c761913f124

Document: c2703254-0048-4349-a186-f4e8aaf34af3 — 用80字介绍 Redis 核心用途
Section: 参考文献
Parent ID: 378a9af9-905d-4e11-a769-2c761913f124

### Child 1
Child ID: b6568712-4048-4f21-a94a-dbd2dc476060
Child Index: 0
Estimated Token Count: 552
正文：
<a id="ref-1"></a>**[1]** qiankunli.github.io — 《Redis核心技术与实现》笔记 - 李乾坤的博客 URL: https://qiankunli.github.io/2020/08/04/redis_practice.html 原文片段：「《Redis核心技术与实现》笔记 - 李乾坤的博客 前言 前言 整体架构 基本设计 键和值用什么结构组织？ 底层数据结构 持久化/单机高可用 AOF RDB（Redis DataBase） 主从同步/多机高可用 切片集群 缓冲区 淘汰策略 事务 影响redis 性能的几大因素 其它 文章部分内容来自对 《Redis核心技术与实现》的学习 整体架构 基本设计 对于键值数据库而言，基本的数据模型是 key-value 模型。key 一般是 String 类型，而 value 类型则比较多样。在对键值数据库进行选型时， 一个重要的考虑因素是它支持的 value...」 <a id="ref-2"></a>**[2]** developer.aliyun.com — Redis核心原理数据类型持久化与集群全解析-开发者社区-阿里云 URL: https://developer.aliyun.com/article/618702 原文片段：「Redis核心原理数据类型持久化与集群全解析-开发者社区-阿里云 开发者社区 数据库 文章 正文 介绍Redis的各种用途以及使用场景 2018-07-26 12479 版权 版权声明： 本文内容由阿里云实名注册用户自发贡献，版权归原作者所有，阿里云开发者社区不拥有其著作权，亦不承担相应法律责任。具体规则请查看《 阿里云开发者社区用户服务协议 》和 《 阿里云开发者社区知识产权保护指引 》。如果您发现本社区中有涉嫌抄袭的内容，填写 侵权投诉表单 进行举报，一经查实，本社区将立刻删除涉嫌侵权内容。 简介： 介绍Redis的各种用途以及使用场景 Redis...」
自动质量检查：
- navigation_noise: yes
- text_complete: yes
- obvious_duplicate: no
- auto_status: unusable_candidate
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 2
Child ID: cd44e304-434b-4a35-8a69-ae001738bd11
Child Index: 1
Estimated Token Count: 686
正文：
开发者社区知识产权保护指引 》。如果您发现本社区中有涉嫌抄袭的内容，填写 侵权投诉表单 进行举报，一经查实，本社区将立刻删除涉嫌侵权内容。 简介： 介绍Redis的各种用途以及使用场景 Redis...」 <a id="ref-3"></a>**[3]** cnblogs.com — 极客时间之Redis核心技术与实战 - strongmore - 博客园 URL: https://www.cnblogs.com/strongmore/p/17131266.html 原文片段：「极客时间之Redis核心技术与实战 - strongmore - 博客园 strongmore 怕什么真理无穷，进一寸有一寸的欢喜。 极客时间之Redis核心技术与实战 开篇介绍 知识全景图 问题群像图 01-基本架构：一个键值数据库包含什么 02-数据结构：快速的Redis有哪些慢操作？ 新版的数据机构有变化 rehash过程 为了使rehash操作更高效，Redis默认使用了两个全局哈希表：哈希表1和哈希表2。一开始，当你刚插入数据时，默认使用哈希表1，此时的哈希表2并没有被分配空间。随着数据逐步增多，Redis开始执行rehash，这个过程分为三步...」 <a id="ref-4"></a>**[4]** pegasuswang.readthedocs.io — 《Redis深度历险核心原理和应用实践》 - PegasusWang的读书笔记 URL: https://pegasuswang.readthedocs.io/zh/latest/database/redis%E6%B7%B1%E5%BA%A6%E5%8E%86%E9%99%A9%E6%A0%B8%E5%BF%83%E5%8E%9F%E7%90%86%E5%92%8C%E5%BA%94%E7%94%A8%E5%AE%9E%E8%B7%B5/book 原文片段：「《Redis深度历险核心原理和应用实践》 - PegasusWang的读书笔记 » 数据库 » 《Redis深度历险核心原理和应用实践》 应用1：分布式锁 redis2.8 之后加入了set 指令的扩展参数， 使得 setnx 和 expire 可以一起执行（保证原子性） 可重入性：指的是线程持有锁的情况下再次请求加锁，如果一个锁 支持同一个线程的多次加锁，就是可重入的。 应用2：缓兵之计-延时队列 使用 list 作为异步消息队列（你对可靠性没有极致追求） blpop,brpop 阻塞操作，如果list 没有数据就会进入休眠。这里需要注意长时间连接断开...」
自动质量检查：
- navigation_noise: yes
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 3
Child ID: 7ce2d1e9-1f93-431a-916e-32a4e5c2b084
Child Index: 2
Estimated Token Count: 589
正文：
多次加锁，就是可重入的。 应用2：缓兵之计-延时队列 使用 list 作为异步消息队列（你对可靠性没有极致追求） blpop,brpop 阻塞操作，如果list 没有数据就会进入休眠。这里需要注意长时间连接断开...」 <a id="ref-5"></a>**[5]** blog.csdn.net — Redis 核心原理深度解析：从架构到实现_redis架构与实现-CSDN博客 URL: https://blog.csdn.net/weixin_42593797/article/details/147741581 原文片段：「Redis 核心原理深度解析：从架构到实现_redis架构与实现-CSDN博客 Redis 核心原理深度解析：从架构到实现 最新推荐文章于 2026-08-08 08:42:46 发布 原创 最新推荐文章于 2026-08-08 08:42:46 发布 · 1.4k 阅读 · 17 · 20 · 收录于 当前文章被以下社区和专栏收录： 前言 Redis 作为高性能内存数据库的标杆，其设计原理蕴含着对性能、可靠性和扩展性的深度优化。理解 Redis 的核心原理，不仅能帮助开发者合理使用其功能，更能在性能调优、故障排查和架构设计中占据主动。本文将从数据结构、...」 <a id="ref-6"></a>**[6]** cnblogs.com — Redis核心原理和应用场景 - WK_BlogYard - 博客园 URL: https://www.cnblogs.com/wk-missQ1/p/16107976.html 原文片段：「Redis核心原理和应用场景 - WK_BlogYard - 博客园 WK_BlogYard 很多东西不是你觉得有用才去学,而是你学了才知道有用! Redis核心原理和应用场景 Redis核心原理和使用场景 原文链接：https://mp.weixin.qq.com/s/7ct-mvSIaT3o4-tsMaKRWA 一 什么是NoSQL？ Nosql = not only sql（不仅仅是SQL） 关系型数据库：列+行，同一个表下数据的结构是一样的。 非关系型数据库：数据存储没有固定的格式，并且可以进行横向扩展。 NoSQL泛指非关系型数据库，随着web...」
自动质量检查：
- navigation_noise: yes
- text_complete: yes
- obvious_duplicate: no
- auto_status: unusable_candidate
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent 1dca64e0-586d-48b8-85ef-ee3485a637f9

Document: c57297ed-77f1-4438-9a22-c3528c30a10e — 掘地三尺，搞定 Redis 与 MySQL 数据一致性问题 | 社区征文  - 文章 - 开发者社区 - 火山引擎
Section: 掘地三尺，搞定 Redis 与 MySQL 数据一致性问题 | 社区征文  - 文章 - 开发者社区 - 火山引擎
Parent ID: 1dca64e0-586d-48b8-85ef-ee3485a637f9

### Child 1
Child ID: c8bb7bc9-148d-484b-8640-2c75872ffc94
Child Index: 0
Estimated Token Count: 839
正文：
题？ 会导致 数据库是最新数据，缓存是旧数据，出现一致性问题。 该图我就不画了，与上一个图类似，对调下 Redis 和 MySQL 的位置即可。 高并发场景 谢霸歌经常 996，腰酸脖子疼，bug 越写越多，想去按摩推拿放提升下编程技巧。 疫情影响，单子来之不易，高端会所的技师都争先恐后想接这一单，高并发啊兄弟们。 在进店以后，前台会将顾客信息录入系统，执行 set xx的服务技师 = 待定 的初始值表示目前无人接待保存到数据库和缓存中，之后再安排技师按摩服务。 如下图所示： 98 号技师先下手为强，向系统发送 set 谢霸歌的服务技师 = 98 的指令写入数据库，这时候系统的网络出现波动，卡顿了， 数据还没来得及写到缓存 。 接下来，520 号技师也向系统发送 set 谢霸哥的服务技师 = 520 写到数据库中，并且也把这个数据写到缓存中了。 这时候之前的 98 号技师的写缓存请求开始执行，顺利将数据 set 谢霸歌的服务技师 = 98 写到缓存中。 最后发现，数据库的值 = set 谢霸哥的服务技师 = 520 ，而缓存的值= set 谢霸歌的服务技师 = 98 。 520 号技师在缓存中的最新数据被 98 号技师的旧数据覆盖了。 所以， 在高并发的场景中，多线程同时写数据再写缓存，就会出现缓存是旧值，数据库是最新值的不一致情况。 该方案直接 pass。 如果第一步就失败，直接返回 50x 异常，并不会出现数据不一致。 3.3 先删缓存，再更新数据库 按照「码哥」前面说的套路，假设第一个操作成功，第二个操作失败推断下会发生什么？高并发场景下又会发生什么？ 第二步写数据库失败 假设现在有两个请求：写请求 A，读请求 B。 写请求 A 第一步先删除缓存成功，写数据到数据库失败，就会导致该次 写数据丢失，数据库保存的是旧值 。 接着另一个读请 B 求进来，发现缓存不存在，从数据库读取旧数据并写到缓存中。 高并发下的问题 还是 98 号技师先下手为强，系统接收请求把缓存数据删除，当系统准备将 set 肖菜鸡的服务技师 = 98 写到数据库的时候发生卡顿，来不及写入。 这时候，大堂经理向系统执行读请求，查下肖菜鸡有没有技师接待，方便安排技师服务，系统发现缓存中没数据，于是乎就从数据库读取到旧数据 set 肖菜鸡的服务技师 = 待定 ，并写到缓存中。 这时候，原先卡顿的 98 号技师写数据 set 肖菜鸡的服务技师 = 98 到数据库的操作完成。 **
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent 0049516e-f5f0-4692-b4f6-e48345e442f5

Document: 752b27fb-1281-40be-93e1-a198b403f144 — 5种Redis热key问题解决方案_redis热key解决方案-CSDN博客
Section: 5种Redis热key问题解决方案_redis热key解决方案-CSDN博客
Parent ID: 0049516e-f5f0-4692-b4f6-e48345e442f5

### Child 1
Child ID: 62e6e94b-7c6d-425b-8506-20a2f78d8e1f
Child Index: 0
Estimated Token Count: 632
正文：
dCache，复杂 Redis 操作使用 StackExchange. Redis ，国内企业项目使用 CS Redis 。如果你是一名 .NET 开发者，StackExchange. Redis 基本属于必须掌握的技能。因为它不仅是 Redis 客户端，更是很多企业级 .NET 系统中的基础组件。 生产环境实战：基于 Flink (Scala) 的高性能 Redis Sink 设计与踩坑复盘 渣渣盟的博客 08-07 354 本文介绍了基于Flink(Scala)构建高性能 Redis Sink的实战经验。文章首先分析了实时流写入 Redis 的常见 问题 ，如数据重复、写入超时等。接着深入讲解了Flink Sink的两阶段提交机制与幂等性设计，对比了 Redis 不同数据结构的适用场景，推荐使用HSET实现精确一次语义。 核心部分详细剖析了 Redis Sink的底层原理，包括序列化机制和连接池I/O模型，并提供了完整的实战代码。文章特别补充了原文缺失的ClickSource实现，修正了 Redis 连接配置的常见错误，如主机地址设置和端口配置。 橡 皮 人 博客等级 码龄7年 113 原创 2160 点赞 4223 收藏 1427 粉丝 关注 私信 TA的精选 新 RocketMQ第11讲——订阅关系一致性 1118 阅读 新 RocketMQ第10讲——消息过滤原理 968 阅读 热 设计模式第9讲——适配器模式（Adapter） 36003 阅读 热 设计模式第10讲——建造者模式（Builder） 22139 阅读 热 设计模式第5讲——观察者模式（Observer） 21121 阅读 查看更多 大家在看 Linux系统编程：C语言从零设计Linux基础终端进度条 15 Prompt Engineering进阶：用结构化指令约束大模型输出的5种策略 42 TensorRL-LLM——高性能实时推理优化库 极限提高GPU性能 287 PagedAttention显存管理算法 509 自学嵌入式第20天（数据结构篇——队列） TA的历史创作历程 2025年 12篇 2024年 42篇 2023年 59篇 分类专栏 RocketMQ 11篇 Java并发编程 16篇 Java 8~Java 24新特性总结 13篇 Redis 29篇 Java集
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent 8649c414-cfd1-4a2c-bc6d-45ccf00e7ef9

Document: f3aa97b2-57cc-475d-9fa3-1b4402493ea8 — How to do distributed locking — Martin Kleppmann’s blog
Section: How to do distributed locking — Martin Kleppmann’s blog
Parent ID: 8649c414-cfd1-4a2c-bc6d-45ccf00e7ef9

### Child 1
Child ID: c4145c16-3a0d-438f-8b4f-4156e0e68206
Child Index: 0
Estimated Token Count: 346
正文：
y your process might get paused. Maybe your process tried to read an address that is not yet loaded into memory, so it gets a page fault and is paused until the page is loaded from disk. Maybe your disk is actually EBS, and so reading a variable unwittingly turned into a synchronous network request over Amazon’s congested network. Maybe there are many other processes contending for CPU, and you hit a black node in your scheduler tree . Maybe someone accidentally sent SIGSTOP to the process. Whatever. Your processes will get paused. If you still don’t believe me about process pauses, then consider instead that the file-writing request may get delayed in the network before reaching the storage service. Packet networks such as Ethernet and IP may delay packets arbitrarily , and they do [7]: in a famous incident at GitHub , packets were delayed in the network for approximately 90 seconds [8]. This means that an application process may send a write request, and it may reach the stor
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent 6b71fc8b-c55d-4a39-8eb3-b58d13f27908

Document: df732fe5-3c1b-442d-a005-3d514350571d — Redis分布式锁：从SETNX到Redisson的演进 | Seven的菜鸟成长之路
Section: Redis分布式锁：从SETNX到Redisson的演进 | Seven的菜鸟成长之路
Parent ID: 6b71fc8b-c55d-4a39-8eb3-b58d13f27908

### Child 1
Child ID: da1668e8-f06e-4181-b382-1feedc6d4187
Child Index: 0
Estimated Token Count: 335
正文：
Async ( long waitTime , long leaseTime , TimeUnit unit , long threadId , RedisStrictCommand < T > command) { this . internalLockLeaseTime = unit . toMillis (leaseTime); return this . evalWriteAsync ( this . getName (), LongCodec . INSTANCE , command, "if (redis.call('exists', KEYS[1]) == 0) then redis.call('hincrby', KEYS[1], ARGV[2], 1); redis.call('pexpire', KEYS[1], ARGV[1]); return nil; end; if (redis.call('hexists', KEYS[1], ARGV[2]) == 1) then redis.call('hincrby', KEYS[1], ARGV[2], 1); redis.call('pexpire', KEYS[1], ARGV[1]); return nil; end; return redis.call('pttl', KEYS[1]);" , Collections . singletonList ( this . getName ()), this . internalLockLeaseTime , this . getLockName (threadId)); } eval命令执行Lua脚本的地方，此处将Lua脚本展开 -- 不存在该key时 if ( redis . call ( 'exists' , KEYS [ 1 ]) == 0 ) then -- 新增该锁并且hash中该线程id对应的count置1 redis . call ( 'hincrby' , KEYS [ 1 ], ARGV [ 2 ], 1 ); -- 设置过期时间 redis . call ( 'pexpire' , KEYS [ 1 ], ARGV [ 1 ]); return nil ; end ; -- 存在该key 并且 hash中线程
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent 754b5be9-e39e-41ca-a38a-853052846b1c

Document: 60b6e1da-7442-4af2-a031-a9948ec0aed9 — Redis分布式锁 （图解-秒懂-史上最全） - 技术自由圈 - 博客园
Section: Redis分布式锁 （图解-秒懂-史上最全） - 技术自由圈 - 博客园
Parent ID: 754b5be9-e39e-41ca-a38a-853052846b1c

### Child 1
Child ID: a3d8f9ec-9e3c-4b75-9d23-c6f423bc9911
Child Index: 0
Estimated Token Count: 447
正文：
端请求标识，那么在客户端在解锁的时候就可以进行校验是否是同一个客户端。 由于我们只考虑Redis单机部署的场景，所以容错性我们暂不考虑。 基于Jedis 的API实现简单解锁代码 还是先展示代码，再带大家慢慢解释为什么这样实现。 解锁的简单代码实现 ： package com.crazymaker.springcloud.standard.lock; @Slf4j @Data @AllArgsConstructor public class JedisCommandLock { private static final Long RELEASE_SUCCESS = 1L; /** * 释放分布式锁 * @param jedis Redis客户端 * @param lockKey 锁 * @param requestId 请求标识 * @return 是否释放成功 */ public static boolean releaseDistributedLock(Jedis jedis, String lockKey, String requestId) { String script = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end"; Object result = jedis.eval(script, Collections.singletonList(lockKey), Collections.singletonList(requestId)); if (RELEASE_SUCCESS.equals(result)) { return true; } return false; } } 那么这段Lua代码的功能是什么呢？ 其实很简单，首先获取锁对应的value值，检查是否与requestId相等，如果相等则删除锁（解锁）。 第一行代码，我们写了一个简单的Lua脚本代码。 第二行代码，我们将Lua代码传到 jedis.eval() 方法里，并使参数KEYS[1]赋值为lockKey，ARGV[1]赋值为requestId。eval()方法是将Lua代码交给Redis服务端执行。 那么为什么要使用Lua
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent 0d2b423f-1c03-4368-91a8-e2c2c25abe8f

Document: dd6039e5-a86d-4042-90a5-b304bd98bf61 — Redis分布式锁经典问题详解：误删、过期、续命，及Redisson看门狗机制_redisson 设置了过期时间会自动续期吗-CSDN博客
Section: Redis分布式锁经典问题详解：误删、过期、续命，及Redisson看门狗机制_redisson 设置了过期时间会自动续期吗-CSDN博客
Parent ID: 0d2b423f-1c03-4368-91a8-e2c2c25abe8f

### Child 1
Child ID: c7e2bfee-252e-4f4d-a5ec-76c6c89793e3
Child Index: 0
Estimated Token Count: 742
正文：
le）记录的是 Redis 执行的每一个写命令。每次执行写操作，命令就会被追加到 AOF 文件末尾。把所有写操作写成日记，重启时重放日记就能恢复数据。AOF 会按照 Redis 协议格式记录每一次写命令，而不是简单保存命令字符串。 Codex 精准 高并发点赞系统终极解决方案｜前端防抖幂等 + Redis 抗并发 + 异步落库 十年老程序猿，AI 疯狂研究专家，前沿硬核知识分享 08-04 474 防抖锁：拦截短时间连续点击幂等 ID：规避网络重试产生重复请求乐观 UI：优化交互，消除等待卡顿前端依靠防抖、幂等、乐观 UI 拦截大部分无效流量；后端标准架构： Redis 承载流量峰值 + MQ 异步落库 + 定时任务数据校正；高并发系统通用思路：请求拦截、流量削峰、接口幂等、最终一致性兜底；AI 高效开发方式：精准架构约束提示词 + Codex Agent 工程能力，直接落地生产级代码。 Spring Boot 接口幂等实战：重复提交、 Redis Lua、唯一索引与消息重复消费一次讲透 2501_94007735的博客 08-07 355 用户只点了一次“提交订单”，服务端为什么收到两次请求？原因可能是按钮连点、移动网络重传、网关超时重试、调用方没有收到响应后的补偿重试，也可能是支付平台重复回调或消息中间件再次投递。对查询接口来说，多执行一次通常只是浪费资源；对下单、扣款、发券、库存变更而言，一次重复就可能变成真实损失。很多教程把幂等简化为“ Redis SETNX成功就放行”，但这只能挡住一部分并发。 Redis 占位成功后应用可能崩溃，数据库提交后回包可能丢失，TTL 可能早于业务结束，缓存还可能因淘汰或故障切换丢键。 清空 Redis 数据 Bigbullwang的博客 08-06 60 3.执行FLUSHALL命令，即清空 Redis 。1.点击 redis -cli。Auth+ Redis 密码。 黑马点评—— 分布式锁 与 Redis 消息队列 weixin_42927227的博客 08-06 350 分布式锁 ：满足 分布式 系统或集群模式下多进程可见、并且互斥的锁。特性含义多进程可见不只是 JVM 内部可见，跨进程、跨机器也要能拿同一把锁互斥任意时刻只能有一个客户端持有锁高可用锁服务挂了要能快速恢复，不能因为锁服务挂掉导致整个业务瘫
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent ab2a4e39-290b-40f4-a417-e64c374438e6

Document: b86d33a3-db24-48db-8a79-64feebbc5aa0 — Redis高级（八）、全网最详细的分布式锁原理+实战+WatchDog机制源码解读首先搞明白RedLock与Rediss - 掘金
Section: Redis高级（八）、全网最详细的分布式锁原理+实战+WatchDog机制源码解读首先搞明白RedLock与Rediss - 掘金
Parent ID: ab2a4e39-290b-40f4-a417-e64c374438e6

### Child 1
Child ID: 723b50ac-8359-492e-9e5b-5295a356e5df
Child Index: 0
Estimated Token Count: 234
正文：
mIdleSize (redisProperties.getPool() .getMinIdle ()); if (StringUtils.isNotBlank(redisProperties.getPassword())) { serverConfig .setPassword (redisProperties.getPassword()); } return Redisson .create (config); } @Bean RedissonClient redissonClient3() { Config config = new Config (); String node = redisProperties .getSingle () .getAddress3 (); node = node .startsWith ("redis://") ? node : "redis://" + node; SingleServerConfig serverConfig = config .useSingleServer () .setAddress (node) .setTimeout (redisProperties.getPool() .getConnTimeout ()) .setConnectionPoolSize (redisProperties.getPool() .getSize ()) .setConnectionMinimumIdleSize (redisProperties.getPool() .getMinIdle ()); if (StringUtils.isNotBlank(redisProperties.getPassword())) { serverConfig .setPassword (redisProperties.getPassword()); } return Redisson .create (config); } /** * 单机 * @return */ /*@Bean public Redisson redisson() { Config config = new Config(); config.useSingleServer().setAddress("redis://192.168.111.14
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent ecef5995-40fc-46e1-b67b-bd8a2ed1550a

Document: b022e1fd-04a5-4d5e-892b-f0ea114cca82 — 一文告诉你“为什么以及怎么样使用分布式锁”
Section: 一文告诉你“为什么以及怎么样使用分布式锁”
Parent ID: ecef5995-40fc-46e1-b67b-bd8a2ed1550a

### Child 1
Child ID: 398521a8-0d16-4f5d-9575-165f972e6ad5
Child Index: 0
Estimated Token Count: 528
正文：
锁的落地方案： 使用 ZK 的临时节点和有序节点，每个线程获取锁就是在 ZK 创建一个临时有序的节点，比如在 /lock/ 目录下。 创建节点成功后，获取 /lock 目录下的所有临时节点，再判断当前线程创建的节点是否是所有的节点的序号最小的节点。 如果当前线程创建的节点是所有节点序号最小的节点，则认为获取锁成功。 如果当前线程创建的节点不是所有节点序号最小的节点，则对节点序号的前一个节点添加一个事件监听。 比如当前线程获取到的节点序号为 /lock/003，然后所有的节点列表为[/lock/001，/lock/002，/lock/003]，则对 /lock/002 这个节点添加一个事件监听器。 如果锁释放了，会唤醒下一个序号的节点，然后重新执行第 3 步，判断是否自己的节点序号是最小。 比如 /lock/001 释放了，/lock/002 监听到时间，此时节点集合为[/lock/002，/lock/003]，则 /lock/002 为最小序号节点，获取到锁。 整个过程如下： 具体的实现思路就是这样，至于代码怎么写，这里比较复杂就不贴出来了。 Curator 介绍 Curator 是一个 ZK 的开源客户端，也提供了分布式锁的实现。它的使用方式也比较简单： InterProcessMutex interProcessMutex = new InterProcessMutex(client,"/anyLock"); interProcessMutex.acquire(); interProcessMutex.release(); 其实现分布式锁的核心源码如下： private boolean internalLockLoop(long startMillis, Long millisToWait, String ourPath) throws Exception { boolean haveTheLock = false; boolean doDelete = false; try { if ( revocable.get() != null ) { client.getData().usingWatcher(revocableWatcher).forPath(ourPath); } while ( (client.getState() == Cura
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent 3bf8c260-75f2-4e64-a26f-d365868822ef

Document: 2d363884-3a5b-4ba8-9949-8a5d4d1a85ea — 分布式锁实现方案详解：Redis、Redlock、ZooKeeper 与 Redisson 看门狗 | JavaGuide
Section: 分布式锁实现方案详解：Redis、Redlock、ZooKeeper 与 Redisson 看门狗 | JavaGuide
Parent ID: 3bf8c260-75f2-4e64-a26f-d365868822ef

### Child 1
Child ID: fb18e10b-3846-43da-8584-c83729afdfc3
Child Index: 0
Estimated Token Count: 430
正文：
在出现故障之后，对应的子节点由于是临时顺序节点，也会被自动删除，避免了锁无法被释放。 我们前面说的事件监听器其实监听的就是这个子节点删除事件，子节点删除就意味着锁被释放。 实际项目中，推荐使用 Curator 来实现 ZooKeeper 分布式锁。Curator 是 Netflix 公司开源的一套 ZooKeeper Java 客户端框架，相比于 ZooKeeper 自带的客户端 zookeeper 来说，Curator 的封装更加完善，各种 API 都可以比较方便地使用。 Curator 主要实现了下面四种锁： InterProcessMutex ：分布式可重入排它锁 InterProcessSemaphoreMutex ：分布式不可重入排它锁 InterProcessReadWriteLock ：分布式读写锁 InterProcessMultiLock ：将多个锁作为单个实体管理的容器，获取锁的时候获取所有锁，释放锁也会释放所有锁资源（忽略释放失败的锁）。 CuratorFramework client = ZKUtils . getClient (); client . start (); // 分布式可重入排它锁 InterProcessLock lock1 = new InterProcessMutex (client , lockPath1) ; // 分布式不可重入排它锁 InterProcessLock lock2 = new InterProcessSemaphoreMutex (client , lockPath2) ; // 将多个锁作为一个整体 InterProcessMultiLock lock = new InterProcessMultiLock ( Arrays . asList (lock1, lock2) ) ; if ( ! lock . acquire ( 10 , TimeUnit . SECONDS ) ) { throw new IllegalStateException ( "不能获取多锁" ) ; } System . out . println ( "已获取多锁" ); System . out . println ( "是否有第一个锁: " + lock1 . isAcquiredInThisPr
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent a1ab4335-d0fd-4e6b-9a8b-396b2bf16d60

Document: 9a51cd43-6996-4a05-853e-c71bf2b2746a — 干货满满：Redis 分布式锁必避的 8 大问题及解决方案 - 佛祖让我来巡山 - 博客园
Section: 干货满满：Redis 分布式锁必避的 8 大问题及解决方案 - 佛祖让我来巡山 - 博客园
Parent ID: a1ab4335-d0fd-4e6b-9a8b-396b2bf16d60

### Child 1
Child ID: c3c1c313-3662-4dc7-bff6-309e3b9e45d1
Child Index: 0
Estimated Token Count: 783
正文：
状态修改）放入锁内，非核心逻辑（如日志记录、消息推送）移至锁外执行。 异步化处理：若锁内必须执行耗时操作，将其异步化（如用线程池、消息队列），缩短锁持有时间。 设置锁持有超时预警：通过监控工具统计锁持有时间，超过阈值（如 20 秒）时告警，及时排查耗时业务。 问题 8：锁 key 设计不当——锁粒度问题引发并发瓶颈 成因 ：锁 key 粒度太粗（如用“lock:stock”作为所有商品的库存锁），导致所有商品的库存操作都互斥，即使操作不同商品，也需排队等待锁释放，彻底丧失分布式系统的并发优势。 表现 ：系统并发量极低，不同商品的库存扣减请求串行执行，接口吞吐量远低于预期。 解决方案 ：精细化设计锁 key，按具体资源标识拆分锁。比如库存锁，用“lock:stock:1001”（1001 为商品 ID）作为锁 key，仅对同一商品的库存操作互斥，不同商品可并行处理，大幅提升并发量。 延伸：高并发场景下，可进一步用“分段锁”拆分资源（如将商品 ID 哈希到 10 个分段，锁 key 为“lock:stock:segment:1”），同一分段互斥，不同分段并行，进一步提升并发能力。 问题 9：网络分区导致锁状态不一致——极端场景下的隐患 成因 ：分布式环境中出现网络分区，持有锁的服务与 Redis 集群隔离，无法主动释放锁，也无法接收锁续约信号；锁过期后，其他服务加锁成功；网络恢复后，原持有锁的服务误以为锁仍有效，继续操作资源，导致数据冲突。 表现 ：极端网络异常后，出现数据不一致，且问题难以排查（与网络分区时间、锁过期时间强相关）。 解决方案 ： 引入业务校验机制：操作资源前，再次校验资源状态（如扣减库存前，检查库存是否与预期一致），避免基于过期锁的无效操作。 缩短锁过期时间：结合 Watch Dog 机制，将基础过期时间设短（如 10 秒），减少网络分区导致的锁状态不一致窗口。 使用 Redlock 算法：多主节点投票机制，可降低网络分区对锁状态的影响，提升一致性。 二、生产避坑总结 Redis 分布式锁的问题，大多不是 Redis 本身的缺陷，而是对分布式场景的复杂性考虑不足。结合实战经验，总结 3 个核心避坑原则： 优先使用成熟框架：放弃手动实现分布式锁，Redisson 已封装解决上述所有问题，开箱即用，稳定性远高于自定义实现。 匹配业务场景选型
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent e3dc0571-855c-4072-8f34-20a1fe5de99b

Document: e4c0eb9b-8f9c-4a0a-818f-d3c633c67457 — 深入理解分布式锁：原理、应用与挑战-京东云开发者社区
Section: 深入理解分布式锁：原理、应用与挑战-京东云开发者社区
Parent ID: e3dc0571-855c-4072-8f34-20a1fe5de99b

### Child 1
Child ID: ff651920-a885-4987-a701-a674ef6f6afd
Child Index: 0
Estimated Token Count: 593
正文：
完全避免在加锁后中断设置不上超时时间的问题。也不会存在有时钟不一致的问题，和高并发情况下多个线程都加上锁的问题。但是这种方式就一定没有问题了吗？答案是否定的。考虑以下场景： 当服务A加锁成功后，正在执行业务的过程中，锁过期啦，这时服务A是没有感知的； 接着服务B这时来获取锁，成功获取到了； 紧接着，服务A处理完业务了，来释放锁，成功释放掉了，而服务B这时还以为它的锁还在，在执行代码。 全乱套了有没有？以为自己加锁了，其实你没加； 以为自己解锁成功了，其实解的是别人的锁； 这种方案的问题主要是因为两点： 锁过期释放，业务没处理完；锁没有唯一身份标识 。 备注 ：从Redis 2.6.12版本开始支持setNx同时设置超时时间 如果你想要在设置key的同时为其设置过期时间，并希望这是一个原子操作，你可以考虑使用Redis的 SET 命令，如下所示： SET mykey "myvalue" NX EX 10 # 设置mykey的值为myvalue，仅当mykey不存在时，并设置过期时间为10秒 方案四：SET NX PX EX + 唯一标识 对于误删锁的问题，我们可以在加锁时，由客户端生成一个唯一ID作为value设置在锁中，在删除锁时先进行身份判断，再删除；加锁逻辑如下： public boolean getLock(String key,String uniId,Long expireTime) { //加锁 return jedis.set(key, uniId, "NX", "EX", expireTime) == 1; } // 解锁 public boolean releaseLock(String key,String uniId) { // 因为get和del操作并不是原子的，所以使用lua脚本 String lua_script = "if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end;"; List<String> keys = Collections.singletonList(key); List<String> argv = Arrays.asList(uuiId); Object resul
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent 66e4aba4-de05-4609-bdfe-bc2c0396dc5b

Document: 9887b22d-6784-455d-9ac1-ddfd1fdc69f5 — 聊聊redis分布式锁的8大坑前言 在分布式系统中，由于redis分布式锁相对于更简单和高效，成为了分布式锁的首先，被用 - 掘金
Section: 聊聊redis分布式锁的8大坑前言 在分布式系统中，由于redis分布式锁相对于更简单和高效，成为了分布式锁的首先，被用 - 掘金
Parent ID: 66e4aba4-de05-4609-bdfe-bc2c0396dc5b

### Child 1
Child ID: f358f7db-de57-4f73-bd5a-9799f2906cb4
Child Index: 0
Estimated Token Count: 584
正文：
的频率远远大于写数据。而线程间的并发读操作是并不涉及并发安全问题，我们没有必要给读操作加互斥锁，只要保证读写、写写并发操作上锁是互斥的就行，这样可以提升系统的性能。 我们以redisson框架为例，它内部已经实现了读写锁的功能。 读锁的伪代码如下： RReadWriteLock readWriteLock = redisson.getReadWriteLock( "readWriteLock" ); RLock rLock = readWriteLock.readLock(); try { rLock.lock(); //业务操作 } catch (Exception e) { log.error(e); } finally { rLock.unlock(); } 写锁的伪代码如下： RReadWriteLock readWriteLock = redisson.getReadWriteLock( "readWriteLock" ); RLock rLock = readWriteLock.writeLock(); try { rLock.lock(); //业务操作 } catch (InterruptedException e) { log.error(e); } finally { rLock.unlock(); } 将读锁和写锁分开，最大的好处是提升读操作的性能，因为读和读之间是共享的，不存在互斥性。而我们的实际业务场景中，绝大多数数据操作都是读操作。所以，如果提升了读操作的性能，也就会提升整个锁的性能。 下面总结一个读写锁的特点： 读与读是共享的，不互斥 读与写互斥 写与写互斥 6.2 锁分段 此外，为了减小锁的粒度，比较常见的做法是将大锁： 分段 。 在java中 ConcurrentHashMap ，就是将数据分为 16段 ，每一段都有单独的锁，并且处于不同锁段的数据互不干扰，以此来提升锁的性能。 放在实际业务场景中，我们可以这样做： 比如在秒杀扣库存的场景中，现在的库存中有2000个商品，用户可以秒杀。为了防止出现超卖的情况，通常情况下，可以对库存加锁。如果有1W的用户竞争同一把锁，显然系统吞吐量会非常低。 为了提升系统性能，我们可以将库存分段，比如：分为100段，这样每段就有20个商品可以参与秒杀。 在秒杀的过程中，先把用户id获取
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent 94c18658-42fa-4a97-b258-b5d9db45abe4

Document: 1da35a80-14b8-45dc-a21b-f5d3d7143faa — 2026年超级全面Redis分布式锁选型指南，限流实现方案全解析 - FineDataLink数据集成平台
Section: 2026年超级全面Redis分布式锁选型指南，限流实现方案全解析 - FineDataLink数据集成平台
Parent ID: 94c18658-42fa-4a97-b258-b5d9db45abe4

### Child 1
Child ID: 18ef18ce-af28-4e21-a178-85e3c4fef41c
Child Index: 0
Estimated Token Count: 805
正文：
多节点集群建议加监控、降级，防止锁服务宕机影响业务。 如果锁的场景和数据同步/ETL任务强相关，比如定时同步任务、数据管道并发执行，直接上FineDataLink，省心省力还安全： FineDataLink体验Demo 。 ⚡限流和分布式锁有什么本质区别？高并发场景下组合用法怎么落地最优？ 最近做系统扩容，老板说“分布式锁和限流都要配齐”，但我实际用的时候发现两者有点傻傻分不清楚。有大佬能系统讲讲锁和限流的本质区别吗？在高并发场景下怎么合理搭配，哪些坑要重点避开？比如秒杀、数据同步、ETL场景有没有最佳实践？ 回答： 这个问题特别有代表性！很多同学做分布式业务时，确实会把“分布式锁”和“限流”混淆，甚至以为只要有锁就能抗住高并发，其实两者本质完全不同。 本质区别： 分布式锁： 控制“同一资源”在同一时刻只能被一个实例操作。 解决的是“唯一性、一致性”问题，比如订单号生成、库存扣减、任务调度。 限流： 控制单位时间内“总并发量”不超过设定阈值。 解决的是“服务过载保护”，比如API接口QPS限制、秒杀系统流量削峰。 维度 分布式锁 限流 关注点 资源独占 总并发量控制 典型场景 订单、库存、定时任务 秒杀、接口防刷、流量削峰 实现方式 Redis/ZK分布式锁 令牌桶、漏桶、计数器 风险 死锁、性能瓶颈 流量被拒、用户体验下降 高并发下组合用法实操案例： 秒杀系统 ： 首先用限流（如令牌桶算法）挡掉超高并发的流量，保护下游服务不崩溃。 剩下的流量再用分布式锁串行扣减库存，确保不会超卖。 定时任务/同步任务 ： 多实例部署时，先用分布式锁保证任务只被一个服务实例执行，避免重复处理。 同时用限流防止一次处理量过大，压垮数据库或目标系统。 ETL/数据集成平台 ： 比如FineDataLink（FDL）这样的平台，会把数据同步任务自动分片、并发处理，用分布式锁确保同一批次任务不被重复消费，再用限流保护下游写入能力不被打爆。 常见坑： 只用锁不限流：高并发瞬间全卡在锁上，Redis性能瓶颈，甚至出现锁雪崩。 只限流不加锁：出现数据重复、超卖、任务重复执行等一致性问题。 锁和限流位置混淆：比如把限流放在锁后面，导致锁竞争压力过大，达不到削峰效果。 最佳实践清单： 限流优先，锁后置 ：先削峰填谷，再保证一致性。 锁粒度设计合理 ：能细就细，别用全局大锁。 监控和
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent 326cee13-9500-44e9-ace9-59c572173565

Document: ff411da1-0278-4cdb-ae77-26b24f210ce9 — Redis - 高并发场景下的Redis最佳实践_翻过6座大山-腾讯云开发者社区-腾讯云
Section: Redis - 高并发场景下的Redis最佳实践_翻过6座大山-腾讯云开发者社区-腾讯云
Parent ID: 326cee13-9500-44e9-ace9-59c572173565

### Child 1
Child ID: 6e0f67c6-e44e-4597-823e-51ac8009e18e
Child Index: 0
Estimated Token Count: 717
正文：
汰，包括带过期时间和不带过期时间的数据。 volatile-random： 随机选择一个带过期时间的数据进行淘汰。 allkeys-random： 随机选择一个数据进行淘汰，包括带过期时间和不带过期时间的数据。 volatile-ttl： 选择最接近过期的数据进行释放操作，只从带过期时间的数据集中选择。 发生场景 把Redis当存储使用： 部分场景下，将Redis用作数据存储，不设置过期时间，可能导致内存持续增长，触发淘汰策略，不正确的淘汰策略可能导致数据丢失。 Bug数据逐步污染缓存： 开发人员忘记设置过期时间，或设置过期时间过长，导致缓存内存被占满。 解决方案 存储隔离： 对于永不过期的数据，要与正常的缓存数据做集群的分离，以便设置不同的淘汰策略。 容量监控： 预估使用容量，给予足够的冗余应对业务发展。 实时监控使用量变化，一旦超过阈值，立即扩容并排查原因。 监控key的过期时间，定期扫描，发现未设置过期时间或设置不合理的key，并及时修复。 在实际应用中，结合合适的淘汰策略和监控手段，能够更好地管理Redis缓存，保障系统的稳定性和可靠性。 6座大山之_Hot Key 热 Key 是指在Redis中频繁访问的某些特定key，可能导致单个实例的性能问题。 即使对Redis进行扩容，也无法完全解决热 Key 问题，因为对于同一个key的访问通常会集中在同一个实例上 。 热 Key 问题可能导致接口超时、网络负载过大、连接数达到上限等一系列问题，严重影响系统稳定性和性能。 发现热 Key 按业务场景预估热点 key： 根据业务特点预估一些热门key，如促销商品、秒杀商品等。这种方法简单但依赖于人工经验，无法发现意外的热点。 客户端收集： 封装代码统计Redis的所有访问命令，对命令进行统计分析。简单方便但需要代码修改。 代理层收集： 在访问Redis之前添加访问代理层，代理层收敛请求并进行统计。无代码侵入但架构复杂。 Redis监控命令： 使用Redis提供的监控命令，如 hotkeys 命令，实时监控热 Key。无代码侵入但对大集群扫描较慢。 代码语言： javascript 复制
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent 5e7e75f6-5cf2-4b5b-aa9b-212509d45e99

Document: 26f4d3a8-ae66-4fb0-ac37-58da6263232f — Kubernetes 中 HPA 与 VPA 的差异及生产落地建议
Section: 参考文献
Parent ID: 5e7e75f6-5cf2-4b5b-aa9b-212509d45e99

### Child 1
Child ID: ec679cc8-0bab-4a42-8c82-71b8ccc41ffe
Child Index: 0
Estimated Token Count: 479
正文：
<a id="ref-10"></a>**[10]** lixueduan.com — Kubernetes教程(十二)---VPA:垂直 Pod 自动扩缩容 - 探索云原生 URL: https://www.lixueduan.com/posts/kubernetes/12-vpa 原文片段：「Kubernetes教程(十二)---VPA:垂直 Pod 自动扩缩容 - 探索云原生 Kubernetes教程(十二)---VPA:垂直 Pod 自动扩缩容 意琦行 收录于 Kubernetes 2022-10-14 00:00:00 约 2900 字 预计阅读 6 分钟 - 次阅读 目录 本文主要记录 k8s 中与 HPA 相对应的 VPA 功能，包括架构、大致实现以及 demo。 什么是 VPA？ VPA 全称 Vertical Pod Autoscaler,即垂直 Pod 自动扩缩容 ,它根据容器资源使用率自动设置 CPU 和内存的request...」 <a id="ref-11"></a>**[11]** cnblogs.com — 云原生：使用HPA和VPA实现集群扩缩容 - Hello-Brand - 博客园 URL: https://www.cnblogs.com/wzh2010/p/18031123 原文片段：「云原生：使用HPA和VPA实现集群扩缩容 - Hello-Brand - 博客园 Brand 一生践行韦特莱法则，一生保持高执行力高效率... 云原生：使用HPA和VPA实现集群扩缩容 1 背景 我们之前介绍过，随着业务流量上涨之后，我们的系统需要适时的进行扩容。 数据存储层我们也介绍过MySQL的扩容 Scale UP（纵向扩展） 和 Scale Out（横向扩展） 垂直拆分（Scale Up 纵向扩展）：包括垂直分库、垂直分表 水平拆分（Scale Out 横向扩展）：包括库内分表、分库分表 详细可以参考笔者这几篇： 《 MySQL全面瓦解28：分库...」
自动质量检查：
- navigation_noise: yes
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent 23a18d64-3c46-484c-bef1-eac2d7445037

Document: 88c21fa4-e42d-4cbb-bca8-8c435925631e — Redis 分布式锁的实现原理与常见坑，控制在800字以内
Section: 参考文献
Parent ID: 23a18d64-3c46-484c-bef1-eac2d7445037

### Child 1
Child ID: 35347050-3659-4e4a-b7e6-c938ac30ba95
Child Index: 0
Estimated Token Count: 415
正文：
<a id="ref-14"></a>**[14]** learn.lianglianglee.com — 08 基于 Redis 的分布式锁实现及其踩坑案例 URL: https://learn.lianglianglee.com/%E4%B8%93%E6%A0%8F/%E5%88%86%E5%B8%83%E5%BC%8F%E4%B8%AD%E9%97%B4%E4%BB%B6%E5%AE%9E%E8%B7%B5%E4%B9%8B%E8%B7%AF%EF%BC%88%E5%AE%8C%EF%BC%89/08%20%E5%9F%BA%E4%BA%8E%20Redis%20%E7%9A%84%E5%88%86%E5%B8%83%E5%BC%8F%E9%94%81%E5%AE%9E%E7%8E%B0%E5%8F%8A%E5%85%B6%E8%B8%A9%E5%9D%91%E6%A1%88%E4%BE%8B.md 原文片段：「08 基于 Redis 的分布式锁实现及其踩坑案例 技术文章摘抄 首页 上一级 01 开篇词：从中间件开始学习分布式.md 02 走进分布式中间件（课前必读）.md 03 主流分布式缓存方案的解读及比较.md 04 分布式一致性协议 Gossip 和 Redis 集群原理解析.md 05 基于 Redis 的分布式缓存实现及加固策略.md 06 Redis 实际应用中的异常场景及其根因分析和解决方案.md 07 Redis-Cluster 故障倒换调优原理分析.md 08 基于 Redis 的分布式锁实现及其踩坑案例.md 09 分布式一致性算法 Raf...」
自动质量检查：
- navigation_noise: yes
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent d05dbfec-6bd4-4b78-9fff-2c9a79239d7f

Document: 178d5753-0258-4963-a8b0-2ba80a9da886 — 亿级电商流量，高并发下Redis与MySQL的数据一致性如何保证-阿里云开发者社区
Section: 亿级电商流量，高并发下Redis与MySQL的数据一致性如何保证-阿里云开发者社区
Parent ID: d05dbfec-6bd4-4b78-9fff-2c9a79239d7f

### Child 1
Child ID: ac6450de-8c72-4522-8dd9-b8bd93481f33
Child Index: 0
Estimated Token Count: 510
正文：
失败任务 执行二次删除redis缓存 说到底就是通过数据库的 binlog 来异步淘汰 key，利用工具(canal)将 binlog 日志采集发送到 MQ 中，然后通过 ACK 机制确认处理删除缓存。 先更新 DB，后删除缓存，这种方式，被称为 Cache Aside Pattern ，属于缓存更新的 经典设计模式 之一。 所以如果大家做缓存与数据库的同步，推荐大家选择这一种方式。 总结 至此，亿级电商流量，高并发下Redis与MySQL的数据一致性如何保证的方案，非常圆满了。以上的内容，如果大家能烂熟于心、对答如流、如数家珍，基本上 面试官会被你 震惊到、吸引到。 最终， 让面试官爱到 “不能自已、口水直流” 。offer， 也就来了。 文末留个问题给大家： 文中提到第4种方案（先更新数据库，后删除缓存）被称为Cache Aside Pattern，属于缓存 更新的经典设计模式之一。 问题： 那大家还知道其他缓存更新的经典设计模式吗？ 说在最后 求一键三连：点赞、分享、收藏 点赞对我真的非常重要！在线求赞，加个关注我会非常感激！ 最近无意间获得一份阿里大佬写的刷题笔记，一下子打通了我的任督二脉，进大厂原来没那么难。 这是大佬写的， 7701页的BAT大佬写的刷题笔记，让我offer拿到手软 本文，已收录于，我的技术网站 aijiangsir.com ，有大厂完整面经，工作技术，架构师成长之路，等经验分享 求一键三连：点赞、分享、收藏 点赞对我真的非常重要！在线求赞，加个关注我会非常感激！ 江-小北 目录 热门文章 最新文章
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent 3c0ae026-3b0b-4fa7-8dd2-e78e0b3922af

Document: 4bfd8c68-1be5-40ad-9817-8e2c1b7857ac — ping test
Section: 四、 结果解读与常见错误排查
Parent ID: 3c0ae026-3b0b-4fa7-8dd2-e78e0b3922af

### Child 1
Child ID: 7900c458-dc24-41a4-93c1-3fca0890926b
Child Index: 0
Estimated Token Count: 306
正文：
在执行Ping测试时，正确解读输出信息和错误代码是排障的关键。正常的Ping结果会显示字节数（通常为32或64）、回复时间（ms）和TTL值[2]。当网络出现问题时，通常会返回以下错误信息： | 错误信息 | 潜在原因与排查方向 | | :--- | :--- | | **Unknown host** | 域名无法解析。表明DNS服务器不可用或配置错误，需检查本地DNS设置或WINS服务器状态[2]。 | | **Destination host unreachable** | 路由失败。表明本地PC没有到达目标的路由，或者中间路由器找不到目标路径。需检查本地网关配置或路由表[2]。 | | **General failure** | 本地网络栈或硬件故障。通常指向本地网卡驱动异常、TCP/IP协议栈损坏或设备未获取到有效IP地址[2]。 | | **Request timed out** | 请求超时。目标设备不可达，或者目标设备/中间防火墙配置为丢弃ICMP包。需确认目标是否禁Ping，或排查中间链路拥塞[2][3]。 |
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent 8528ba93-fbb3-4f8a-b321-ebef5cf08c48

Document: 46667324-46da-4298-9335-3d26a07f5830 — 一、Redis 快速入门 | Hedon
Section: Redis2.6
Parent ID: 8528ba93-fbb3-4f8a-b321-ebef5cf08c48

### Child 1
Child ID: 44b091a9-9303-455f-b3d4-82b7a4ebea80
Child Index: 0
Estimated Token Count: 262
正文：
Redis2.6在2012年正是发布，经历了17个版本，到2.6.17版本，相对于Redis2.4，主要特性如下： 1）服务端支持Lua脚本。 2）去掉虚拟内存相关功能。 3）放开对客户端连接数的硬编码限制。 4）键的过期时间支持毫秒。 5）从节点支持只读功能。 6）两个新的位图命令：bitcount和bitop。 7）增强了redis-benchmark的功能：支持定制化的压测，CSV输出等功能。 8）基于浮点数自增命令：incrbyfloat和hincrbyfloat。 9）redis-cli可以使用--eval参数实现Lua脚本执行。 10）shutdown命令增强。 11）重构了大量的核心代码，所有集群相关的代码都去掉了，cluster功能将会是3.0版本最大的亮点。 12）info可以按照section输出，并且添加了一些统计项 13）sort命令优化
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent 9714a0b5-0be5-4e3d-819e-2fc16ed0667b

Document: 8b442ea2-f9dd-4550-a65b-06f30d80a1b6 — 大Key和热Key的找出优化与预防方法-云数据库 Tair（兼容 Redis®）-阿里云
Section: 大Key和热Key的找出优化与预防方法-云数据库 Tair（兼容 Redis®）-阿里云
Parent ID: 9714a0b5-0be5-4e3d-819e-2fc16ed0667b

### Child 1
Child ID: 8d4e0f65-1c79-4b7c-9f1a-5544eff04adf
Child Index: 0
Estimated Token Count: 675
正文：
大Key和热Key的找出优化与预防方法-云数据库 Tair（兼容 Redis®）-阿里云 官方文档 Big keys（大 Key）与 Hot keys（热 Key）可能导致服务性能下降、请求超时，甚至引发系统故障。本文介绍如何快速找出和优化大 Key 与热 Key，分析其产生原因及影响，并提供预防措施以降低对业务的影响。 步骤一：快速找出大 Key 和热 Key 阿里云控制台工具 Tair 和 Redis 在控制台提供了 Top Key 统计和离线全量 Key 分析功能帮助您快速找出大 Key 与热 Key。 方法 使用限制 说明 操作步骤 Top Key 统计 （推荐） 仅 Redis 开源版 5.0 及以上版本和 Tair（企业版） 内存型、持久内存型支持该功能。 实时显示每个分片中各数据类型前三的大 Key 和热 Key 信息。 支持查看 4 天内大 Key 和热 Key 的历史信息。 访问 实例列表 ，在上方选择地域，然后单击目标实例 ID。 在左侧导航栏，单击 CloudDBA > 实时 Top Key 统计 或 离线全量 Key 分析 。 离线全量 Key 分析 单副本实例或 磁盘型实例不支持该功能。 对 RDB 备份文件进行定制化的分析，得出 Key 在内存中的占用和分布、Key 过期时间等信息。 时效性差，RDB 文件较大时耗时较长。 无法分析热 Key 信息。 如果您的实例不能使用上述功能，请参考以下方法。 其他方法找出大 Key 和热 Key 方法 优缺点 说明 通过 redis-cli 的 bigkeys 、 memkeys 和 hotkeys 参数 优点：方便、快速、安全。 缺点：分析结果不可定制化，准确性与时效性差；需要遍历实例当前所有 Key，可能影响实例性能。 redis-cli 的 bigkeys 、 memkeys 与 hotkeys 参数能获取 Key 的整体统计信息与每个数据类型中 Top1 的大 Key 或热 Key。 区别如下： bigkeys ：统计大 Key 信息，集合或列表类型返回元素个数。 memkeys ：统计大 Key 信息，返回所有数据类型所占内存大小。 hotkeys ：统计热 Key 信息。 支持的数据类型：STRING、LIST、HASH、SET、ZSET、STREAM。 以 bigkeys 为例，命令示例为 redis-cli -h r-***************.redis.
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 2
Child ID: f24fcfdb-a666-43e3-8908-51a4c427aeb3
Child Index: 1
Estimated Token Count: 790
正文：
型返回元素个数。 memkeys ：统计大 Key 信息，返回所有数据类型所占内存大小。 hotkeys ：统计热 Key 信息。 支持的数据类型：STRING、LIST、HASH、SET、ZSET、STREAM。 以 bigkeys 为例，命令示例为 redis-cli -h r-***************.redis. rds.aliyuncs.com -a <password> --bigkeys 。 通过内置命令对目标 Key 进行分析 优点：对线上服务影响小。 缺点：返回的 Key 序列化长度并不等同于它在内存空间中的真实长度，因此不够准确，仅可作为参考。 对不同数据类型的目标 Key，分别通过如下风险较低的命令进行分析，来判断目标 Key 是否符合大 Key 判定标准。 STRING 类型： STRLEN 命令，返回对应 Key 的 value 的字节数。 LIST 类型： LLEN 命令，返回对应 Key 的列表长度。 HASH 类型： HLEN 命令，返回对应 Key 的成员数量。 SET 类型： SCARD 命令，返回对应 Key 的成员数量。 ZSET 类型： ZCARD 命令，返回对应 Key 的成员数量。 STREAM 类型： XLEN 命令，返回对应 Key 的成员数量。 说明 DEBUG OBJECT 与 MEMORY USAGE 命令在执行时需占用较多资源，且时间复杂度为 O(N)，有阻塞实例的风险，不建议使用。 通过业务层定位热 Key 优点：可准确并及时地定位热 Key。 缺点：业务代码复杂度的增加，同时可能会降低一些性能。 通过在业务层增加相应的代码对实例的访问进行记录并异步汇总分析。 通过 redis-rdb-tools 工具以定制化方式找出大 Key 优点：支持定制化分析，对线上服务无影响。 缺点：时效性差，RDB 文件较大时耗时较长。 Redis-rdb-tools 是通过 Python 编写的开源工具，支持定制化分析 RDB 快照文件。 下载 RDB 文件 后，您可以根据业务需求分析实例中所有 Key 的内存占用情况，并支持灵活地查询。 通过 MONITOR 命令找出热 Key 优点：方便、安全。 缺点：会占用 CPU、内存、网络资源，时效性与准确性较差。 MONITOR 命令能够忠实地打印实例中的所有请求，包括时间信息、Client 信息、命令以及 Key 信息。 在发生紧急情况时，可以通过短暂执行 MONITOR 命令并将返回信息输入至文件，在关闭 MONITOR 命令后，对文件中请求进行归类分析，找出这段时间中的热 Key。 说明 由于 MONITOR 命令对实例性能消耗较大，非特殊情况不推荐使用 MONITOR 命令。 步骤二：优化大 Key 与热 Key 大 Key 方案 适用场景 操作建议 清理过期
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 3
Child ID: b450fa80-4dae-4451-80c6-5a5e5ed9cd63
Child Index: 2
Estimated Token Count: 854
正文：
归类分析，找出这段时间中的热 Key。 说明 由于 MONITOR 命令对实例性能消耗较大，非特殊情况不推荐使用 MONITOR 命令。 步骤二：优化大 Key 与热 Key 大 Key 方案 适用场景 操作建议 清理过期数据 大量 过期数据堆积，如 HASH 中未清理的增量数据。 通过 HSCAN 命令配合 HDEL 命令对失效数据进行清理，避免清理大量数据造成实例阻塞。 压缩大 Key JSON、XML 文本数据等可压缩数据，如日志、配置。 序列化时启动压缩，如 GZIP、Snappy。 使用二进制序列化协议，如 Protocol Buffers。 说明 压缩和解压缩操作需要消耗额外的 CPU 资源，可能影响处理性能。 拆分大 Key 高频访问的 HASH、ZSET 等，如排行榜。 按照业务逻辑拆分，如用户 ID、时间范围。 使用分片键设计，如：user:1001:shard1、user:1001:shard2。 拆分大 Key 能有效避免数据倾斜。 转存大 Key String 类型大文件或 BLOB。 将不适用数据存至其它存储（如 OSS），并在实例中删除此类数据。 Redis 开源版 4.0 及之后版本：您可以通过 UNLINK 命令安全地删除大 Key 甚至特大 Key，该命令通过异步方式清理 Key，避免阻塞主线程。 Redis 开源版 4.0 之前的版本：建议先通过 SCAN 命令读取部分数据，然后进行删除，避免一次性删除大量 key 导致主线程阻塞。 热 Key 方案 适用场景 操作建议 在集群架构中对热 Key 进行复制 热 Key 作为整体存储在单一分片，无法通过迁移部分数据分散请求。 将热 Key 复制并迁移至其他数据分片，例如将热 Key foo 复制出 3 个内容完全一样的 Key 并命名为 foo2、foo3、foo4，将这三个 Key 迁移到其他数据分片来解决单个数据分片的热 Key 压力。 说明 该方案的缺点是需修改代码维护多个副本，且多副本间的数据一致性难以保障（例如更新操作需同步所有副本）。建议将该方案作为临时解决方案，用于缓解紧急问题。 开启读写分离 读多写少 如果开启后读请求负载依旧很高，可通过增加只读节点数量进一步缓解读请求负载。 说明 在请求量极大的场景下，主备同步会产生不可避免的延迟，此时会出现读取到脏数据的问题。因此，在读、写压力都较大且对数据一致性要求很高的场景下，不推荐开启读写分离。 步骤三：预防大 Key 和热 Key 影响业务 大 Key 和热 Key 产生的原因 Tair 和 Redis 的最小数据分布粒度为 Key。单个 Key 将存储在特定的数据分片中，且不会被拆分。业务规划不足、无效数据的堆积以及访问量的突增
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 4
Child ID: da28c124-72d6-44b8-9232-0f30c8553b09
Child Index: 3
Estimated Token Count: 441
正文：
和热 Key 影响业务 大 Key 和热 Key 产生的原因 Tair 和 Redis 的最小数据分布粒度为 Key。单个 Key 将存储在特定的数据分片中，且不会被拆分。业务规划不足、无效数据的堆积以及访问量的突增 等因素，均会使实例产生大 Key 与热 Key，如： 类别 原因 大 Key 在不适用的场景下使用 Tair 和 Redis ，易造成 Key 的 value 过大，如使用 String 类型的 Key 存放大体积二进制文件型数据； 业务上线前规划设计不足，没有对 Key 中的成员进行合理的拆分，造成个别 Key 中的成员数量过多； 未定期清理无效数据，造成如 HASH 类型 Key 中的成员持续不断地增加； 使用 LIST 类型 Key 的业务消费侧发生代码故障，造成对应 Key 的成员只增不减。 热 Key 预期外的访问量陡增，如突然出现的爆款商品、访问量暴涨的热点新闻、直播间某主播搞活动带来的大量刷屏点赞、游戏中某区域发生多个工会之间的战斗涉及大量玩家等。 大 Key 和热 Key 带来的影响 类别 影响 大 Key 客户端执行命令的时长变慢。 实例内存达到 maxmemory 上限时，可能导致操作阻塞、重要 Key 被逐出，甚至内存溢出（OOM）。 集群架构下，某个数据分片的内存使用率远超其他数据分片，无法使数据分片的内存资源达到均衡。
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent f4329fc8-5cee-490a-916d-e8652922c191

Document: 36c928af-64d7-448f-a878-055c64e9230f — 大Key/热Key分析-分布式缓存服务Redis版-常见问题 - 天翼云
Section: 大Key/热Key分析-分布式缓存服务Redis版-常见问题 - 天翼云
Parent ID: f4329fc8-5cee-490a-916d-e8652922c191

### Child 1
Child ID: 6e762405-d7b1-41c2-9672-063edea14b46
Child Index: 0
Estimated Token Count: 774
正文：
大Key/热Key分析-分布式缓存服务Redis版-常见问题 - 天翼云 活动 天翼云最新优惠活动，涵盖免费试用，产品折扣等，助您降本增效！ 息壤智算 领先开放的智算服务平台，提供算力、平台、数据、模型、应用“五位一体”智算服务体系，构建全流程的AI基础设施能力 应用商城 天翼云精选行业优秀合作伙伴及千余款商品，提供一站式云上应用服务 进入甄选商城 进入AI Store 公有云生态专区 智云上海应用生态专区 定价 协助您快速了解云产品计费模式、价格详情，轻松预估上云成本 合作伙伴 天翼云携手合作伙伴，共创云上生态，合作共赢 开发者 开发者相关功能入口汇聚 支持与服务 为您提供全方位支持与服务，全流程技术保障，助您轻松上云，安全无忧 了解天翼云 天翼云秉承央企使命，致力于成为数字经济主力军，投身科技强国伟大事业，为用户提供安全、普惠云服务 活动 息壤智算 产品 解决方案 应用商城 定价 合作伙伴 开发者 支持与服务 了解天翼云 文档 控制中心 备案 管理中心 分布式缓存服务Redis版 分布式缓存服务Redis版 分布式缓存服务Redis版 无数据 产品动态 产品简介 版本发布说明 版本发布记录 产品定义 应用场景 实例类型 Redis单机实例 Redis主备实例 Redis Proxy集群实例 Redis Cluster集群实例 读写分离实例 实例规格 Redis3.0实例 Redis4.0/5.0实例 Redis 6.0实例 开源命令兼容性 Redis3.0命令 Redis4.0命令 Redis5.0命令 Redis 6.0命令 Web CLI命令 实例受限使用命令 部分命令使用限制 缓存灾备策略 Redis版本差异 与开源服务的差异 基本概念 与其他服务的关系 权限管理 计费说明 公有云计费说明 产品价格 计费方式 计费模式 专属云计费说明 开通方式 产品价格 计费模式 快速入门 创建实例 创建前准备 准备实例依赖资源 创建Redis实例 连接实例 配置Redis网络连接 连接Redis网络要求 开启Redis公网访问并获取公网访问地址 配置Redis访问控制 配置Redis访问白名单 使用Redis-cli连接Redis实例 控制台连接Redis4.0/5.0/6.0/7.0实例 多语言连接 Java客户端 Jedis Lettuce Redisson SpringBoot集成Lettuce Python Redis客户端 Go Redi
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 2
Child ID: 573a2228-bf05-4c42-ace5-54ae1276296f
Child Index: 1
Estimated Token Count: 858
正文：
Redis访问控制 配置Redis访问白名单 使用Redis-cli连接Redis实例 控制台连接Redis4.0/5.0/6.0/7.0实例 多语言连接 Java客户端 Jedis Lettuce Redisson SpringBoot集成Lettuce Python Redis客户端 Go Redi s客户端 C++Redis客户端（hiredis） C# Redis客户端 PHP客户端 Node.js Redis客户端 查看实例信息 用户指南 监控 支持的监控指标 查看监控指标 必须配置的告警监控 密码管理 关于实例连接密码的说明 修改缓存实例密码 重置缓存实例密码 修改Redis实例的访问方式 实例备份恢复管理 备份与恢复说明 设置备份策略 手动备份实例 实例恢复 下载实例备份文件 实例日常操作 变更规格 重启实例 删除实例 主备切换 清空实例数据 导出实例列表 命令重命名 升级DCS实例小版本/代理版本 实例配置管理 配置管理说明 修改实例配置参数 修改实例维护时间窗 修改实例安全组 查看实例后台任务 查看Redis 3.0 Proxy集群实例的数据存储统计信息 分析Redis实例大Key和热Key 查询Redis实例慢查询 管理实例白名单 管理标签 扫描并删除Redis实例的过期Key 管理分片与副本 实例诊断 升级Redis3.0实例大版本 调整Redis实例带宽 恢复或销毁回收站内的DCS实例 审计 服务支持的DCS操作列表 查看云审计日志 权限管理 参数模板 查看参数模板信息 创建自定义参数模板 修改自定义参数模板 删除自定义参数模板 使用DCS迁移数据 使用DCS迁移介绍 备份文件导入方式 备份文件导入方式-OBS桶 备份文件导入方式-Redis实例 在线迁移方式 交换DCS实例IP 数据迁移指南 概述 迁移流程介绍 迁移方案说明 自建Redis迁移至DCS 使用迁移任务在线迁移自建Redis 使用备份文件离线迁移自建Redis 使用Redis-cli离线迁移自建Redis（AOF文件） 使用Redis-cli离线迁移自建Redis（RDB文件） 使用Redis-Shake工具在线迁移自建Redis Cluster集群 使用Redis-Shake工具离线迁移自建Redis Cluster集群 DCS实例间迁移 使用迁移任务在线迁移DCS Redis实例 使用备份文件离线迁移DCS Redis实例 其他云厂商Redis服务迁移至DCS 使用迁移任务在线迁移其他云厂商Redis 使用备份文件离线迁移其他云厂商Redis 使用Rump在线迁移其他云厂商Redis 使用RedisShake离线迁移其他云厂商Redis 使用Redisshake工具在线迁移其他云厂商Redis DCS实例迁移下云 常见问题 实例类型/版本 客户端和网络
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 3
Child ID: 7aedf20c-a9d1-406d-b0ec-67cad013c604
Child Index: 2
Estimated Token Count: 845
正文：
迁移其他云厂商Redis 使用Rump在线迁移其他云厂商Redis 使用RedisShake离线迁移其他云厂商Redis 使用Redisshake工具在线迁移其他云厂商Redis DCS实例迁移下云 常见问题 实例类型/版本 客户端和网络 连接 Redis使用 Redis命令 扩容缩容与实例升级 监控告警 数据备份/导出 大Key/热Key分析 主备倒换 故障排除 Redis连接失败问题排查和解决 Redis实例CPU使用率高问题排查和解决 Redis实例内存使用率高问题排查和解决 排查Redis实例带宽使用率高的问题 数据迁移失败问题排查 最佳实践 redis常见使用规范 使用Nginx实现公网访问Redis 4.0/5.0的单机主备Proxy集群实例 使用SSH隧道代理机制实现公网访问DCS实例 使用Redis实现排行榜功能 视频专区 相关协议 天翼云分布式缓存服务协议 分布式缓存服务Redis服务等级协议 文档下载 无相关产品 本页目录 帮助中心 分布式缓存服务Redis版 常见问题 大Key/热Key分析 大Key/热Key分析 更新时间 2023-10-19 13:57:52 新浪微博 微信 扫码分享 复制链接 最近更新时间: 2023-10-19 13:57:52 分享文章 新浪微博 微信 扫码分享 复制链接 本节主要介绍大Key/热Key分析 类问题 什么是大Key/热Key？ 名词 定义 大Key 大Key可以分为两种情况： Key的Value较大，例如一个String类型的Key大小达到10MB，或者一个集合类型（Hash，List，Set等）的元素总大小达到了100MB。一般单个String类型的Key大小达到10KB，或者集合类型的Key总大小达到50MB，则定义其为大Key。 Key的元素较多，例如一个Hash类型的Key，其元素数量达到了10000。一般定义集合类型的Key中元素超过5000个，则认为其为大Key。 热Key 通常以一个Key被操作的频率和占用的资源来判定其是否为热Key，例如： 某个集群实例一个分片每秒处理10000次请求，其中有3000次都是操作同一个Key。 某个集群实例一个分片的总带宽使用（入带宽+出带宽）为100Mbits/s，其中80Mbits是由于对某个Hash类型的Key执行HGETALL所占用。 存在大Key/热Key，有什么影响？ 类别 影响 大Key 造成规格变更失败。 Redis集群变更规格过程中会进行数据rebalance（节点间迁移数据），单个Key过大的时候会触发Redis内核对于单Key的迁移限制，造成数据迁移超时失败，Key越大失败的概率越高，大于512MB的Key可能会触发该问题。 造成数据迁移失败。
自动质量检查：
- navigation_noise: yes
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 4
Child ID: ac37d2dc-d755-422a-aa63-baa5d302b2ce
Child Index: 3
Estimated Token Count: 497
正文：
据rebalance（节点间迁移数据），单个Key过大的时候会触发Redis内核对于单Key的迁移限制，造成数据迁移超时失败，Key越大失败的概率越高，大于512MB的Key可能会触发该问题。 造成数据迁移失败。 数据迁移过程中，如果一个大Key的元素过多，则会阻塞后续Key的迁移，后续Key的数据会放到迁移机的内存Buffer中，如果阻塞时间太久，则会导致迁移失败。 容易造成集群分片不均的情况。 各分片内存使用不均。例如某个分片占用内存较高甚至首先使用满，导致该分片Key被逐出，同时也会造成其他分片的资源浪费。 各分片的带宽使用不均。例如某个分片被频繁流控，其他分片则没有这种情况。 客户端执行命令的时延变大。 对大Key进行的慢操作会导致后续的命令被阻塞，从而导致一系列慢查询。 导致实例流控。 对大Key高频率的读会使得实例出方向带宽被打满，导致流控，产生大量命令超时或者慢查询，业务受损。 导致主备倒换。 对大Key执行危险的DEL操作可能会导致主节点长时间阻塞，从而导致主备倒换。 热Key 容易造成集群分片不均的情况。 造成热Key所在的分片有大量业务访问而同时其他的分片压力较低。这样不仅会容易产生单分片性能瓶颈，还会浪费其他分片的计算资源。 使得CPU冲高。 对热Key的大量操作可能会使得CPU冲高，如果表现在集群单分片中就可以明显地看到热Key所在
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent d6ec4f7e-6ffb-4576-8719-85a80fa3a6e6

Document: 82d5865b-d8cc-4b07-a965-112b9bd65bda — Redis 篇-深入了解分布式锁 Redisson 原理（可重入原理、可重试原理、主从一致性原理、解决超时锁失效）_redis可重入锁原理-CSDN博客
Section: Redis 篇-深入了解分布式锁 Redisson 原理（可重入原理、可重试原理、主从一致性原理、解决超时锁失效）_redis可重入锁原理-CSDN博客
Parent ID: d6ec4f7e-6ffb-4576-8719-85a80fa3a6e6

### Child 1
Child ID: 9b76a641-e132-42a7-99cd-d8449e424457
Child Index: 0
Estimated Token Count: 698
正文：
1）尝试获取锁： 先判断缓存中是否存在 key 字段，如果存在，则说明锁已经被成功获取，这时候需要继续判断成功获取锁的对象是否为当前线程，如果根据 key field 来判断是当前线程，则 value += 1 且还需要重置锁的超时时间；如果根据 key field 判断不是当前线程，则直接返回 null。如果缓存中不存在 key 字段，则说明锁还没有被其他线程获取，则获取锁成功。 2）释放锁： 当业务完成之后，在释放锁之前，先判断获取锁的对象是不是当前线程，如果不是当前线程，则说明可能由于超时，锁已经被自动释放了，这时候直接返回 null；如果是当前线程，则进行 value -= 1 ，最后再来判断 value 是否大于 0 ，当大于 0 时，则不能直接释放锁，需要重置锁的超时时间；当 value = 0 时，则可以真正的释放锁。 如图： 又因为使用 Java 实现不能保证原子性，所以需要借助 Lua 脚本实现多条 Redis 命令来保证原则性。 尝试获取锁的 Lua 脚本： 释放锁的 Lua 脚本： 5.0 Redisson 锁重试原理 在之前基于 setnx 实现的分布式锁，获取锁只尝试一次就返回 false ，没有重试机制。 而 Redisson 是如何实现锁重试的呢？ 实现锁重试 追踪源代码： 得到该类： 首先，将等待时间转换为毫秒，接着获取当前时间和获取当前线程 ID ，再接着第一个尝试去获取锁，将参数 waitTime 最大等待时间，leaseTime 锁的超时时间，unit 时间单位，threadId 当前线程 ID 传进去 tryAcquire 方法中。 紧接着来查看 tryAcquire 方法： 再查看调用的 tryAcquireAsync 方法： 当指定了 leaseTime 锁的超时时间，则会调用 tryLockInnerAsync 方法；当没有指定 leaseTime 锁的超时时间，则会调用 getLockWatchdogTimeout 方法，默认超时时间为 30 秒。 接着查看 tryLockInnerAsync 方法： 可以看到，这就是尝试获取是的 Lua 脚本执行多条 Redis 命令。 细心可以发现，如果正常获取锁，则返回 null ；如果获取锁失败，则返回当前锁的 TTL ，锁的剩余时间。 因此最后将当前锁的 TTL 返回赋值给 Long ttl 变量。 再接着往下： 当 ttl == null ，则说明当前
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 2
Child ID: f853d0c7-270a-46da-9eee-4e4d526ee648
Child Index: 1
Estimated Token Count: 797
正文：
命令。 细心可以发现，如果正常获取锁，则返回 null ；如果获取锁失败，则返回当前锁的 TTL ，锁的剩余时间。 因此最后将当前锁的 TTL 返回赋值给 Long ttl 变量。 再接着往下： 当 ttl == null ，则说明当前 线程成功获取锁，因此就不需要接着往下再次尝试去获取锁了。相反，当 ttl != null ，则需要接着往下走，重新尝试去获取锁。 判断 time 等于当前时间减去在第一次获取锁之前的时间，time 也就是最大的等待时间还剩多少。判断 time 是否小于 0 ，若小于 0 则已经到了最大等待时间了，所以不需要再继续等下去了，直接返回 false 即可。 若 time 还是大于 0 ，则接着往下走： 调用 subscribe 方法，该方法可以理解成订阅锁，一旦锁被释放之后，该方法就会收到通知，然后再去尝试获取锁。 回顾在释放锁的时候，使用 Redis 命令中的 redis.call('publish', KEYS[2], ARGV[1]) 来发布消息，通知锁已经被释放，一旦锁被释放，那么就可以成功订阅。 因此，在订阅锁的过程中，并不是一直死等下去，而是在 time 剩余最大等待时间之内，如果可以订阅锁成功，才会去尝试获取锁。如果在 time 时间内，订阅锁失败，则会取消订阅，再返回 false 。 接着往下走，当在 time 时间内订阅锁成功，会更新 time 时间，也就是更新最大的等待时间，判断 time 小于 0 ，则返回 false ，如果 time 还是大于 0 ，则到了真正尝试第二次获取锁，调用 tryAcquire(waitTime, leaseTime, unit, threadId) 方法，将返回值再次赋值给变量 ttl ，判断 ttl == null ，则说明成功获取锁了，直接返回 true ；判断 ttl != null ，则第二次获取锁还是失败，由需要更新 time 了，因为在调用尝试获取锁的过程中，消耗时间还是挺大的，同理，判断更新完之后的 time 是否大于 0，如果 time 小于 0，则超过了剩余最大锁的超时时间，返回 false ； 如果判断 time 仍旧大于 0 ： 那么先判断锁的过期时间 ttl 与 剩余时间 time ，如果 ttl < time ，则类似订阅方法一样的思路，选择等待 ttl 锁的过期时间，当 ttl 过期之后，就会订阅该锁；如果 time < ttl ，则 ttl 还没有释放，就不需要等 ttl 了，等到 time 结束还没有订阅到锁，则 time 也就小于 0 了，如果在 time 时间内获取到锁，再次尝试去获取锁，同样的，当在 ttl 时间内，成功订阅了，而且 time > 0 ，则会第
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 3
Child ID: fc9f1a15-0a08-45ed-b5bb-08dc214659b4
Child Index: 2
Estimated Token Count: 831
正文：
还没有释放，就不需要等 ttl 了，等到 time 结束还没有订阅到锁，则 time 也就小于 0 了，如果在 time 时间内获取到锁，再次尝试去获取锁，同样的，当在 ttl 时间内，成功订阅了，而且 time > 0 ，则会第 三次去尝试获取锁。之后的步骤都是如此，这里使用了 do whlie 循环，判断循环成立为 time > 0，当 time < 0 ，则会退出循环。 总结，在解决可重试锁过程中，并不是循环不断的调用 tryAcquire(waitTime, leaseTime, unit, threadId) 方法来获取锁，这样容易造成 CPU 的浪费，而是通过等待锁释放，再去获取锁的方式来实现的可重试锁，利用信号量（Semaphore）和发布/订阅（PubSub）模式实现等待、唤醒、获取锁失败的重试机制。 6.0 Redisson WatchDog 机制 在之前基于 setnx 实现的分布式锁，锁超时释放虽然可以避免死锁，但是如果是业务执行耗时较长，也会导致锁释放，存在安全隐患。 6.1 Redisson 是如何解决超时释放问题的呢？ 解决超时释放的核心是：当 leaseTime == -1 时，为了保证当前业务执行完毕才能释放锁，而不是业务还没有执行完毕，锁就被自动释放了。 追踪源代码： 当 leaseTime == -1 时，默认锁的最大超时时间为 30 秒，会执行以下代码。 接着点进去： WatchDog 会在锁的过期时间到期之前，定期向 Redis 发送续约请求，更新锁的过期时间。这通常是通过设置一个较短的过期时间和一个续约间隔来实现的。 如果持有锁的线程正常释放锁，WatchDog 会停止续约操作。如果持有锁的线程崩溃或失去响应，WatchDog 会在锁的过期时间到达后自动释放锁。 简单概述一下 WatchDog 机制：在获取锁成功之后，就会调用 scheduleExpirationRenewal(threadId) 方法开启自动续约，具体是由在 map 中添加业务名称和任务定时器，这个定时器会在一定时间内执行，比如说 10 秒就会自动开启任务，而该定时器中的任务就是不断的重置锁的最大超时时间，使用递归，不断的调用重置锁的时间，这就保证了锁是永久被当前线程持有。 这样就可以保证执行业务之后，才会释放锁。释放锁之后，会取消定时任务。 7.0 Redisson MultiLock 原理 7.1 Redisson 分布式锁是如何解决主从一致性问题的呢？ 先搞清楚什么是主从一致性问题，在集群的 Redis 中会区分出主力机和一般机器，在写 Redis 命令会放到主力机中运行，而主力机和一般机器需要保证数据都是一样的，也就是主从同步数据，在主力机中执行写命令时
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 4
Child ID: d7a15564-e469-464f-9e49-364964ca55c3
Child Index: 3
Estimated Token Count: 513
正文：
从一致性问题，在集群的 Redis 中会区分出主力机和一般机器，在写 Redis 命令会放到主力机中运行，而主力机和一般机器需要保证数据都是一样的，也就是主从同步数据，在主力机中执行写命令时 ，突然发生宕机，未来得及将数据同步到其他一般机器中，而且当主力机宕机之后，会选出一台一般机器充当主力机，这时候的主力机没有同步之前的数据，那么其他线程再来写命名的时候就会出现问题了，这出现了主从不一致性。 那么 Redisson 是如何来解决该问题呢？ 在多主架构中，每台主机都可以接收写请求，这样即使某一台主机宕机，其他主机仍然可以继续处理写请求。 当某一台主机宕机后，如果在它恢复之前有新的写操作发生，可能会导致数据不一致。通过比较不同主机的数据状态，可以很容易地发现这些不一致的问题。 当宕机的主机恢复后，可以通过与其他主机的数据进行比较，找出差异并进行数据同步，确保所有主机的数据一致。 简单来说，设置多台主力机，每一次写命令都是一式多份，当某一台主力机出现宕机了，主从未来得及同步时，再写命令，同样一式多份，这样充当主力机出现了跟其他主力机不同的结果时，就很容易的发现问题了。 通过设置多台主力机并进行写操作的多份复制，可以有效提高系统的可靠性，并在出现问题时快速发现和解决数据不一致的问题。 具体使用： 本文章已经生成可运行项目 一键运行 生成项目
自动质量检查：
- navigation_noise: no
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Parent de32f0b9-3013-4ba6-b397-d7c61376827b

Document: 142392dc-c95f-40df-b724-6bc0d7f9fa6c — 帮我调研SSE，要求400字（指：Server-Sent Events (SSE; HTTP EventSource server push)）
Section: 参考文献
Parent ID: de32f0b9-3013-4ba6-b397-d7c61376827b

### Child 1
Child ID: e39cbe02-1edf-43a1-a45f-f0faa1cda823
Child Index: 0
Estimated Token Count: 447
正文：
<a id="ref-1"></a>**[1]** zh.wiktionary.org — 帮 - 维基词典，自由的多语言词典 URL: https://zh.wiktionary.org/wiki/%E5%B8%AE 原文片段：「帮 - 维基词典，自由的多语言词典 跳转到内容 維基詞典，自由的多語言詞典 帮 U+5E2E , &#24110; 中日韓統一表意文字-5E2E ← 席 [U+5E2D] 中日韓統一表意文字 帯 → [U+5E2F] 跨語言 [ 编辑 ] 筆順 繁體中文 幫 日本新字体 幇 简体中文 帮 漢字 [ 编辑 ] 帮 （ 巾部 +7畫，共10畫， 倉頡碼 ：手中中月（ QLLB ）， 四角號碼 ： 5722 7 ， 部件組合 ： ⿱ 邦 巾 ） 來源 [ 编辑 ] 康熙字典 ：未收錄，如收錄將位於 第332页 第12字的下一個 大漢和辭典 ：第8928字 大字...」 <a id="ref-2"></a>**[2]** prepedu.com — Cách dùng 3 từ 帮, 帮忙 và 帮助 trong tiếng Trung URL: https://prepedu.com/vi/blog/bang-bangmang-va-bangzhu-tieng-trung 原文片段：「Cách dùng 3 từ 帮, 帮忙 và 帮助 trong tiếng Trung Phân biệt 帮, 帮忙 và 帮助 trong tiếng Trung HSK TỪ VỰNG Quy tắc biên tập và xuất bản nội dung 帮, 帮忙 và 帮助 trong tiếng Trung đều mang ý nghĩa là “giúp đỡ”. Vậy 3 từ này dùng trong trường hợp nào? Theo dõi bài viết dưới đây để được PREP hướn...」
自动质量检查：
- navigation_noise: yes
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 2
Child ID: 776f3a65-b66e-4b11-a096-66608f5454a4
Child Index: 1
Estimated Token Count: 501
正文：
ội dung 帮, 帮忙 và 帮助 trong tiếng Trung đều mang ý nghĩa là “giúp đỡ”. Vậy 3 từ này dùng trong trường hợp nào? Theo dõi bài viết dưới đây để được PREP hướn...」 <a id="ref-3"></a>**[3]** cnblogs.com — SSE（Server-Sent Events）圣经： 底层原理 + 应用开发 + 技术对比 （图解+秒懂+史上最全） - 技术自由圈 - 博客园 URL: https://www.cnblogs.com/crazymakercircle/p/19065461 原文片段：「SSE（Server-Sent Events）圣经： 底层原理 + 应用开发 + 技术对比 （图解+秒懂+史上最全） - 技术自由圈 - 博客园 疯狂创客圈 SSE（Server-Sent Events）圣经： 底层原理 + 应用开发 + 技术对比 （图解+秒懂+史上最全） 本文 的 原文 地址 原始的内容，请参考 本文 的 原文 地址 本文 的 原文 地址 尼恩说在前面 在45岁老架构师 尼恩的 读者交流群 (50+)中，通过 Java+AI双驱架构 帮助很多小伙伴拿到了一线企业如 字节、得物、阿里、滴滴、极兔、有赞、希音、百度、网易、美团、蚂蚁、得物...」 <a id="ref-4"></a>**[4]** dev.to — Deep Dive into Server-sent Events (SSE) - DEV Community URL: https://dev.to/debajit13/deep-dive-into-server-sent-events-sse-52 原文片段：「Deep Dive into Server-sent Events (SSE) - DEV Community Add reaction Like Unicorn Exploding Head Raised Hands Fire Jump to Comments Save Boost Copy link Copied to Clipboard Share to X Share to LinkedIn Share to Facebook Share to Mastodon Report Abuse Introduction We've all built...」
自动质量检查：
- navigation_noise: yes
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 3
Child ID: 83e8fb99-a4eb-4fe7-9f92-dff9776986ff
Child Index: 2
Estimated Token Count: 501
正文：
Community Add reaction Like Unicorn Exploding Head Raised Hands Fire Jump to Comments Save Boost Copy link Copied to Clipboard Share to X Share to LinkedIn Share to Facebook Share to Mastodon Report Abuse Introduction We've all built...」 <a id="ref-5"></a>**[5]** kimi.com — Server-Sent Events (SSE) 技术详解 URL: https://www.kimi.com/preview/197bf3c5-a5c1-878a-8825-cfbcc8000519 原文片段：「Server-Sent Events (SSE) 技术详解 Server-Sent Events 技术详解 基于 HTTP 的服务器推送技术，实现高效、简单的单向实时通信 实时通信 轻量级 HTTP 标准 核心价值 单向推送 服务器主动推送更新，无需客户端轮询 自动重连 内置断线重连与消息续传机制 简单实现 基于标准 HTTP，易于集成部署 SSE 技术概述 什么是 Server-Sent Events Server-Sent Events (SSE) 是一种基于 HTTP 的服务器推送技术，它允许服务器将实时更新主动发送到客户端（通常是 Web 浏览器...」 <a id="ref-6"></a>**[6]** nimbleway.com — Server-Sent Events vs WebSockets: Key Differences and Use Cases in 2026 URL: https://www.nimbleway.com/blog/server-sent-events-vs-websockets-what-is-the-difference-2026-guide 原文片段：「Server-Sent Events vs WebSockets: Key Differences and Use Cases in 2026 Announcing Web Search Agents Self-learning web search for your domain Learn More Login Sign Up Get Expert-Level Web Search for Your AI Agents Let's talk about your use cases and show you how Nimble delivers h...」
自动质量检查：
- navigation_noise: yes
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

### Child 4
Child ID: 18a489f4-95a4-49a6-8ab6-2d0cc9150668
Child Index: 3
Estimated Token Count: 208
正文：
in 2026 Announcing Web Search Agents Self-learning web search for your domain Learn More Login Sign Up Get Expert-Level Web Search for Your AI Agents Let's talk about your use cases and show you how Nimble delivers h...」 <a id="ref-7"></a>**[7]** ably.com — ably.com URL: https://ably.com/blog/websockets-vs-sse 原文片段：「On this page WebSockets and Server-Sent Events are commonly used in realtime applications where quick and efficient data transfer is a critical requirement. The expectations of realtime experiences in applications has only grown with time, with improving technology and understand...」
自动质量检查：
- navigation_noise: yes
- text_complete: yes
- obvious_duplicate: no
- auto_status: needs_human_review
人工审核：
[ ] Clean / 可用于 Gold
[ ] Unusable
[ ] 需要相邻 Child 才完整
可支持的事实点（留空，人工填写）：

人工备注：

## Human Review Results (v1)

### 881ee352-b7c6-4fa1-83c8-e1f802d1f129
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 5224115d-af43-447a-a96f-ae12459c0d9b
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### da6f4372-fa23-4d84-b2f3-98dd256253f0
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 解锁前必须校验锁持有者
  - Lua 可原子执行 compare-and-delete
  - 单 Redis 实例存在单点故障风险
### b39ddde1-9b8a-46d1-bcfc-23c468c1634f
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redlock 在多个独立 Redis 实例上申请锁
  - 使用随机唯一 value 标识锁所有者
  - 多数实例成功是获取锁的核心条件
### 7854e15d-b9bf-4382-917f-be979ebca791
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redis 主从异步复制可能导致故障切换后锁丢失
  - Redlock 要求至少 N/2+1 节点成功
  - 获取耗时必须小于锁有效期
### dfef6d0c-18a6-4651-9ad2-4cf3ed6aa4db
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redlock 节点可以彼此独立
  - 客户端应保持低延迟通信
  - 可使用多路复用并行发送 SET 请求
### 1cc83662-096d-4bb9-be35-bc9a7e8b844c
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - fencing token 要求资源服务器能够拒绝旧 token
  - 文中讨论使用随机锁 value 配合资源侧校验的方案
### 3e1c8633-3aba-45ed-b7a8-d8ac46803fae
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 文中区分分布式锁的互斥性与操作顺序性
  - ZooKeeper 可利用临时节点实现锁生命周期管理
### ca51e67f-0d3e-4452-902c-4ba2cea05965
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - ZooKeeper Session 通过心跳维持临时节点
  - 长进程暂停可能导致 Session 过期及锁丢失
  - 极端情况下分布式锁不能替代资源层一致性兜底
### 79ee9853-ab18-4e37-b727-a87c643ab063
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Ping 测 RTT 与目标连接稳定性
  - Traceroute 展示数据包经过的 Hop 路径
### 0727ac9b-a72e-485c-bb0f-e2afbab30777
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 04dc005d-210b-4537-ac99-54ebcb5048dc
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7cb50cf1-a34a-413b-a1eb-65b3f63a1e4a
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### b6568712-4048-4f21-a94a-dbd2dc476060
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### cd44e304-434b-4a35-8a69-ae001738bd11
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7ce2d1e9-1f93-431a-916e-32a4e5c2b084
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### c8bb7bc9-148d-484b-8640-2c75872ffc94
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 并发更新数据库和缓存可能产生旧缓存覆盖新值
  - 先删缓存再更新数据库存在读请求回填旧值窗口
### 62e6e94b-7c6d-425b-8506-20a2f78d8e1f
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### c4145c16-3a0d-438f-8b4f-4156e0e68206
- human_status: B
- usable_for_gold: true
- needs_neighbor: true
- fact_points:
  - 进程暂停和网络延迟可能持续很长时间
  - 这类暂停会破坏基于固定租约时间的安全假设
  - 必须结合相邻上下文使用
### da1668e8-f06e-4181-b382-1feedc6d4187
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 可使用 Hash 中线程标识和计数实现可重入
  - Lua 同时维护计数和 PEXPIRE
### a3d8f9ec-9e3c-4b75-9d23-c6f423bc9911
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 解锁应校验 requestId
  - Lua 将 GET 校验和 DEL 合并为原子操作
### c7e2bfee-252e-4f4d-a5ec-76c6c89793e3
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 723b50ac-8359-492e-9e5b-5295a356e5df
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 398521a8-0d16-4f5d-9575-165f972e6ad5
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - ZooKeeper 使用临时有序节点竞争锁
  - 未获得锁的客户端监听前驱节点
  - 前驱释放后重新判断是否获得锁
### fb18e10b-3846-43da-8584-c83729afdfc3
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 临时节点随客户端故障自动删除
  - Curator 提供可重入锁、不可重入锁、读写锁和 MultiLock
### c3c1c313-3662-4dc7-bff6-309e3b9e45d1
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 锁粒度过粗会降低并发
  - 可按资源 ID 或分段方式细化锁
  - 网络分区可能产生锁状态冲突
### ff651920-a885-4987-a701-a674ef6f6afd
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 锁先过期而业务未完成可能导致误删其他客户端的锁
  - 唯一客户端 ID 可标识锁所有权
  - SET NX EX/PX 与 Lua 解锁用于提高原子性
### f358f7db-de57-4f73-bd5a-9799f2906cb4
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 读锁之间可共享
  - 读写、写写需要互斥
  - 分段锁可以降低锁粒度提高并发
### 18ef18ce-af28-4e21-a178-85e3c4fef41c
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 6e0f67c6-e44e-4597-823e-51ac8009e18e
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 单一热 Key 会形成单实例热点
  - 单纯扩容不能自动分散同一个 Key 的请求
  - 可通过业务预估、客户端、代理层和 Redis 工具发现热 Key
### ec679cc8-0bab-4a42-8c82-71b8ccc41ffe
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 35347050-3659-4e4a-b7e6-c938ac30ba95
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### ac6450de-8c72-4522-8dd9-b8bd93481f33
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7900c458-dc24-41a4-93c1-3fca0890926b
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Ping 正常结果包含 RTT、TTL 等字段
  - Unknown host 对应名称解析问题
  - Destination host unreachable 对应路由问题
  - Request timed out 可能与不可达或 ICMP 丢弃有关
### 44b091a9-9303-455f-b3d4-82b7a4ebea80
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redis 2.6 支持 Lua
  - 键过期精度支持毫秒
  - 从节点支持只读
  - redis-cli 支持 --eval
### 8d4e0f65-1c79-4b7c-9f1a-5544eff04adf
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Top Key 与离线全量分析的能力差异
  - bigkeys、memkeys、hotkeys 的用途差异
### f24fcfdb-a666-43e3-8908-51a4c427aeb3
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - STRLEN/LLEN/HLEN/SCARD/ZCARD/XLEN 可辅助分析不同类型 Key
  - MONITOR 会消耗资源，不建议长期使用
  - 业务层或 RDB 工具可定位热点/大 Key
### b450fa80-4dae-4451-80c6-5a5e5ed9cd63
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 可通过清理、压缩、拆分、转存处理
  - UNLINK 可异步删除大 Key
  - 热 Key 可通过副本或读写分离缓解，但存在一致性权衡
### da28c124-72d6-44b8-9232-0f30c8553b09
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 常由数据过大、成员过多或无效数据累积产生
  - 热 Key 可由突发访问量产生
  - 大 Key 会导致内存和分片资源不均
### 6e762405-d7b1-41c2-9672-063edea14b46
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 573a2228-bf05-4c42-ace5-54ae1276296f
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7aedf20c-a9d1-406d-b0ec-67cad013c604
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### ac37d2dc-d755-422a-aa63-baa5d302b2ce
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 可导致 rebalance/迁移失败和命令阻塞
  - 热 Key 可造成单分片 CPU 与带宽压力
### 9b76a641-e132-42a7-99cd-d8449e424457
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 使用线程标识和重入计数维护可重入锁
  - 获取失败时返回 TTL 进入等待/重试流程
  - 未显式指定 leaseTime 时文中给出默认 watchdog timeout
### f853d0c7-270a-46da-9eee-4e4d526ee648
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 获取失败后不会简单忙轮询
  - 使用 Pub/Sub 等待锁释放通知
  - 重试受到剩余 waitTime/TTL 限制
### fc9f1a15-0a08-45ed-b5bb-08dc214659b4
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 重试通过等待与唤醒避免持续占用 CPU
  - WatchDog 在业务未完成时周期性续约
  - 正常释放后停止续约，客户端异常后最终由 TTL 释放
### d7a15564-e469-464f-9e49-364964ca55c3
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### e39cbe02-1edf-43a1-a45f-f0faa1cda823
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 776f3a65-b66e-4b11-a096-66608f5454a4
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 83e8fb99-a4eb-4fe7-9f92-dff9776986ff
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 18a489f4-95a4-49a6-8ab6-2d0cc9150668
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A

## Human Review Results (v1)

### 881ee352-b7c6-4fa1-83c8-e1f802d1f129
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 5224115d-af43-447a-a96f-ae12459c0d9b
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### da6f4372-fa23-4d84-b2f3-98dd256253f0
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 解锁前必须校验锁持有者
  - Lua 可原子执行 compare-and-delete
  - 单 Redis 实例存在单点故障风险
### b39ddde1-9b8a-46d1-bcfc-23c468c1634f
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redlock 在多个独立 Redis 实例上申请锁
  - 使用随机唯一 value 标识锁所有者
  - 多数实例成功是获取锁的核心条件
### 7854e15d-b9bf-4382-917f-be979ebca791
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redis 主从异步复制可能导致故障切换后锁丢失
  - Redlock 要求至少 N/2+1 节点成功
  - 获取耗时必须小于锁有效期
### dfef6d0c-18a6-4651-9ad2-4cf3ed6aa4db
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redlock 节点可以彼此独立
  - 客户端应保持低延迟通信
  - 可使用多路复用并行发送 SET 请求
### 1cc83662-096d-4bb9-be35-bc9a7e8b844c
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - fencing token 要求资源服务器能够拒绝旧 token
  - 文中讨论使用随机锁 value 配合资源侧校验的方案
### 3e1c8633-3aba-45ed-b7a8-d8ac46803fae
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 文中区分分布式锁的互斥性与操作顺序性
  - ZooKeeper 可利用临时节点实现锁生命周期管理
### ca51e67f-0d3e-4452-902c-4ba2cea05965
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - ZooKeeper Session 通过心跳维持临时节点
  - 长进程暂停可能导致 Session 过期及锁丢失
  - 极端情况下分布式锁不能替代资源层一致性兜底
### 79ee9853-ab18-4e37-b727-a87c643ab063
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Ping 测 RTT 与目标连接稳定性
  - Traceroute 展示数据包经过的 Hop 路径
### 0727ac9b-a72e-485c-bb0f-e2afbab30777
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 04dc005d-210b-4537-ac99-54ebcb5048dc
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7cb50cf1-a34a-413b-a1eb-65b3f63a1e4a
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### b6568712-4048-4f21-a94a-dbd2dc476060
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### cd44e304-434b-4a35-8a69-ae001738bd11
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7ce2d1e9-1f93-431a-916e-32a4e5c2b084
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### c8bb7bc9-148d-484b-8640-2c75872ffc94
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 并发更新数据库和缓存可能产生旧缓存覆盖新值
  - 先删缓存再更新数据库存在读请求回填旧值窗口
### 62e6e94b-7c6d-425b-8506-20a2f78d8e1f
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### c4145c16-3a0d-438f-8b4f-4156e0e68206
- human_status: B
- usable_for_gold: true
- needs_neighbor: true
- fact_points:
  - 进程暂停和网络延迟可能持续很长时间
  - 这类暂停会破坏基于固定租约时间的安全假设
  - 必须结合相邻上下文使用
### da1668e8-f06e-4181-b382-1feedc6d4187
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 可使用 Hash 中线程标识和计数实现可重入
  - Lua 同时维护计数和 PEXPIRE
### a3d8f9ec-9e3c-4b75-9d23-c6f423bc9911
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 解锁应校验 requestId
  - Lua 将 GET 校验和 DEL 合并为原子操作
### c7e2bfee-252e-4f4d-a5ec-76c6c89793e3
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 723b50ac-8359-492e-9e5b-5295a356e5df
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 398521a8-0d16-4f5d-9575-165f972e6ad5
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - ZooKeeper 使用临时有序节点竞争锁
  - 未获得锁的客户端监听前驱节点
  - 前驱释放后重新判断是否获得锁
### fb18e10b-3846-43da-8584-c83729afdfc3
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 临时节点随客户端故障自动删除
  - Curator 提供可重入锁、不可重入锁、读写锁和 MultiLock
### c3c1c313-3662-4dc7-bff6-309e3b9e45d1
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 锁粒度过粗会降低并发
  - 可按资源 ID 或分段方式细化锁
  - 网络分区可能产生锁状态冲突
### ff651920-a885-4987-a701-a674ef6f6afd
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 锁先过期而业务未完成可能导致误删其他客户端的锁
  - 唯一客户端 ID 可标识锁所有权
  - SET NX EX/PX 与 Lua 解锁用于提高原子性
### f358f7db-de57-4f73-bd5a-9799f2906cb4
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 读锁之间可共享
  - 读写、写写需要互斥
  - 分段锁可以降低锁粒度提高并发
### 18ef18ce-af28-4e21-a178-85e3c4fef41c
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 6e0f67c6-e44e-4597-823e-51ac8009e18e
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 单一热 Key 会形成单实例热点
  - 单纯扩容不能自动分散同一个 Key 的请求
  - 可通过业务预估、客户端、代理层和 Redis 工具发现热 Key
### ec679cc8-0bab-4a42-8c82-71b8ccc41ffe
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 35347050-3659-4e4a-b7e6-c938ac30ba95
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### ac6450de-8c72-4522-8dd9-b8bd93481f33
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7900c458-dc24-41a4-93c1-3fca0890926b
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Ping 正常结果包含 RTT、TTL 等字段
  - Unknown host 对应名称解析问题
  - Destination host unreachable 对应路由问题
  - Request timed out 可能与不可达或 ICMP 丢弃有关
### 44b091a9-9303-455f-b3d4-82b7a4ebea80
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redis 2.6 支持 Lua
  - 键过期精度支持毫秒
  - 从节点支持只读
  - redis-cli 支持 --eval
### 8d4e0f65-1c79-4b7c-9f1a-5544eff04adf
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Top Key 与离线全量分析的能力差异
  - bigkeys、memkeys、hotkeys 的用途差异
### f24fcfdb-a666-43e3-8908-51a4c427aeb3
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - STRLEN/LLEN/HLEN/SCARD/ZCARD/XLEN 可辅助分析不同类型 Key
  - MONITOR 会消耗资源，不建议长期使用
  - 业务层或 RDB 工具可定位热点/大 Key
### b450fa80-4dae-4451-80c6-5a5e5ed9cd63
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 可通过清理、压缩、拆分、转存处理
  - UNLINK 可异步删除大 Key
  - 热 Key 可通过副本或读写分离缓解，但存在一致性权衡
### da28c124-72d6-44b8-9232-0f30c8553b09
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 常由数据过大、成员过多或无效数据累积产生
  - 热 Key 可由突发访问量产生
  - 大 Key 会导致内存和分片资源不均
### 6e762405-d7b1-41c2-9672-063edea14b46
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 573a2228-bf05-4c42-ace5-54ae1276296f
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7aedf20c-a9d1-406d-b0ec-67cad013c604
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### ac37d2dc-d755-422a-aa63-baa5d302b2ce
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 可导致 rebalance/迁移失败和命令阻塞
  - 热 Key 可造成单分片 CPU 与带宽压力
### 9b76a641-e132-42a7-99cd-d8449e424457
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 使用线程标识和重入计数维护可重入锁
  - 获取失败时返回 TTL 进入等待/重试流程
  - 未显式指定 leaseTime 时文中给出默认 watchdog timeout
### f853d0c7-270a-46da-9eee-4e4d526ee648
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 获取失败后不会简单忙轮询
  - 使用 Pub/Sub 等待锁释放通知
  - 重试受到剩余 waitTime/TTL 限制
### fc9f1a15-0a08-45ed-b5bb-08dc214659b4
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 重试通过等待与唤醒避免持续占用 CPU
  - WatchDog 在业务未完成时周期性续约
  - 正常释放后停止续约，客户端异常后最终由 TTL 释放
### d7a15564-e469-464f-9e49-364964ca55c3
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### e39cbe02-1edf-43a1-a45f-f0faa1cda823
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 776f3a65-b66e-4b11-a096-66608f5454a4
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 83e8fb99-a4eb-4fe7-9f92-dff9776986ff
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 18a489f4-95a4-49a6-8ab6-2d0cc9150668
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A

## Human Review Results (v1)

### 881ee352-b7c6-4fa1-83c8-e1f802d1f129
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 5224115d-af43-447a-a96f-ae12459c0d9b
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### da6f4372-fa23-4d84-b2f3-98dd256253f0
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 解锁前必须校验锁持有者
  - Lua 可原子执行 compare-and-delete
  - 单 Redis 实例存在单点故障风险
### b39ddde1-9b8a-46d1-bcfc-23c468c1634f
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redlock 在多个独立 Redis 实例上申请锁
  - 使用随机唯一 value 标识锁所有者
  - 多数实例成功是获取锁的核心条件
### 7854e15d-b9bf-4382-917f-be979ebca791
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redis 主从异步复制可能导致故障切换后锁丢失
  - Redlock 要求至少 N/2+1 节点成功
  - 获取耗时必须小于锁有效期
### dfef6d0c-18a6-4651-9ad2-4cf3ed6aa4db
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redlock 节点可以彼此独立
  - 客户端应保持低延迟通信
  - 可使用多路复用并行发送 SET 请求
### 1cc83662-096d-4bb9-be35-bc9a7e8b844c
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - fencing token 要求资源服务器能够拒绝旧 token
  - 文中讨论使用随机锁 value 配合资源侧校验的方案
### 3e1c8633-3aba-45ed-b7a8-d8ac46803fae
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 文中区分分布式锁的互斥性与操作顺序性
  - ZooKeeper 可利用临时节点实现锁生命周期管理
### ca51e67f-0d3e-4452-902c-4ba2cea05965
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - ZooKeeper Session 通过心跳维持临时节点
  - 长进程暂停可能导致 Session 过期及锁丢失
  - 极端情况下分布式锁不能替代资源层一致性兜底
### 79ee9853-ab18-4e37-b727-a87c643ab063
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Ping 测 RTT 与目标连接稳定性
  - Traceroute 展示数据包经过的 Hop 路径
### 0727ac9b-a72e-485c-bb0f-e2afbab30777
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 04dc005d-210b-4537-ac99-54ebcb5048dc
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7cb50cf1-a34a-413b-a1eb-65b3f63a1e4a
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### b6568712-4048-4f21-a94a-dbd2dc476060
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### cd44e304-434b-4a35-8a69-ae001738bd11
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7ce2d1e9-1f93-431a-916e-32a4e5c2b084
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### c8bb7bc9-148d-484b-8640-2c75872ffc94
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 并发更新数据库和缓存可能产生旧缓存覆盖新值
  - 先删缓存再更新数据库存在读请求回填旧值窗口
### 62e6e94b-7c6d-425b-8506-20a2f78d8e1f
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### c4145c16-3a0d-438f-8b4f-4156e0e68206
- human_status: B
- usable_for_gold: true
- needs_neighbor: true
- fact_points:
  - 进程暂停和网络延迟可能持续很长时间
  - 这类暂停会破坏基于固定租约时间的安全假设
  - 必须结合相邻上下文使用
### da1668e8-f06e-4181-b382-1feedc6d4187
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 可使用 Hash 中线程标识和计数实现可重入
  - Lua 同时维护计数和 PEXPIRE
### a3d8f9ec-9e3c-4b75-9d23-c6f423bc9911
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 解锁应校验 requestId
  - Lua 将 GET 校验和 DEL 合并为原子操作
### c7e2bfee-252e-4f4d-a5ec-76c6c89793e3
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 723b50ac-8359-492e-9e5b-5295a356e5df
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 398521a8-0d16-4f5d-9575-165f972e6ad5
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - ZooKeeper 使用临时有序节点竞争锁
  - 未获得锁的客户端监听前驱节点
  - 前驱释放后重新判断是否获得锁
### fb18e10b-3846-43da-8584-c83729afdfc3
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 临时节点随客户端故障自动删除
  - Curator 提供可重入锁、不可重入锁、读写锁和 MultiLock
### c3c1c313-3662-4dc7-bff6-309e3b9e45d1
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 锁粒度过粗会降低并发
  - 可按资源 ID 或分段方式细化锁
  - 网络分区可能产生锁状态冲突
### ff651920-a885-4987-a701-a674ef6f6afd
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 锁先过期而业务未完成可能导致误删其他客户端的锁
  - 唯一客户端 ID 可标识锁所有权
  - SET NX EX/PX 与 Lua 解锁用于提高原子性
### f358f7db-de57-4f73-bd5a-9799f2906cb4
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 读锁之间可共享
  - 读写、写写需要互斥
  - 分段锁可以降低锁粒度提高并发
### 18ef18ce-af28-4e21-a178-85e3c4fef41c
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 6e0f67c6-e44e-4597-823e-51ac8009e18e
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 单一热 Key 会形成单实例热点
  - 单纯扩容不能自动分散同一个 Key 的请求
  - 可通过业务预估、客户端、代理层和 Redis 工具发现热 Key
### ec679cc8-0bab-4a42-8c82-71b8ccc41ffe
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 35347050-3659-4e4a-b7e6-c938ac30ba95
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### ac6450de-8c72-4522-8dd9-b8bd93481f33
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7900c458-dc24-41a4-93c1-3fca0890926b
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Ping 正常结果包含 RTT、TTL 等字段
  - Unknown host 对应名称解析问题
  - Destination host unreachable 对应路由问题
  - Request timed out 可能与不可达或 ICMP 丢弃有关
### 44b091a9-9303-455f-b3d4-82b7a4ebea80
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redis 2.6 支持 Lua
  - 键过期精度支持毫秒
  - 从节点支持只读
  - redis-cli 支持 --eval
### 8d4e0f65-1c79-4b7c-9f1a-5544eff04adf
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Top Key 与离线全量分析的能力差异
  - bigkeys、memkeys、hotkeys 的用途差异
### f24fcfdb-a666-43e3-8908-51a4c427aeb3
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - STRLEN/LLEN/HLEN/SCARD/ZCARD/XLEN 可辅助分析不同类型 Key
  - MONITOR 会消耗资源，不建议长期使用
  - 业务层或 RDB 工具可定位热点/大 Key
### b450fa80-4dae-4451-80c6-5a5e5ed9cd63
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 可通过清理、压缩、拆分、转存处理
  - UNLINK 可异步删除大 Key
  - 热 Key 可通过副本或读写分离缓解，但存在一致性权衡
### da28c124-72d6-44b8-9232-0f30c8553b09
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 常由数据过大、成员过多或无效数据累积产生
  - 热 Key 可由突发访问量产生
  - 大 Key 会导致内存和分片资源不均
### 6e762405-d7b1-41c2-9672-063edea14b46
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 573a2228-bf05-4c42-ace5-54ae1276296f
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7aedf20c-a9d1-406d-b0ec-67cad013c604
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### ac37d2dc-d755-422a-aa63-baa5d302b2ce
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 可导致 rebalance/迁移失败和命令阻塞
  - 热 Key 可造成单分片 CPU 与带宽压力
### 9b76a641-e132-42a7-99cd-d8449e424457
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 使用线程标识和重入计数维护可重入锁
  - 获取失败时返回 TTL 进入等待/重试流程
  - 未显式指定 leaseTime 时文中给出默认 watchdog timeout
### f853d0c7-270a-46da-9eee-4e4d526ee648
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 获取失败后不会简单忙轮询
  - 使用 Pub/Sub 等待锁释放通知
  - 重试受到剩余 waitTime/TTL 限制
### fc9f1a15-0a08-45ed-b5bb-08dc214659b4
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 重试通过等待与唤醒避免持续占用 CPU
  - WatchDog 在业务未完成时周期性续约
  - 正常释放后停止续约，客户端异常后最终由 TTL 释放
### d7a15564-e469-464f-9e49-364964ca55c3
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### e39cbe02-1edf-43a1-a45f-f0faa1cda823
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 776f3a65-b66e-4b11-a096-66608f5454a4
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 83e8fb99-a4eb-4fe7-9f92-dff9776986ff
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 18a489f4-95a4-49a6-8ab6-2d0cc9150668
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A

## Human Review Results (v1)

### 881ee352-b7c6-4fa1-83c8-e1f802d1f129
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 5224115d-af43-447a-a96f-ae12459c0d9b
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### da6f4372-fa23-4d84-b2f3-98dd256253f0
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 解锁前必须校验锁持有者
  - Lua 可原子执行 compare-and-delete
  - 单 Redis 实例存在单点故障风险
### b39ddde1-9b8a-46d1-bcfc-23c468c1634f
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redlock 在多个独立 Redis 实例上申请锁
  - 使用随机唯一 value 标识锁所有者
  - 多数实例成功是获取锁的核心条件
### 7854e15d-b9bf-4382-917f-be979ebca791
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redis 主从异步复制可能导致故障切换后锁丢失
  - Redlock 要求至少 N/2+1 节点成功
  - 获取耗时必须小于锁有效期
### dfef6d0c-18a6-4651-9ad2-4cf3ed6aa4db
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redlock 节点可以彼此独立
  - 客户端应保持低延迟通信
  - 可使用多路复用并行发送 SET 请求
### 1cc83662-096d-4bb9-be35-bc9a7e8b844c
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - fencing token 要求资源服务器能够拒绝旧 token
  - 文中讨论使用随机锁 value 配合资源侧校验的方案
### 3e1c8633-3aba-45ed-b7a8-d8ac46803fae
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 文中区分分布式锁的互斥性与操作顺序性
  - ZooKeeper 可利用临时节点实现锁生命周期管理
### ca51e67f-0d3e-4452-902c-4ba2cea05965
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - ZooKeeper Session 通过心跳维持临时节点
  - 长进程暂停可能导致 Session 过期及锁丢失
  - 极端情况下分布式锁不能替代资源层一致性兜底
### 79ee9853-ab18-4e37-b727-a87c643ab063
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Ping 测 RTT 与目标连接稳定性
  - Traceroute 展示数据包经过的 Hop 路径
### 0727ac9b-a72e-485c-bb0f-e2afbab30777
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 04dc005d-210b-4537-ac99-54ebcb5048dc
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7cb50cf1-a34a-413b-a1eb-65b3f63a1e4a
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### b6568712-4048-4f21-a94a-dbd2dc476060
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### cd44e304-434b-4a35-8a69-ae001738bd11
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7ce2d1e9-1f93-431a-916e-32a4e5c2b084
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### c8bb7bc9-148d-484b-8640-2c75872ffc94
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 并发更新数据库和缓存可能产生旧缓存覆盖新值
  - 先删缓存再更新数据库存在读请求回填旧值窗口
### 62e6e94b-7c6d-425b-8506-20a2f78d8e1f
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### c4145c16-3a0d-438f-8b4f-4156e0e68206
- human_status: B
- usable_for_gold: true
- needs_neighbor: true
- fact_points:
  - 进程暂停和网络延迟可能持续很长时间
  - 这类暂停会破坏基于固定租约时间的安全假设
  - 必须结合相邻上下文使用
### da1668e8-f06e-4181-b382-1feedc6d4187
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 可使用 Hash 中线程标识和计数实现可重入
  - Lua 同时维护计数和 PEXPIRE
### a3d8f9ec-9e3c-4b75-9d23-c6f423bc9911
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 解锁应校验 requestId
  - Lua 将 GET 校验和 DEL 合并为原子操作
### c7e2bfee-252e-4f4d-a5ec-76c6c89793e3
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 723b50ac-8359-492e-9e5b-5295a356e5df
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 398521a8-0d16-4f5d-9575-165f972e6ad5
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - ZooKeeper 使用临时有序节点竞争锁
  - 未获得锁的客户端监听前驱节点
  - 前驱释放后重新判断是否获得锁
### fb18e10b-3846-43da-8584-c83729afdfc3
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 临时节点随客户端故障自动删除
  - Curator 提供可重入锁、不可重入锁、读写锁和 MultiLock
### c3c1c313-3662-4dc7-bff6-309e3b9e45d1
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 锁粒度过粗会降低并发
  - 可按资源 ID 或分段方式细化锁
  - 网络分区可能产生锁状态冲突
### ff651920-a885-4987-a701-a674ef6f6afd
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 锁先过期而业务未完成可能导致误删其他客户端的锁
  - 唯一客户端 ID 可标识锁所有权
  - SET NX EX/PX 与 Lua 解锁用于提高原子性
### f358f7db-de57-4f73-bd5a-9799f2906cb4
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 读锁之间可共享
  - 读写、写写需要互斥
  - 分段锁可以降低锁粒度提高并发
### 18ef18ce-af28-4e21-a178-85e3c4fef41c
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 6e0f67c6-e44e-4597-823e-51ac8009e18e
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 单一热 Key 会形成单实例热点
  - 单纯扩容不能自动分散同一个 Key 的请求
  - 可通过业务预估、客户端、代理层和 Redis 工具发现热 Key
### ec679cc8-0bab-4a42-8c82-71b8ccc41ffe
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 35347050-3659-4e4a-b7e6-c938ac30ba95
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### ac6450de-8c72-4522-8dd9-b8bd93481f33
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7900c458-dc24-41a4-93c1-3fca0890926b
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Ping 正常结果包含 RTT、TTL 等字段
  - Unknown host 对应名称解析问题
  - Destination host unreachable 对应路由问题
  - Request timed out 可能与不可达或 ICMP 丢弃有关
### 44b091a9-9303-455f-b3d4-82b7a4ebea80
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redis 2.6 支持 Lua
  - 键过期精度支持毫秒
  - 从节点支持只读
  - redis-cli 支持 --eval
### 8d4e0f65-1c79-4b7c-9f1a-5544eff04adf
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Top Key 与离线全量分析的能力差异
  - bigkeys、memkeys、hotkeys 的用途差异
### f24fcfdb-a666-43e3-8908-51a4c427aeb3
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - STRLEN/LLEN/HLEN/SCARD/ZCARD/XLEN 可辅助分析不同类型 Key
  - MONITOR 会消耗资源，不建议长期使用
  - 业务层或 RDB 工具可定位热点/大 Key
### b450fa80-4dae-4451-80c6-5a5e5ed9cd63
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 可通过清理、压缩、拆分、转存处理
  - UNLINK 可异步删除大 Key
  - 热 Key 可通过副本或读写分离缓解，但存在一致性权衡
### da28c124-72d6-44b8-9232-0f30c8553b09
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 常由数据过大、成员过多或无效数据累积产生
  - 热 Key 可由突发访问量产生
  - 大 Key 会导致内存和分片资源不均
### 6e762405-d7b1-41c2-9672-063edea14b46
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 573a2228-bf05-4c42-ace5-54ae1276296f
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7aedf20c-a9d1-406d-b0ec-67cad013c604
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### ac37d2dc-d755-422a-aa63-baa5d302b2ce
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 可导致 rebalance/迁移失败和命令阻塞
  - 热 Key 可造成单分片 CPU 与带宽压力
### 9b76a641-e132-42a7-99cd-d8449e424457
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 使用线程标识和重入计数维护可重入锁
  - 获取失败时返回 TTL 进入等待/重试流程
  - 未显式指定 leaseTime 时文中给出默认 watchdog timeout
### f853d0c7-270a-46da-9eee-4e4d526ee648
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 获取失败后不会简单忙轮询
  - 使用 Pub/Sub 等待锁释放通知
  - 重试受到剩余 waitTime/TTL 限制
### fc9f1a15-0a08-45ed-b5bb-08dc214659b4
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 重试通过等待与唤醒避免持续占用 CPU
  - WatchDog 在业务未完成时周期性续约
  - 正常释放后停止续约，客户端异常后最终由 TTL 释放
### d7a15564-e469-464f-9e49-364964ca55c3
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### e39cbe02-1edf-43a1-a45f-f0faa1cda823
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 776f3a65-b66e-4b11-a096-66608f5454a4
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 83e8fb99-a4eb-4fe7-9f92-dff9776986ff
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 18a489f4-95a4-49a6-8ab6-2d0cc9150668
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A

## Human Review Results (v1)

### 881ee352-b7c6-4fa1-83c8-e1f802d1f129
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 5224115d-af43-447a-a96f-ae12459c0d9b
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### da6f4372-fa23-4d84-b2f3-98dd256253f0
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 解锁前必须校验锁持有者
  - Lua 可原子执行 compare-and-delete
  - 单 Redis 实例存在单点故障风险
### b39ddde1-9b8a-46d1-bcfc-23c468c1634f
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redlock 在多个独立 Redis 实例上申请锁
  - 使用随机唯一 value 标识锁所有者
  - 多数实例成功是获取锁的核心条件
### 7854e15d-b9bf-4382-917f-be979ebca791
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redis 主从异步复制可能导致故障切换后锁丢失
  - Redlock 要求至少 N/2+1 节点成功
  - 获取耗时必须小于锁有效期
### dfef6d0c-18a6-4651-9ad2-4cf3ed6aa4db
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redlock 节点可以彼此独立
  - 客户端应保持低延迟通信
  - 可使用多路复用并行发送 SET 请求
### 1cc83662-096d-4bb9-be35-bc9a7e8b844c
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - fencing token 要求资源服务器能够拒绝旧 token
  - 文中讨论使用随机锁 value 配合资源侧校验的方案
### 3e1c8633-3aba-45ed-b7a8-d8ac46803fae
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 文中区分分布式锁的互斥性与操作顺序性
  - ZooKeeper 可利用临时节点实现锁生命周期管理
### ca51e67f-0d3e-4452-902c-4ba2cea05965
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - ZooKeeper Session 通过心跳维持临时节点
  - 长进程暂停可能导致 Session 过期及锁丢失
  - 极端情况下分布式锁不能替代资源层一致性兜底
### 79ee9853-ab18-4e37-b727-a87c643ab063
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Ping 测 RTT 与目标连接稳定性
  - Traceroute 展示数据包经过的 Hop 路径
### 0727ac9b-a72e-485c-bb0f-e2afbab30777
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 04dc005d-210b-4537-ac99-54ebcb5048dc
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7cb50cf1-a34a-413b-a1eb-65b3f63a1e4a
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### b6568712-4048-4f21-a94a-dbd2dc476060
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### cd44e304-434b-4a35-8a69-ae001738bd11
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7ce2d1e9-1f93-431a-916e-32a4e5c2b084
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### c8bb7bc9-148d-484b-8640-2c75872ffc94
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 并发更新数据库和缓存可能产生旧缓存覆盖新值
  - 先删缓存再更新数据库存在读请求回填旧值窗口
### 62e6e94b-7c6d-425b-8506-20a2f78d8e1f
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### c4145c16-3a0d-438f-8b4f-4156e0e68206
- human_status: B
- usable_for_gold: true
- needs_neighbor: true
- fact_points:
  - 进程暂停和网络延迟可能持续很长时间
  - 这类暂停会破坏基于固定租约时间的安全假设
  - 必须结合相邻上下文使用
### da1668e8-f06e-4181-b382-1feedc6d4187
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 可使用 Hash 中线程标识和计数实现可重入
  - Lua 同时维护计数和 PEXPIRE
### a3d8f9ec-9e3c-4b75-9d23-c6f423bc9911
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 解锁应校验 requestId
  - Lua 将 GET 校验和 DEL 合并为原子操作
### c7e2bfee-252e-4f4d-a5ec-76c6c89793e3
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 723b50ac-8359-492e-9e5b-5295a356e5df
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 398521a8-0d16-4f5d-9575-165f972e6ad5
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - ZooKeeper 使用临时有序节点竞争锁
  - 未获得锁的客户端监听前驱节点
  - 前驱释放后重新判断是否获得锁
### fb18e10b-3846-43da-8584-c83729afdfc3
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 临时节点随客户端故障自动删除
  - Curator 提供可重入锁、不可重入锁、读写锁和 MultiLock
### c3c1c313-3662-4dc7-bff6-309e3b9e45d1
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 锁粒度过粗会降低并发
  - 可按资源 ID 或分段方式细化锁
  - 网络分区可能产生锁状态冲突
### ff651920-a885-4987-a701-a674ef6f6afd
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 锁先过期而业务未完成可能导致误删其他客户端的锁
  - 唯一客户端 ID 可标识锁所有权
  - SET NX EX/PX 与 Lua 解锁用于提高原子性
### f358f7db-de57-4f73-bd5a-9799f2906cb4
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 读锁之间可共享
  - 读写、写写需要互斥
  - 分段锁可以降低锁粒度提高并发
### 18ef18ce-af28-4e21-a178-85e3c4fef41c
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 6e0f67c6-e44e-4597-823e-51ac8009e18e
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 单一热 Key 会形成单实例热点
  - 单纯扩容不能自动分散同一个 Key 的请求
  - 可通过业务预估、客户端、代理层和 Redis 工具发现热 Key
### ec679cc8-0bab-4a42-8c82-71b8ccc41ffe
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 35347050-3659-4e4a-b7e6-c938ac30ba95
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### ac6450de-8c72-4522-8dd9-b8bd93481f33
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7900c458-dc24-41a4-93c1-3fca0890926b
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Ping 正常结果包含 RTT、TTL 等字段
  - Unknown host 对应名称解析问题
  - Destination host unreachable 对应路由问题
  - Request timed out 可能与不可达或 ICMP 丢弃有关
### 44b091a9-9303-455f-b3d4-82b7a4ebea80
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redis 2.6 支持 Lua
  - 键过期精度支持毫秒
  - 从节点支持只读
  - redis-cli 支持 --eval
### 8d4e0f65-1c79-4b7c-9f1a-5544eff04adf
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Top Key 与离线全量分析的能力差异
  - bigkeys、memkeys、hotkeys 的用途差异
### f24fcfdb-a666-43e3-8908-51a4c427aeb3
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - STRLEN/LLEN/HLEN/SCARD/ZCARD/XLEN 可辅助分析不同类型 Key
  - MONITOR 会消耗资源，不建议长期使用
  - 业务层或 RDB 工具可定位热点/大 Key
### b450fa80-4dae-4451-80c6-5a5e5ed9cd63
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 可通过清理、压缩、拆分、转存处理
  - UNLINK 可异步删除大 Key
  - 热 Key 可通过副本或读写分离缓解，但存在一致性权衡
### da28c124-72d6-44b8-9232-0f30c8553b09
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 常由数据过大、成员过多或无效数据累积产生
  - 热 Key 可由突发访问量产生
  - 大 Key 会导致内存和分片资源不均
### 6e762405-d7b1-41c2-9672-063edea14b46
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 573a2228-bf05-4c42-ace5-54ae1276296f
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7aedf20c-a9d1-406d-b0ec-67cad013c604
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### ac37d2dc-d755-422a-aa63-baa5d302b2ce
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 可导致 rebalance/迁移失败和命令阻塞
  - 热 Key 可造成单分片 CPU 与带宽压力
### 9b76a641-e132-42a7-99cd-d8449e424457
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 使用线程标识和重入计数维护可重入锁
  - 获取失败时返回 TTL 进入等待/重试流程
  - 未显式指定 leaseTime 时文中给出默认 watchdog timeout
### f853d0c7-270a-46da-9eee-4e4d526ee648
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 获取失败后不会简单忙轮询
  - 使用 Pub/Sub 等待锁释放通知
  - 重试受到剩余 waitTime/TTL 限制
### fc9f1a15-0a08-45ed-b5bb-08dc214659b4
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 重试通过等待与唤醒避免持续占用 CPU
  - WatchDog 在业务未完成时周期性续约
  - 正常释放后停止续约，客户端异常后最终由 TTL 释放
### d7a15564-e469-464f-9e49-364964ca55c3
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### e39cbe02-1edf-43a1-a45f-f0faa1cda823
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 776f3a65-b66e-4b11-a096-66608f5454a4
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 83e8fb99-a4eb-4fe7-9f92-dff9776986ff
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 18a489f4-95a4-49a6-8ab6-2d0cc9150668
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A

## Human Review Results (v1)

### 881ee352-b7c6-4fa1-83c8-e1f802d1f129
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 5224115d-af43-447a-a96f-ae12459c0d9b
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### da6f4372-fa23-4d84-b2f3-98dd256253f0
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 解锁前必须校验锁持有者
  - Lua 可原子执行 compare-and-delete
  - 单 Redis 实例存在单点故障风险
### b39ddde1-9b8a-46d1-bcfc-23c468c1634f
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redlock 在多个独立 Redis 实例上申请锁
  - 使用随机唯一 value 标识锁所有者
  - 多数实例成功是获取锁的核心条件
### 7854e15d-b9bf-4382-917f-be979ebca791
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redis 主从异步复制可能导致故障切换后锁丢失
  - Redlock 要求至少 N/2+1 节点成功
  - 获取耗时必须小于锁有效期
### dfef6d0c-18a6-4651-9ad2-4cf3ed6aa4db
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redlock 节点可以彼此独立
  - 客户端应保持低延迟通信
  - 可使用多路复用并行发送 SET 请求
### 1cc83662-096d-4bb9-be35-bc9a7e8b844c
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - fencing token 要求资源服务器能够拒绝旧 token
  - 文中讨论使用随机锁 value 配合资源侧校验的方案
### 3e1c8633-3aba-45ed-b7a8-d8ac46803fae
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 文中区分分布式锁的互斥性与操作顺序性
  - ZooKeeper 可利用临时节点实现锁生命周期管理
### ca51e67f-0d3e-4452-902c-4ba2cea05965
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - ZooKeeper Session 通过心跳维持临时节点
  - 长进程暂停可能导致 Session 过期及锁丢失
  - 极端情况下分布式锁不能替代资源层一致性兜底
### 79ee9853-ab18-4e37-b727-a87c643ab063
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Ping 测 RTT 与目标连接稳定性
  - Traceroute 展示数据包经过的 Hop 路径
### 0727ac9b-a72e-485c-bb0f-e2afbab30777
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 04dc005d-210b-4537-ac99-54ebcb5048dc
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7cb50cf1-a34a-413b-a1eb-65b3f63a1e4a
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### b6568712-4048-4f21-a94a-dbd2dc476060
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### cd44e304-434b-4a35-8a69-ae001738bd11
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7ce2d1e9-1f93-431a-916e-32a4e5c2b084
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### c8bb7bc9-148d-484b-8640-2c75872ffc94
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 并发更新数据库和缓存可能产生旧缓存覆盖新值
  - 先删缓存再更新数据库存在读请求回填旧值窗口
### 62e6e94b-7c6d-425b-8506-20a2f78d8e1f
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### c4145c16-3a0d-438f-8b4f-4156e0e68206
- human_status: B
- usable_for_gold: true
- needs_neighbor: true
- fact_points:
  - 进程暂停和网络延迟可能持续很长时间
  - 这类暂停会破坏基于固定租约时间的安全假设
  - 必须结合相邻上下文使用
### da1668e8-f06e-4181-b382-1feedc6d4187
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 可使用 Hash 中线程标识和计数实现可重入
  - Lua 同时维护计数和 PEXPIRE
### a3d8f9ec-9e3c-4b75-9d23-c6f423bc9911
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 解锁应校验 requestId
  - Lua 将 GET 校验和 DEL 合并为原子操作
### c7e2bfee-252e-4f4d-a5ec-76c6c89793e3
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 723b50ac-8359-492e-9e5b-5295a356e5df
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 398521a8-0d16-4f5d-9575-165f972e6ad5
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - ZooKeeper 使用临时有序节点竞争锁
  - 未获得锁的客户端监听前驱节点
  - 前驱释放后重新判断是否获得锁
### fb18e10b-3846-43da-8584-c83729afdfc3
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 临时节点随客户端故障自动删除
  - Curator 提供可重入锁、不可重入锁、读写锁和 MultiLock
### c3c1c313-3662-4dc7-bff6-309e3b9e45d1
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 锁粒度过粗会降低并发
  - 可按资源 ID 或分段方式细化锁
  - 网络分区可能产生锁状态冲突
### ff651920-a885-4987-a701-a674ef6f6afd
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 锁先过期而业务未完成可能导致误删其他客户端的锁
  - 唯一客户端 ID 可标识锁所有权
  - SET NX EX/PX 与 Lua 解锁用于提高原子性
### f358f7db-de57-4f73-bd5a-9799f2906cb4
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 读锁之间可共享
  - 读写、写写需要互斥
  - 分段锁可以降低锁粒度提高并发
### 18ef18ce-af28-4e21-a178-85e3c4fef41c
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 6e0f67c6-e44e-4597-823e-51ac8009e18e
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 单一热 Key 会形成单实例热点
  - 单纯扩容不能自动分散同一个 Key 的请求
  - 可通过业务预估、客户端、代理层和 Redis 工具发现热 Key
### ec679cc8-0bab-4a42-8c82-71b8ccc41ffe
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 35347050-3659-4e4a-b7e6-c938ac30ba95
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### ac6450de-8c72-4522-8dd9-b8bd93481f33
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7900c458-dc24-41a4-93c1-3fca0890926b
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Ping 正常结果包含 RTT、TTL 等字段
  - Unknown host 对应名称解析问题
  - Destination host unreachable 对应路由问题
  - Request timed out 可能与不可达或 ICMP 丢弃有关
### 44b091a9-9303-455f-b3d4-82b7a4ebea80
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redis 2.6 支持 Lua
  - 键过期精度支持毫秒
  - 从节点支持只读
  - redis-cli 支持 --eval
### 8d4e0f65-1c79-4b7c-9f1a-5544eff04adf
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Top Key 与离线全量分析的能力差异
  - bigkeys、memkeys、hotkeys 的用途差异
### f24fcfdb-a666-43e3-8908-51a4c427aeb3
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - STRLEN/LLEN/HLEN/SCARD/ZCARD/XLEN 可辅助分析不同类型 Key
  - MONITOR 会消耗资源，不建议长期使用
  - 业务层或 RDB 工具可定位热点/大 Key
### b450fa80-4dae-4451-80c6-5a5e5ed9cd63
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 可通过清理、压缩、拆分、转存处理
  - UNLINK 可异步删除大 Key
  - 热 Key 可通过副本或读写分离缓解，但存在一致性权衡
### da28c124-72d6-44b8-9232-0f30c8553b09
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 常由数据过大、成员过多或无效数据累积产生
  - 热 Key 可由突发访问量产生
  - 大 Key 会导致内存和分片资源不均
### 6e762405-d7b1-41c2-9672-063edea14b46
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 573a2228-bf05-4c42-ace5-54ae1276296f
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7aedf20c-a9d1-406d-b0ec-67cad013c604
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### ac37d2dc-d755-422a-aa63-baa5d302b2ce
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 可导致 rebalance/迁移失败和命令阻塞
  - 热 Key 可造成单分片 CPU 与带宽压力
### 9b76a641-e132-42a7-99cd-d8449e424457
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 使用线程标识和重入计数维护可重入锁
  - 获取失败时返回 TTL 进入等待/重试流程
  - 未显式指定 leaseTime 时文中给出默认 watchdog timeout
### f853d0c7-270a-46da-9eee-4e4d526ee648
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 获取失败后不会简单忙轮询
  - 使用 Pub/Sub 等待锁释放通知
  - 重试受到剩余 waitTime/TTL 限制
### fc9f1a15-0a08-45ed-b5bb-08dc214659b4
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 重试通过等待与唤醒避免持续占用 CPU
  - WatchDog 在业务未完成时周期性续约
  - 正常释放后停止续约，客户端异常后最终由 TTL 释放
### d7a15564-e469-464f-9e49-364964ca55c3
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### e39cbe02-1edf-43a1-a45f-f0faa1cda823
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 776f3a65-b66e-4b11-a096-66608f5454a4
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 83e8fb99-a4eb-4fe7-9f92-dff9776986ff
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 18a489f4-95a4-49a6-8ab6-2d0cc9150668
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A

## Human Review Results (v1)

### 881ee352-b7c6-4fa1-83c8-e1f802d1f129
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 5224115d-af43-447a-a96f-ae12459c0d9b
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### da6f4372-fa23-4d84-b2f3-98dd256253f0
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 解锁前必须校验锁持有者
  - Lua 可原子执行 compare-and-delete
  - 单 Redis 实例存在单点故障风险
### b39ddde1-9b8a-46d1-bcfc-23c468c1634f
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redlock 在多个独立 Redis 实例上申请锁
  - 使用随机唯一 value 标识锁所有者
  - 多数实例成功是获取锁的核心条件
### 7854e15d-b9bf-4382-917f-be979ebca791
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redis 主从异步复制可能导致故障切换后锁丢失
  - Redlock 要求至少 N/2+1 节点成功
  - 获取耗时必须小于锁有效期
### dfef6d0c-18a6-4651-9ad2-4cf3ed6aa4db
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redlock 节点可以彼此独立
  - 客户端应保持低延迟通信
  - 可使用多路复用并行发送 SET 请求
### 1cc83662-096d-4bb9-be35-bc9a7e8b844c
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - fencing token 要求资源服务器能够拒绝旧 token
  - 文中讨论使用随机锁 value 配合资源侧校验的方案
### 3e1c8633-3aba-45ed-b7a8-d8ac46803fae
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 文中区分分布式锁的互斥性与操作顺序性
  - ZooKeeper 可利用临时节点实现锁生命周期管理
### ca51e67f-0d3e-4452-902c-4ba2cea05965
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - ZooKeeper Session 通过心跳维持临时节点
  - 长进程暂停可能导致 Session 过期及锁丢失
  - 极端情况下分布式锁不能替代资源层一致性兜底
### 79ee9853-ab18-4e37-b727-a87c643ab063
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Ping 测 RTT 与目标连接稳定性
  - Traceroute 展示数据包经过的 Hop 路径
### 0727ac9b-a72e-485c-bb0f-e2afbab30777
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 04dc005d-210b-4537-ac99-54ebcb5048dc
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7cb50cf1-a34a-413b-a1eb-65b3f63a1e4a
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### b6568712-4048-4f21-a94a-dbd2dc476060
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### cd44e304-434b-4a35-8a69-ae001738bd11
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7ce2d1e9-1f93-431a-916e-32a4e5c2b084
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### c8bb7bc9-148d-484b-8640-2c75872ffc94
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 并发更新数据库和缓存可能产生旧缓存覆盖新值
  - 先删缓存再更新数据库存在读请求回填旧值窗口
### 62e6e94b-7c6d-425b-8506-20a2f78d8e1f
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### c4145c16-3a0d-438f-8b4f-4156e0e68206
- human_status: B
- usable_for_gold: true
- needs_neighbor: true
- fact_points:
  - 进程暂停和网络延迟可能持续很长时间
  - 这类暂停会破坏基于固定租约时间的安全假设
  - 必须结合相邻上下文使用
### da1668e8-f06e-4181-b382-1feedc6d4187
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 可使用 Hash 中线程标识和计数实现可重入
  - Lua 同时维护计数和 PEXPIRE
### a3d8f9ec-9e3c-4b75-9d23-c6f423bc9911
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 解锁应校验 requestId
  - Lua 将 GET 校验和 DEL 合并为原子操作
### c7e2bfee-252e-4f4d-a5ec-76c6c89793e3
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 723b50ac-8359-492e-9e5b-5295a356e5df
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 398521a8-0d16-4f5d-9575-165f972e6ad5
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - ZooKeeper 使用临时有序节点竞争锁
  - 未获得锁的客户端监听前驱节点
  - 前驱释放后重新判断是否获得锁
### fb18e10b-3846-43da-8584-c83729afdfc3
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 临时节点随客户端故障自动删除
  - Curator 提供可重入锁、不可重入锁、读写锁和 MultiLock
### c3c1c313-3662-4dc7-bff6-309e3b9e45d1
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 锁粒度过粗会降低并发
  - 可按资源 ID 或分段方式细化锁
  - 网络分区可能产生锁状态冲突
### ff651920-a885-4987-a701-a674ef6f6afd
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 锁先过期而业务未完成可能导致误删其他客户端的锁
  - 唯一客户端 ID 可标识锁所有权
  - SET NX EX/PX 与 Lua 解锁用于提高原子性
### f358f7db-de57-4f73-bd5a-9799f2906cb4
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 读锁之间可共享
  - 读写、写写需要互斥
  - 分段锁可以降低锁粒度提高并发
### 18ef18ce-af28-4e21-a178-85e3c4fef41c
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 6e0f67c6-e44e-4597-823e-51ac8009e18e
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 单一热 Key 会形成单实例热点
  - 单纯扩容不能自动分散同一个 Key 的请求
  - 可通过业务预估、客户端、代理层和 Redis 工具发现热 Key
### ec679cc8-0bab-4a42-8c82-71b8ccc41ffe
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 35347050-3659-4e4a-b7e6-c938ac30ba95
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### ac6450de-8c72-4522-8dd9-b8bd93481f33
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7900c458-dc24-41a4-93c1-3fca0890926b
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Ping 正常结果包含 RTT、TTL 等字段
  - Unknown host 对应名称解析问题
  - Destination host unreachable 对应路由问题
  - Request timed out 可能与不可达或 ICMP 丢弃有关
### 44b091a9-9303-455f-b3d4-82b7a4ebea80
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redis 2.6 支持 Lua
  - 键过期精度支持毫秒
  - 从节点支持只读
  - redis-cli 支持 --eval
### 8d4e0f65-1c79-4b7c-9f1a-5544eff04adf
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Top Key 与离线全量分析的能力差异
  - bigkeys、memkeys、hotkeys 的用途差异
### f24fcfdb-a666-43e3-8908-51a4c427aeb3
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - STRLEN/LLEN/HLEN/SCARD/ZCARD/XLEN 可辅助分析不同类型 Key
  - MONITOR 会消耗资源，不建议长期使用
  - 业务层或 RDB 工具可定位热点/大 Key
### b450fa80-4dae-4451-80c6-5a5e5ed9cd63
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 可通过清理、压缩、拆分、转存处理
  - UNLINK 可异步删除大 Key
  - 热 Key 可通过副本或读写分离缓解，但存在一致性权衡
### da28c124-72d6-44b8-9232-0f30c8553b09
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 常由数据过大、成员过多或无效数据累积产生
  - 热 Key 可由突发访问量产生
  - 大 Key 会导致内存和分片资源不均
### 6e762405-d7b1-41c2-9672-063edea14b46
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 573a2228-bf05-4c42-ace5-54ae1276296f
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7aedf20c-a9d1-406d-b0ec-67cad013c604
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### ac37d2dc-d755-422a-aa63-baa5d302b2ce
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 可导致 rebalance/迁移失败和命令阻塞
  - 热 Key 可造成单分片 CPU 与带宽压力
### 9b76a641-e132-42a7-99cd-d8449e424457
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 使用线程标识和重入计数维护可重入锁
  - 获取失败时返回 TTL 进入等待/重试流程
  - 未显式指定 leaseTime 时文中给出默认 watchdog timeout
### f853d0c7-270a-46da-9eee-4e4d526ee648
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 获取失败后不会简单忙轮询
  - 使用 Pub/Sub 等待锁释放通知
  - 重试受到剩余 waitTime/TTL 限制
### fc9f1a15-0a08-45ed-b5bb-08dc214659b4
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 重试通过等待与唤醒避免持续占用 CPU
  - WatchDog 在业务未完成时周期性续约
  - 正常释放后停止续约，客户端异常后最终由 TTL 释放
### d7a15564-e469-464f-9e49-364964ca55c3
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### e39cbe02-1edf-43a1-a45f-f0faa1cda823
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 776f3a65-b66e-4b11-a096-66608f5454a4
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 83e8fb99-a4eb-4fe7-9f92-dff9776986ff
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 18a489f4-95a4-49a6-8ab6-2d0cc9150668
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A

## Human Review Results (v1)

### 881ee352-b7c6-4fa1-83c8-e1f802d1f129
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 5224115d-af43-447a-a96f-ae12459c0d9b
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### da6f4372-fa23-4d84-b2f3-98dd256253f0
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 解锁前必须校验锁持有者
  - Lua 可原子执行 compare-and-delete
  - 单 Redis 实例存在单点故障风险
### b39ddde1-9b8a-46d1-bcfc-23c468c1634f
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redlock 在多个独立 Redis 实例上申请锁
  - 使用随机唯一 value 标识锁所有者
  - 多数实例成功是获取锁的核心条件
### 7854e15d-b9bf-4382-917f-be979ebca791
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redis 主从异步复制可能导致故障切换后锁丢失
  - Redlock 要求至少 N/2+1 节点成功
  - 获取耗时必须小于锁有效期
### dfef6d0c-18a6-4651-9ad2-4cf3ed6aa4db
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redlock 节点可以彼此独立
  - 客户端应保持低延迟通信
  - 可使用多路复用并行发送 SET 请求
### 1cc83662-096d-4bb9-be35-bc9a7e8b844c
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - fencing token 要求资源服务器能够拒绝旧 token
  - 文中讨论使用随机锁 value 配合资源侧校验的方案
### 3e1c8633-3aba-45ed-b7a8-d8ac46803fae
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 文中区分分布式锁的互斥性与操作顺序性
  - ZooKeeper 可利用临时节点实现锁生命周期管理
### ca51e67f-0d3e-4452-902c-4ba2cea05965
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - ZooKeeper Session 通过心跳维持临时节点
  - 长进程暂停可能导致 Session 过期及锁丢失
  - 极端情况下分布式锁不能替代资源层一致性兜底
### 79ee9853-ab18-4e37-b727-a87c643ab063
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Ping 测 RTT 与目标连接稳定性
  - Traceroute 展示数据包经过的 Hop 路径
### 0727ac9b-a72e-485c-bb0f-e2afbab30777
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 04dc005d-210b-4537-ac99-54ebcb5048dc
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7cb50cf1-a34a-413b-a1eb-65b3f63a1e4a
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### b6568712-4048-4f21-a94a-dbd2dc476060
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### cd44e304-434b-4a35-8a69-ae001738bd11
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7ce2d1e9-1f93-431a-916e-32a4e5c2b084
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### c8bb7bc9-148d-484b-8640-2c75872ffc94
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 并发更新数据库和缓存可能产生旧缓存覆盖新值
  - 先删缓存再更新数据库存在读请求回填旧值窗口
### 62e6e94b-7c6d-425b-8506-20a2f78d8e1f
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### c4145c16-3a0d-438f-8b4f-4156e0e68206
- human_status: B
- usable_for_gold: true
- needs_neighbor: true
- fact_points:
  - 进程暂停和网络延迟可能持续很长时间
  - 这类暂停会破坏基于固定租约时间的安全假设
  - 必须结合相邻上下文使用
### da1668e8-f06e-4181-b382-1feedc6d4187
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 可使用 Hash 中线程标识和计数实现可重入
  - Lua 同时维护计数和 PEXPIRE
### a3d8f9ec-9e3c-4b75-9d23-c6f423bc9911
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 解锁应校验 requestId
  - Lua 将 GET 校验和 DEL 合并为原子操作
### c7e2bfee-252e-4f4d-a5ec-76c6c89793e3
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 723b50ac-8359-492e-9e5b-5295a356e5df
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 398521a8-0d16-4f5d-9575-165f972e6ad5
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - ZooKeeper 使用临时有序节点竞争锁
  - 未获得锁的客户端监听前驱节点
  - 前驱释放后重新判断是否获得锁
### fb18e10b-3846-43da-8584-c83729afdfc3
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 临时节点随客户端故障自动删除
  - Curator 提供可重入锁、不可重入锁、读写锁和 MultiLock
### c3c1c313-3662-4dc7-bff6-309e3b9e45d1
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 锁粒度过粗会降低并发
  - 可按资源 ID 或分段方式细化锁
  - 网络分区可能产生锁状态冲突
### ff651920-a885-4987-a701-a674ef6f6afd
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 锁先过期而业务未完成可能导致误删其他客户端的锁
  - 唯一客户端 ID 可标识锁所有权
  - SET NX EX/PX 与 Lua 解锁用于提高原子性
### f358f7db-de57-4f73-bd5a-9799f2906cb4
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 读锁之间可共享
  - 读写、写写需要互斥
  - 分段锁可以降低锁粒度提高并发
### 18ef18ce-af28-4e21-a178-85e3c4fef41c
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 6e0f67c6-e44e-4597-823e-51ac8009e18e
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 单一热 Key 会形成单实例热点
  - 单纯扩容不能自动分散同一个 Key 的请求
  - 可通过业务预估、客户端、代理层和 Redis 工具发现热 Key
### ec679cc8-0bab-4a42-8c82-71b8ccc41ffe
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 35347050-3659-4e4a-b7e6-c938ac30ba95
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### ac6450de-8c72-4522-8dd9-b8bd93481f33
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7900c458-dc24-41a4-93c1-3fca0890926b
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Ping 正常结果包含 RTT、TTL 等字段
  - Unknown host 对应名称解析问题
  - Destination host unreachable 对应路由问题
  - Request timed out 可能与不可达或 ICMP 丢弃有关
### 44b091a9-9303-455f-b3d4-82b7a4ebea80
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redis 2.6 支持 Lua
  - 键过期精度支持毫秒
  - 从节点支持只读
  - redis-cli 支持 --eval
### 8d4e0f65-1c79-4b7c-9f1a-5544eff04adf
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Top Key 与离线全量分析的能力差异
  - bigkeys、memkeys、hotkeys 的用途差异
### f24fcfdb-a666-43e3-8908-51a4c427aeb3
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - STRLEN/LLEN/HLEN/SCARD/ZCARD/XLEN 可辅助分析不同类型 Key
  - MONITOR 会消耗资源，不建议长期使用
  - 业务层或 RDB 工具可定位热点/大 Key
### b450fa80-4dae-4451-80c6-5a5e5ed9cd63
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 可通过清理、压缩、拆分、转存处理
  - UNLINK 可异步删除大 Key
  - 热 Key 可通过副本或读写分离缓解，但存在一致性权衡
### da28c124-72d6-44b8-9232-0f30c8553b09
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 常由数据过大、成员过多或无效数据累积产生
  - 热 Key 可由突发访问量产生
  - 大 Key 会导致内存和分片资源不均
### 6e762405-d7b1-41c2-9672-063edea14b46
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 573a2228-bf05-4c42-ace5-54ae1276296f
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7aedf20c-a9d1-406d-b0ec-67cad013c604
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### ac37d2dc-d755-422a-aa63-baa5d302b2ce
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 可导致 rebalance/迁移失败和命令阻塞
  - 热 Key 可造成单分片 CPU 与带宽压力
### 9b76a641-e132-42a7-99cd-d8449e424457
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 使用线程标识和重入计数维护可重入锁
  - 获取失败时返回 TTL 进入等待/重试流程
  - 未显式指定 leaseTime 时文中给出默认 watchdog timeout
### f853d0c7-270a-46da-9eee-4e4d526ee648
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 获取失败后不会简单忙轮询
  - 使用 Pub/Sub 等待锁释放通知
  - 重试受到剩余 waitTime/TTL 限制
### fc9f1a15-0a08-45ed-b5bb-08dc214659b4
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 重试通过等待与唤醒避免持续占用 CPU
  - WatchDog 在业务未完成时周期性续约
  - 正常释放后停止续约，客户端异常后最终由 TTL 释放
### d7a15564-e469-464f-9e49-364964ca55c3
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### e39cbe02-1edf-43a1-a45f-f0faa1cda823
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 776f3a65-b66e-4b11-a096-66608f5454a4
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 83e8fb99-a4eb-4fe7-9f92-dff9776986ff
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 18a489f4-95a4-49a6-8ab6-2d0cc9150668
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A

## Human Review Results (v1)

### 881ee352-b7c6-4fa1-83c8-e1f802d1f129
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 5224115d-af43-447a-a96f-ae12459c0d9b
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### da6f4372-fa23-4d84-b2f3-98dd256253f0
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 解锁前必须校验锁持有者
  - Lua 可原子执行 compare-and-delete
  - 单 Redis 实例存在单点故障风险
### b39ddde1-9b8a-46d1-bcfc-23c468c1634f
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redlock 在多个独立 Redis 实例上申请锁
  - 使用随机唯一 value 标识锁所有者
  - 多数实例成功是获取锁的核心条件
### 7854e15d-b9bf-4382-917f-be979ebca791
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redis 主从异步复制可能导致故障切换后锁丢失
  - Redlock 要求至少 N/2+1 节点成功
  - 获取耗时必须小于锁有效期
### dfef6d0c-18a6-4651-9ad2-4cf3ed6aa4db
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redlock 节点可以彼此独立
  - 客户端应保持低延迟通信
  - 可使用多路复用并行发送 SET 请求
### 1cc83662-096d-4bb9-be35-bc9a7e8b844c
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - fencing token 要求资源服务器能够拒绝旧 token
  - 文中讨论使用随机锁 value 配合资源侧校验的方案
### 3e1c8633-3aba-45ed-b7a8-d8ac46803fae
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 文中区分分布式锁的互斥性与操作顺序性
  - ZooKeeper 可利用临时节点实现锁生命周期管理
### ca51e67f-0d3e-4452-902c-4ba2cea05965
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - ZooKeeper Session 通过心跳维持临时节点
  - 长进程暂停可能导致 Session 过期及锁丢失
  - 极端情况下分布式锁不能替代资源层一致性兜底
### 79ee9853-ab18-4e37-b727-a87c643ab063
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Ping 测 RTT 与目标连接稳定性
  - Traceroute 展示数据包经过的 Hop 路径
### 0727ac9b-a72e-485c-bb0f-e2afbab30777
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 04dc005d-210b-4537-ac99-54ebcb5048dc
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7cb50cf1-a34a-413b-a1eb-65b3f63a1e4a
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### b6568712-4048-4f21-a94a-dbd2dc476060
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### cd44e304-434b-4a35-8a69-ae001738bd11
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7ce2d1e9-1f93-431a-916e-32a4e5c2b084
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### c8bb7bc9-148d-484b-8640-2c75872ffc94
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 并发更新数据库和缓存可能产生旧缓存覆盖新值
  - 先删缓存再更新数据库存在读请求回填旧值窗口
### 62e6e94b-7c6d-425b-8506-20a2f78d8e1f
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### c4145c16-3a0d-438f-8b4f-4156e0e68206
- human_status: B
- usable_for_gold: true
- needs_neighbor: true
- fact_points:
  - 进程暂停和网络延迟可能持续很长时间
  - 这类暂停会破坏基于固定租约时间的安全假设
  - 必须结合相邻上下文使用
### da1668e8-f06e-4181-b382-1feedc6d4187
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 可使用 Hash 中线程标识和计数实现可重入
  - Lua 同时维护计数和 PEXPIRE
### a3d8f9ec-9e3c-4b75-9d23-c6f423bc9911
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 解锁应校验 requestId
  - Lua 将 GET 校验和 DEL 合并为原子操作
### c7e2bfee-252e-4f4d-a5ec-76c6c89793e3
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 723b50ac-8359-492e-9e5b-5295a356e5df
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 398521a8-0d16-4f5d-9575-165f972e6ad5
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - ZooKeeper 使用临时有序节点竞争锁
  - 未获得锁的客户端监听前驱节点
  - 前驱释放后重新判断是否获得锁
### fb18e10b-3846-43da-8584-c83729afdfc3
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 临时节点随客户端故障自动删除
  - Curator 提供可重入锁、不可重入锁、读写锁和 MultiLock
### c3c1c313-3662-4dc7-bff6-309e3b9e45d1
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 锁粒度过粗会降低并发
  - 可按资源 ID 或分段方式细化锁
  - 网络分区可能产生锁状态冲突
### ff651920-a885-4987-a701-a674ef6f6afd
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 锁先过期而业务未完成可能导致误删其他客户端的锁
  - 唯一客户端 ID 可标识锁所有权
  - SET NX EX/PX 与 Lua 解锁用于提高原子性
### f358f7db-de57-4f73-bd5a-9799f2906cb4
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 读锁之间可共享
  - 读写、写写需要互斥
  - 分段锁可以降低锁粒度提高并发
### 18ef18ce-af28-4e21-a178-85e3c4fef41c
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 6e0f67c6-e44e-4597-823e-51ac8009e18e
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 单一热 Key 会形成单实例热点
  - 单纯扩容不能自动分散同一个 Key 的请求
  - 可通过业务预估、客户端、代理层和 Redis 工具发现热 Key
### ec679cc8-0bab-4a42-8c82-71b8ccc41ffe
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 35347050-3659-4e4a-b7e6-c938ac30ba95
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### ac6450de-8c72-4522-8dd9-b8bd93481f33
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7900c458-dc24-41a4-93c1-3fca0890926b
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Ping 正常结果包含 RTT、TTL 等字段
  - Unknown host 对应名称解析问题
  - Destination host unreachable 对应路由问题
  - Request timed out 可能与不可达或 ICMP 丢弃有关
### 44b091a9-9303-455f-b3d4-82b7a4ebea80
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redis 2.6 支持 Lua
  - 键过期精度支持毫秒
  - 从节点支持只读
  - redis-cli 支持 --eval
### 8d4e0f65-1c79-4b7c-9f1a-5544eff04adf
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Top Key 与离线全量分析的能力差异
  - bigkeys、memkeys、hotkeys 的用途差异
### f24fcfdb-a666-43e3-8908-51a4c427aeb3
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - STRLEN/LLEN/HLEN/SCARD/ZCARD/XLEN 可辅助分析不同类型 Key
  - MONITOR 会消耗资源，不建议长期使用
  - 业务层或 RDB 工具可定位热点/大 Key
### b450fa80-4dae-4451-80c6-5a5e5ed9cd63
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 可通过清理、压缩、拆分、转存处理
  - UNLINK 可异步删除大 Key
  - 热 Key 可通过副本或读写分离缓解，但存在一致性权衡
### da28c124-72d6-44b8-9232-0f30c8553b09
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 常由数据过大、成员过多或无效数据累积产生
  - 热 Key 可由突发访问量产生
  - 大 Key 会导致内存和分片资源不均
### 6e762405-d7b1-41c2-9672-063edea14b46
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 573a2228-bf05-4c42-ace5-54ae1276296f
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7aedf20c-a9d1-406d-b0ec-67cad013c604
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### ac37d2dc-d755-422a-aa63-baa5d302b2ce
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 可导致 rebalance/迁移失败和命令阻塞
  - 热 Key 可造成单分片 CPU 与带宽压力
### 9b76a641-e132-42a7-99cd-d8449e424457
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 使用线程标识和重入计数维护可重入锁
  - 获取失败时返回 TTL 进入等待/重试流程
  - 未显式指定 leaseTime 时文中给出默认 watchdog timeout
### f853d0c7-270a-46da-9eee-4e4d526ee648
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 获取失败后不会简单忙轮询
  - 使用 Pub/Sub 等待锁释放通知
  - 重试受到剩余 waitTime/TTL 限制
### fc9f1a15-0a08-45ed-b5bb-08dc214659b4
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 重试通过等待与唤醒避免持续占用 CPU
  - WatchDog 在业务未完成时周期性续约
  - 正常释放后停止续约，客户端异常后最终由 TTL 释放
### d7a15564-e469-464f-9e49-364964ca55c3
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### e39cbe02-1edf-43a1-a45f-f0faa1cda823
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 776f3a65-b66e-4b11-a096-66608f5454a4
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 83e8fb99-a4eb-4fe7-9f92-dff9776986ff
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 18a489f4-95a4-49a6-8ab6-2d0cc9150668
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A

## Human Review Results (v1)

### 881ee352-b7c6-4fa1-83c8-e1f802d1f129
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 5224115d-af43-447a-a96f-ae12459c0d9b
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### da6f4372-fa23-4d84-b2f3-98dd256253f0
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 解锁前必须校验锁持有者
  - Lua 可原子执行 compare-and-delete
  - 单 Redis 实例存在单点故障风险
### b39ddde1-9b8a-46d1-bcfc-23c468c1634f
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redlock 在多个独立 Redis 实例上申请锁
  - 使用随机唯一 value 标识锁所有者
  - 多数实例成功是获取锁的核心条件
### 7854e15d-b9bf-4382-917f-be979ebca791
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redis 主从异步复制可能导致故障切换后锁丢失
  - Redlock 要求至少 N/2+1 节点成功
  - 获取耗时必须小于锁有效期
### dfef6d0c-18a6-4651-9ad2-4cf3ed6aa4db
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redlock 节点可以彼此独立
  - 客户端应保持低延迟通信
  - 可使用多路复用并行发送 SET 请求
### 1cc83662-096d-4bb9-be35-bc9a7e8b844c
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - fencing token 要求资源服务器能够拒绝旧 token
  - 文中讨论使用随机锁 value 配合资源侧校验的方案
### 3e1c8633-3aba-45ed-b7a8-d8ac46803fae
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 文中区分分布式锁的互斥性与操作顺序性
  - ZooKeeper 可利用临时节点实现锁生命周期管理
### ca51e67f-0d3e-4452-902c-4ba2cea05965
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - ZooKeeper Session 通过心跳维持临时节点
  - 长进程暂停可能导致 Session 过期及锁丢失
  - 极端情况下分布式锁不能替代资源层一致性兜底
### 79ee9853-ab18-4e37-b727-a87c643ab063
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Ping 测 RTT 与目标连接稳定性
  - Traceroute 展示数据包经过的 Hop 路径
### 0727ac9b-a72e-485c-bb0f-e2afbab30777
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 04dc005d-210b-4537-ac99-54ebcb5048dc
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7cb50cf1-a34a-413b-a1eb-65b3f63a1e4a
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### b6568712-4048-4f21-a94a-dbd2dc476060
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### cd44e304-434b-4a35-8a69-ae001738bd11
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7ce2d1e9-1f93-431a-916e-32a4e5c2b084
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### c8bb7bc9-148d-484b-8640-2c75872ffc94
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 并发更新数据库和缓存可能产生旧缓存覆盖新值
  - 先删缓存再更新数据库存在读请求回填旧值窗口
### 62e6e94b-7c6d-425b-8506-20a2f78d8e1f
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### c4145c16-3a0d-438f-8b4f-4156e0e68206
- human_status: B
- usable_for_gold: true
- needs_neighbor: true
- fact_points:
  - 进程暂停和网络延迟可能持续很长时间
  - 这类暂停会破坏基于固定租约时间的安全假设
  - 必须结合相邻上下文使用
### da1668e8-f06e-4181-b382-1feedc6d4187
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 可使用 Hash 中线程标识和计数实现可重入
  - Lua 同时维护计数和 PEXPIRE
### a3d8f9ec-9e3c-4b75-9d23-c6f423bc9911
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 解锁应校验 requestId
  - Lua 将 GET 校验和 DEL 合并为原子操作
### c7e2bfee-252e-4f4d-a5ec-76c6c89793e3
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 723b50ac-8359-492e-9e5b-5295a356e5df
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 398521a8-0d16-4f5d-9575-165f972e6ad5
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - ZooKeeper 使用临时有序节点竞争锁
  - 未获得锁的客户端监听前驱节点
  - 前驱释放后重新判断是否获得锁
### fb18e10b-3846-43da-8584-c83729afdfc3
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 临时节点随客户端故障自动删除
  - Curator 提供可重入锁、不可重入锁、读写锁和 MultiLock
### c3c1c313-3662-4dc7-bff6-309e3b9e45d1
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 锁粒度过粗会降低并发
  - 可按资源 ID 或分段方式细化锁
  - 网络分区可能产生锁状态冲突
### ff651920-a885-4987-a701-a674ef6f6afd
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 锁先过期而业务未完成可能导致误删其他客户端的锁
  - 唯一客户端 ID 可标识锁所有权
  - SET NX EX/PX 与 Lua 解锁用于提高原子性
### f358f7db-de57-4f73-bd5a-9799f2906cb4
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 读锁之间可共享
  - 读写、写写需要互斥
  - 分段锁可以降低锁粒度提高并发
### 18ef18ce-af28-4e21-a178-85e3c4fef41c
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 6e0f67c6-e44e-4597-823e-51ac8009e18e
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 单一热 Key 会形成单实例热点
  - 单纯扩容不能自动分散同一个 Key 的请求
  - 可通过业务预估、客户端、代理层和 Redis 工具发现热 Key
### ec679cc8-0bab-4a42-8c82-71b8ccc41ffe
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 35347050-3659-4e4a-b7e6-c938ac30ba95
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### ac6450de-8c72-4522-8dd9-b8bd93481f33
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7900c458-dc24-41a4-93c1-3fca0890926b
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Ping 正常结果包含 RTT、TTL 等字段
  - Unknown host 对应名称解析问题
  - Destination host unreachable 对应路由问题
  - Request timed out 可能与不可达或 ICMP 丢弃有关
### 44b091a9-9303-455f-b3d4-82b7a4ebea80
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redis 2.6 支持 Lua
  - 键过期精度支持毫秒
  - 从节点支持只读
  - redis-cli 支持 --eval
### 8d4e0f65-1c79-4b7c-9f1a-5544eff04adf
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Top Key 与离线全量分析的能力差异
  - bigkeys、memkeys、hotkeys 的用途差异
### f24fcfdb-a666-43e3-8908-51a4c427aeb3
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - STRLEN/LLEN/HLEN/SCARD/ZCARD/XLEN 可辅助分析不同类型 Key
  - MONITOR 会消耗资源，不建议长期使用
  - 业务层或 RDB 工具可定位热点/大 Key
### b450fa80-4dae-4451-80c6-5a5e5ed9cd63
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 可通过清理、压缩、拆分、转存处理
  - UNLINK 可异步删除大 Key
  - 热 Key 可通过副本或读写分离缓解，但存在一致性权衡
### da28c124-72d6-44b8-9232-0f30c8553b09
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 常由数据过大、成员过多或无效数据累积产生
  - 热 Key 可由突发访问量产生
  - 大 Key 会导致内存和分片资源不均
### 6e762405-d7b1-41c2-9672-063edea14b46
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 573a2228-bf05-4c42-ace5-54ae1276296f
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 7aedf20c-a9d1-406d-b0ec-67cad013c604
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### ac37d2dc-d755-422a-aa63-baa5d302b2ce
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 大 Key 可导致 rebalance/迁移失败和命令阻塞
  - 热 Key 可造成单分片 CPU 与带宽压力
### 9b76a641-e132-42a7-99cd-d8449e424457
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 使用线程标识和重入计数维护可重入锁
  - 获取失败时返回 TTL 进入等待/重试流程
  - 未显式指定 leaseTime 时文中给出默认 watchdog timeout
### f853d0c7-270a-46da-9eee-4e4d526ee648
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - 获取失败后不会简单忙轮询
  - 使用 Pub/Sub 等待锁释放通知
  - 重试受到剩余 waitTime/TTL 限制
### fc9f1a15-0a08-45ed-b5bb-08dc214659b4
- human_status: A
- usable_for_gold: true
- needs_neighbor: false
- fact_points:
  - Redisson 重试通过等待与唤醒避免持续占用 CPU
  - WatchDog 在业务未完成时周期性续约
  - 正常释放后停止续约，客户端异常后最终由 TTL 释放
### d7a15564-e469-464f-9e49-364964ca55c3
- human_status: C
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### e39cbe02-1edf-43a1-a45f-f0faa1cda823
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 776f3a65-b66e-4b11-a096-66608f5454a4
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 83e8fb99-a4eb-4fe7-9f92-dff9776986ff
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
### 18a489f4-95a4-49a6-8ab6-2d0cc9150668
- human_status: D
- usable_for_gold: false
- needs_neighbor: false
- fact_points:
  - N/A
