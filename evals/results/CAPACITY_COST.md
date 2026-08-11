# Capacity & cost controlled benchmarks

- Generated (UTC): `2026-08-11T03:52:39.294301+00:00`
- Base URL: `http://127.0.0.1:8000`
- Host: `董` / Python `3.11.15`
- Ready: `ready`

## Scope / 口径限制（必读）

1. 本报告是**单机受控实验**，不是生产容量规划，也不是线上真实流量。
2. **禁止**把并发数或 P95 延迟换算成 QPS；Chat 吞吐以实测 `req/s` 为准。
3. Job 侧报告 **jobs/min / jobs/hour**，不要叫 QPS；受全局并发槽位（实验并发≤2）约束。
4. 成本只汇总 `Job.result.cost` 中的 **searches / llm_calls**（完成任务）；
   **没有**稳定线上平均客单价（USD），也不编造 token 均价。
5. 单次任务成本与模型、检索次数、上下文和输出长度强相关；短/中档仅作对比，不可外推。

## Environment

| Check | OK | Detail |
| --- | --- | --- |
| postgres | True | ok |
| redis | True | ok |
| migrations | True | 005_embedding_dim_1024 |
| queue | True | ok |

## Commands

```bash
D:\anaconda3\envs\gptresearcher\python.exe evals/perf_eval/run_capacity_cost.py \
  --base-url http://127.0.0.1:8000 \
  --chat-duration-sec 1800 \
  --chat-concurrency 5 \
  --short-n 15 \
  --medium-n 8 \
  --job-concurrency 2
```

Artifacts: `evals/results/capacity_cost_latest.json`, this markdown.

## 1) Chat soak (throughput)

- Prompt: `用一句话介绍 GPT Researcher 是什么`
- Target duration: **1800s** (actual **1801.49s**)
- Concurrency (closed-loop workers): **5**

| Metric | Value |
| --- | --- |
| Success requests | 5361 |
| Errors | 0 |
| Success req/s | 2.976 |
| Error rate | 0.0 |
| Latency p50 (ms) | 1644.74 |
| Latency p95 (ms) | 2177.13 |
| Latency p99 (ms) | 2785.94 |
| Latency mean (ms) | 1679.64 |
| Latency max (ms) | 4280.33 |
| HTTP status counts | {"200": 5361} |

> Closed-loop soak throughput on a single host; NOT production QPS capacity. Do not derive QPS from concurrency alone.

## 2) Short Job batch (cost + throughput)

- Task: `用80字介绍 Redis 核心用途`
- `total_words=80`, n=**15**, concurrency=**2**

| Metric | Value |
| --- | --- |
| Completed / N | 14 / 15 |
| Success rate | 0.9333 |
| Wall clock (batch sec) | 683.1 |
| Jobs / min | 1.23 |
| Jobs / hour | 73.78 |
| Wall p50 (sec) | 36.53 |
| Wall p95 (sec) | 386.13 |
| Wall mean (sec) | 63.88 |
| Searches mean (completed) | 3.0 |
| LLM calls mean (completed) | 3.0 |
| LLM calls p50 (completed) | 3.0 |

> Queue throughput under RESEARCH_MAX_CONCURRENT_GLOBAL≈2 style caps; report as jobs/hour, not QPS.

## 3) Medium Job batch (comparison)

- Task: `用600字概述向量数据库的主要选型维度与常见产品`
- `total_words=600`, n=**8**, concurrency=**2**

| Metric | Value |
| --- | --- |
| Completed / N | 8 / 8 |
| Success rate | 1.0 |
| Wall clock (batch sec) | 171.97 |
| Jobs / min | 2.791 |
| Jobs / hour | 167.47 |
| Wall p50 (sec) | 42.58 |
| Wall p95 (sec) | 45.66 |
| Wall mean (sec) | 41.83 |
| Searches mean (completed) | 3.0 |
| LLM calls mean (completed) | 3.0 |
| LLM calls p50 (completed) | 3.0 |

## Short vs medium (side-by-side)

| Cohort | n | Completed | Jobs/hour | Wall p95 (s) | LLM calls mean | Searches mean |
| --- | --- | --- | --- | --- | --- | --- |
| short | 15 | 14 | 73.78 | 386.13 | 3.0 | 3.0 |
| medium | 8 | 8 | 167.47 | 45.66 | 3.0 | 3.0 |

## Observations（读数时注意）

1. **Chat**：30 分钟 closed-loop soak，5361/5361 成功，可持续约 **2.98 req/s**，P95≈**2.2s**，错误率 0。这是实测吞吐，不是用并发反推的 QPS。
2. **短 Job**：15 个中完成 14；多数墙钟约 **33–50s**，但有 1 个约 **386s** 长尾，把 wall p95 拉高到 386s。面试可同时报 **p50≈36.5s** 与 **p95（含长尾）**。
3. **成本字段**：完成任务的 `searches` / `llm_calls` 均值均为 **3.0**（受单 Job 预算/检索上限约束）。短档与中档在本配置下**调用次数未拉开**，因此不能据此声称「600 字一定更贵」；只能说「在当前预算封顶下，完成任务约 3 次检索 + 3 次 LLM」。
4. **中档 jobs/hour 高于短档**：主要因为中档无长尾失败、批次更短，不代表「中档更容易」或「容量更大」；对比时优先看单任务 wall 分布与 cost，不要只看 jobs/hour。
5. 跑短 Job 过程中出现过 Tavily 单 key 额度告警并轮换到下一 key；吞吐/成本结论依赖检索可用性。

## Interview / resume wording (safe)

- ✅ 「单机受控压测：Chat 可持续约 **3.0 req/s**（worker=5，P95≈2.2s，错误率 0；30min soak）」
- ✅ 「短 Job（并发≤2）完成 14/15，完成速率约 **74 jobs/hour**；完成任务成本约 **3 searches + 3 LLM calls**（`Job.result.cost`）」
- ✅ 「另测中档 Job 8/8 完成；在当前预算封顶下调用次数与短档同为 3，说明成本需按档位/预算单独测，不能用字数线性外推」
- ❌ 不要写「生产 QPS / 线上平均成本 / 把 P95 换算成 QPS」

Raw JSON: `F:\agent\gpt-researcher\evals\results\capacity_cost_20260811T043653Z.json`
