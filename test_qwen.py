from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)

resp = client.chat.completions.create(
    model="qwen-plus",
    messages=[
        {"role": "user", "content": "请只回复：qwen-plus connected"}
    ],
    temperature=0,
)

print(resp.choices[0].message.content)
