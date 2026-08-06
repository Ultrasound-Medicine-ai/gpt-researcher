from dotenv import load_dotenv
import os

load_dotenv(".env")

keys = [
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "FAST_LLM",
    "SMART_LLM",
    "STRATEGIC_LLM",
    "EMBEDDING",
    "RETRIEVER",
    "TAVILY_API_KEY",
]

for k in keys:
    v = os.getenv(k)
    if not v:
        print(f"{k}: MISSING")
    elif "KEY" in k:
        print(f"{k}: SET, starts with {v[:6]}***")
    else:
        print(f"{k}: {v}")
