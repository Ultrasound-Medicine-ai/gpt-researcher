"""Smoke-test Matpool chat models for latency (no secrets printed). :-)"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def main() -> None:
    env = load_env(Path(".env"))
    key = env.get("MATPOOL_API_KEY", "")
    base = (env.get("MATPOOL_BASE_URL") or "https://token.matpool.com/v1").rstrip("/")
    print(f"base={base} key_len={len(key)}")
    models = [
        "Qwen3.5-Flash",
        "Qwen-Plus",
        "Doubao-Seed-2.0-Mini",
        "DeepSeek-V4-Flash",
    ]
    for model in models:
        body = json.dumps(
            {
                "model": model,
                "messages": [
                    {"role": "user", "content": "用一句话介绍 Server-Sent Events"}
                ],
                "max_tokens": 64,
                "temperature": 0.2,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{base}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
        )
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            dt = time.time() - t0
            content = (
                ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
                or ""
            )
            content = content.replace("\n", " ")[:80]
            print(f"OK {model:28} {dt:5.1f}s  {content}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:240]
            print(f"FAIL {model:28} HTTP {exc.code} {detail}")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {model:28} {exc}")


if __name__ == "__main__":
    main()
