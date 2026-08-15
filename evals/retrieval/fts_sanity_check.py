"""Four fixed lexical-retrieval checks for the evaluated PostgreSQL corpus."""

from rag.retrieve import fts_search

TENANT_ID = "rag-retrieval-corpus-v1"
USER_ID = "retrieval-eval"
CASES = (
    "先删除缓存再更新数据库时，并发读请求为什么仍可能把旧数据重新写入缓存？",
    "Redis 分布式锁释放时，requestId 校验和 Lua 脚本各负责什么？",
    "设计 Redlock 时，释放锁怎样确认所有者，获取锁又以什么条件判定成功？",
    "SET NX PX",
)


def main() -> None:
    results = [fts_search(query, tenant_id=TENANT_ID, user_id=USER_ID, top_k=20) for query in CASES]
    assert all(results), [len(result) for result in results]
    print(f"fts_targeted_checks_passed={len(results)}")


if __name__ == "__main__":
    main()
