from dotenv import load_dotenv
import os
from tavily import TavilyClient

load_dotenv(".env")

for key in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]:
    os.environ.pop(key, None)

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

result = client.search(
    query="GPT Researcher GitHub",
    max_results=3,
)

print("RESULT KEYS:", result.keys())
print("NUM RESULTS:", len(result.get("results", [])))

for i, item in enumerate(result.get("results", []), start=1):
    print("=" * 60)
    print("RESULT", i)
    print("TITLE:", item.get("title"))
    print("URL:", item.get("url"))
