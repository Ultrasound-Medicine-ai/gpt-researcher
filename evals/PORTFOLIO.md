# 项目二评测：简历指标与面试讲法

面向「可放进简历的数字」+「能把评测过程讲完整」。

## 一句话定位

> 为研究 Agent SaaS 建了分层评测：离线门禁（对话/工具/记忆）+ 抽样 live Chat/调研 + SimpleQA 事实性与幻觉率，指标可复现落盘。

## 跑出指标（推荐）

环境：`conda activate gptresearcher`（Python ≥ 3.10），API 容器在 `8000` 可选（live chat 用）。

```bash
# 一键 portfolio：cheap + harness full(1) + live chat + SimpleQA(3) + hallucination(3)
# 默认 sample seed=42（可用 --seed / EVAL_SAMPLE_SEED 覆盖，保证同一子集可复现）
D:\anaconda3\envs\gptresearcher\python.exe evals/run_portfolio.py --num-examples 3 --seed 42
```

产物：

| 文件 | 内容 |
|------|------|
| `evals/results/portfolio_latest.json` | 全量结构化结果 |
| `evals/results/PORTFOLIO_METRICS.md` | 简历可用摘要表 |
| `evals/results/simpleqa_latest.json` | accuracy / F1 / cost |
| `evals/results/hallucination_latest.json` | hallucination_rate |
| `evals/results/live_chat_latest.json` | Chat 工具路由抽样 |

成本可控：`EVAL_TOTAL_WORDS=350`（默认）缩短成文；`--num-examples 3` 即可讲故事，不必上百题。

## 分层门禁（面试时按这个讲）

```text
cheap（每次改代码）
  pytest scorers + harness offline
  + dialogue/tool/memory mock
      → 不花钱，防回归

full（发版前 / portfolio）
  harness live 调研抽样
  + /api/chat live（报告意图、澄清、禁误触发）
      → 小额 token，验真链路

nightly / portfolio（质量基准）
  SimpleQA：报告是否答对事实（CORRECT/INCORRECT/NOT_ATTEMPTED → accuracy/F1）
  Hallucination：报告是否忠实于检索上下文（hallucination_rate）
      → 可写进简历的质量数字
```

## 被测对象怎么对应

| 对象 | 测什么 | 对应套件 |
|------|--------|----------|
| A 调研 Agent | 检索成文、引用、事实、幻觉 | harness + SimpleQA + hallucination |
| B Chat Agent | 意图、工具选择、澄清、拒答 | dialogue/tool cheap + live chat |
| C 记忆/隔离 | 槽位、跨轮、session soft-pass | memory_eval |

## 简历可写指标（以 `PORTFOLIO_METRICS.md` 为准）

从 `evals/results/PORTFOLIO_METRICS.md` 抄最新值。本机 2026-08-10 **n=10** 样例：

- Cheap / full harness / live chat：**PASS**（live chat 3/3）
- SimpleQA：**accuracy / F1 = 70%**（7/10 CORRECT），成本 ≈ **$0.47**
- Hallucination（MAJOR）：**50%**（5/10；severity: MAJOR 5 / MINOR 1 / NONE 4），成本 ≈ **$0.53**
  - judge=`lite` + **multi-source evidence pack** + 仅计 MAJOR（虚构实体/数字/错误归因）

**表述注意：** 写清 `n`、日期、模型与 judge 设定；勿暗示全量 4k SimpleQA。早期 90% 幻觉率来自 `str(list)` 截断导致 judge 只见 1 篇文档——已修复。

## 面试官常问 → 怎么答

**Q: 你怎么保证 Agent 没乱编？**  
A: 两层——离线 citation/language harness；nightly 用检索上下文做 faithfulness judge，出 hallucination_rate。

**Q: 对话里会不会误开报告任务？**  
A: cheap `tool_eval`/`dialogue_eval` 断言 forbid/must tools；full 再打 live `/api/chat`。

**Q: SSE 这种歧义怎么测？**  
A: `resolve_report_intent` 进 dialogue cheap；期望 `clarify` 而不是直接 create_report。

**Q: 和只跑 SimpleQA 有什么不同？**  
A: 上游 SimpleQA 只覆盖报告事实性；项目二并列加了 Chat 工具链与记忆门禁，并统一 `run_gates`/`run_portfolio`。

**Q: 指标能复现吗？**  
A: case JSONL + `*_latest.json` 落盘；SimpleQA 用本地 CSV；抽样用 `--seed` / `EVAL_SAMPLE_SEED`（默认 42），结果里带 `sample_seed`。

## 与开源上游的关系

上游仓库自带 SimpleQA CSV + hallucination 查询集，**没有**对话/工具/记忆支柱。  
本项目：复用上游质量集做 nightly，自建 Project-2 支柱做产品回归。
