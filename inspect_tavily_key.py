from dotenv import load_dotenv
import os

load_dotenv(".env")

v = os.getenv("TAVILY_API_KEY")

if v is None:
    print("TAVILY_API_KEY is None")
else:
    print("raw length:", len(v))
    print("strip length:", len(v.strip()))
    print("first 6 after strip:", v.strip()[:6] + "***")
    print("has quote:", '"' in v or "'" in v)
    print("has space around:", v != v.strip())
