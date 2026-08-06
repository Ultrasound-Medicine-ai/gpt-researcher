from pathlib import Path

env_path = Path(".env")
text = env_path.read_text(encoding="utf-8", errors="ignore")

for i, line in enumerate(text.splitlines(), start=1):
    if "TAVILY" in line or "RETRIEVER" in line:
        if line.strip().startswith("TAVILY_API_KEY"):
            value = line.split("=", 1)[1] if "=" in line else ""
            print(f"line {i}: TAVILY_API_KEY length={len(value.strip())}, first6={value.strip()[:6]}***")
        else:
            print(f"line {i}: {line}")
