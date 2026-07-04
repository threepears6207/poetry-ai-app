import requests
import json

BASE_URL = "http://127.0.0.1:8000"

response = requests.post(
    f"{BASE_URL}/generate/image",
    json={
        "poem_id": "poem_003",
        "poem_title": "咏鹅",
        "poem_content": ["鹅鹅鹅", "曲项向天歌", "白毛浮绿水", "红掌拨清波"],
        "poet_name": "骆宾王",
        "dynasty": "唐",
        "tags": ["鹅", "水", "自然", "儿童启蒙"]
    },
    timeout=300
)

result = response.json()
print(json.dumps(result, ensure_ascii=False, indent=2))
