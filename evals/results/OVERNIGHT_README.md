# 明早查阅（夜间全自动）

无需手动操作。链路：

1. 等当前 **random SimpleQA n=100** 跑完  
2. **自动停掉** random 后续（避免再花一份幻觉钱）  
3. **分层 SimpleQA n=100**（`sample_mode=stratified`, seed=42）  
4. **幻觉全量 70**（`by_bucket`）  
5. 重建 `PORTFOLIO_METRICS.md` + dashboard  

## 先看这个

- `evals/results/OVERNIGHT_STATUS.md` — 是否 DONE / 各步 exit code  
- `evals/results/PORTFOLIO_METRICS.md` — 简历分账数字  
- `evals/results/simpleqa_latest.json` — 应有 `"sample_mode": "stratified"`  
- `evals/results/hallucination_latest.json` — 应有 `effective_n: 70`  
- `evals/results/portfolio_n100_chain.log` — 全程时间线  

Random 归档：`evals/results/archive_random_n100/`
