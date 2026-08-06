from pathlib import Path

env_path = Path(".env")
print("ENV path:", env_path.resolve())
print("Exists:", env_path.exists())
print("Size:", env_path.stat().st_size if env_path.exists() else "N/A")
print("=" * 60)

target_keys = [
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "FAST_LLM",
    "SMART_LLM",
    "STRATEGIC_LLM",
    "EMBEDDING",
    "RETRIEVER",
]

text = env_path.read_text(encoding="utf-8", errors="ignore")

for i, line in enumerate(text.splitlines(), start=1):
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        continue

    for key in target_keys:
        if key in stripped:
            if "KEY" in key:
                print(f"line {i}: {key}=***MASKED***")
            else:
                print(f"line {i}: {stripped}")
            break
