# Retrieval Gold Omission Review

> 基于完整 299 Child corpus 的现有 Retriever Top20 候选：FTS、Vector 与其 RRF Hybrid。以下仅为待人工确认项，未自动修改 Gold，且不用于任何 Recall/MRR 指标。

## pilot-005
- Query：Cache-Aside、Read-Through 与 Write-Through 的数据读写责任分别落在哪一层？
- Existing Gold Child：`4637bbd5-b09f-4552-9b54-c8f5cf012e33`、`c64e20e7-7125-402e-bb71-c7f016f02aee`
- Possible Missing Child：`b2cf4ad2-19d5-4a62-aaa1-0f06834642ce`
- Parent ID：`cab0e2c7-7d80-4184-b184-4d6b198fb6e4`
- Retrieval Source / Rank：Vector #6；Hybrid #6
- 原文片段：该段讨论缓存更新与数据库更新的四种顺序，以及高并发下的数据不一致问题。
- 为什么可能相关：与已标注 Child 同属缓存模式章节，可能补充 Write-Through 的写入语境；但不直接定义三种模式的读写责任，需人工判定。
- [ ] 加入 Gold
- [x] 不相关（rejected）
- 人工裁决：不加入 Gold。该 Child 讨论缓存与数据库更新顺序及高并发一致性问题；虽同属 Cache 模式章节，但不能直接回答 Cache-Aside / Read-Through / Write-Through 的读写责任边界，仅是相关背景而非必要 Relevant Evidence。

## pilot-014
- Query：采用“先更新数据库再删缓存”后，极端并发仍可能怎样读到旧值，又如何用 binlog 和重试收敛？
- Existing Gold Child：`f0e4adc6-83b1-47c9-8aee-df5b578c16bf`、`126e7851-9146-4c9b-a8b3-a6ad0f674eec`、`da4c9ffd-140f-4491-aebf-606ec2dc737e`
- Possible Missing Child：`c8bb7bc9-148d-484b-8640-2c75872ffc94`
- Parent ID：`1dca64e0-586d-48b8-85ef-ee3485a637f9`
- Retrieval Source / Rank：Vector #8；Hybrid #8
- 原文片段：该段分析“先更新缓存再更新数据库”与“先删缓存再更新数据库”在高并发下导致缓存旧值的风险。
- 为什么可能相关：同属缓存与数据库一致性章节，包含旧值与并发交错的反例；但不是 Query 指定的“先更新数据库再删缓存”路径，需人工判定。
- [ ] 加入 Gold
- [x] 不相关（rejected）
- 人工裁决：不加入 Gold。该 Child 讨论“先更新缓存再更新数据库”和“先删缓存再更新数据库”等其他一致性路径；Query 明确限定“先更新数据库再删缓存”，该内容仅可作为对比背景，并非当前问题的必要证据。
