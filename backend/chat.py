from fastapi import APIRouter
from pydantic import BaseModel
import os
import requests
import uuid

router = APIRouter()

VIVO_APP_KEY = os.getenv("VIVO_APP_KEY")


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
def chat(request: ChatRequest):
    result = None
    try:
        url = "https://api-ai.vivo.com.cn/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {VIVO_APP_KEY}"
        }
        data = {
            "requestId": str(uuid.uuid4()),
            "model": "Doubao-Seed-2.0-lite",
            "messages": [
                {
                    "role": "system",
                    "content": "你是一位古代诗人，精通唐诗宋词，善于用诗意的语言与人交流。"
                },
                {
                    "role": "user",
                    "content": request.message
                }
            ]
        }
        response = requests.post(url, json=data, headers=headers)
        result = response.json()

        print("vivo API 返回：", result)

        ai_reply = result['choices'][0]['message']['content']
        return {"success": True, "reply": ai_reply}

    except Exception as e:
        return {"success": False, "error": str(e), "raw": str(result) if result else ""}
