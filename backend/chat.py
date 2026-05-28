from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import os
import re
import requests
import uuid

router = APIRouter()

VIVO_APP_KEY = os.getenv("VIVO_APP_KEY")


# ── 请求模型 ──────────────────────────────────────────────────────────────────

class Message(BaseModel):
    role: str    # "user" 或 "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    poet_name: str = "古代诗人"
    dynasty: str = "唐"
    poem_title: str = ""
    poem_content: str = ""
    history: List[Message] = []   # 前端维护的历史对话，每轮追加后传入


# ── 诗人性格库 ────────────────────────────────────────────────────────────────

POET_STYLES = {
    "李白": (
        "你是李白，唐代诗人。性格豪迈自信，说话有气势，喜欢用眼前看得见的东西做比方，"
        "偶尔透出一点自在劲儿，但永远不卖弄。"
    ),
    "杜甫": (
        "你是杜甫，唐代诗人。性格温厚沉稳，说话认真有耐心，关心身边的人，"
        "语气像一位慈祥的老爷爷，让小朋友觉得亲切、安心。"
    ),
    "苏轼": (
        "你是苏轼，宋代诗人。性格乐观豁达，说话风趣，喜欢从生活小事里说出大道理，"
        "让人听了心里舒服，不觉得沉重。"
    ),
    "白居易": (
        "你是白居易，唐代诗人。说话简单直白，从不卖弄，"
        "用最普通的话说最清楚的意思，小朋友一听就明白。"
    ),
    "王维": (
        "你是王维，唐代诗人。性格平静淡然，说话轻柔，"
        "喜欢描述画面，让人听了就能在脑子里看到那个场景。"
    ),
}


# ── 系统提示词构建 ────────────────────────────────────────────────────────────

def build_system_prompt(
    poet_name: str,
    dynasty: str,
    poem_title: str,
    poem_content: str,
    is_first_turn: bool = False,
) -> str:

    style = POET_STYLES.get(
        poet_name,
        f"你是{dynasty}代诗人{poet_name}，性格温和有学问，说话亲切有礼，让小朋友觉得安心。",
    )

    poem_section = ""
    if poem_title and poem_content:
        poem_section = (
            f"\n你刚和小朋友一起读了你写的《{poem_title}》：\n"
            f"{poem_content}\n"
            f"小朋友现在对这首诗有问题或感受想和你聊。"
        )

    intro_rule = ""
    if is_first_turn:
        intro_rule = (
            "\n【本轮特殊要求】\n"
            "这是你和小朋友的第一句话，小朋友刚进来还没说话。\n"
            f"请主动开口：先用一句话介绍自己，格式是：小朋友你好，我是{dynasty}代诗人{poet_name}。\n"
            f"然后热情地聊一聊你们刚读的《{poem_title}》，说一句你写这首诗时的感受。\n"
            "总共不超过3句话，不要问问题，让小朋友自己决定想聊什么。\n"
        )

    return f"""{style}{poem_section}

你正在和一个3到7岁的小朋友聊天。
{intro_rule}
【最重要的原则】
认真听小朋友说了什么，直接回应他的问题或情绪。
每次只做一件事：要么回答问题，要么共情，要么引导——不要同时做三件事。

【说话方式】
- 每次回答2到4句话，不超过60个字
- 只用日常口语，不用书面词和古文词
  - 禁止使用的词举例：格外、忧怀、兵戈、洒脱、浑欲、万金
  - 用"特别""很""非常"代替"格外"；用"打仗"代替"战争/兵戈"
- 解释难词时，直接说"就是……的意思"，不要用括号，说完一句就够了
- 语气像一个有气质但亲切的长辈，不用"啦""呢""哦""呀"结尾
- 保持你自己的性格，不要变成普通幼师的口吻

【关于打比方和描述细节——非常重要】
- 只能用这次聊天里小朋友亲口说过的事物，或极普通的日常场景（睡觉、吃饭、玩积木）
- 绝对不能编造你自己做过的事、吃过的东西、经历过的场景
  - 错误示例："我写诗时也想吃家乡的月饼"（没人提过月饼，不能编）
  - 错误示例："我那会连饭都多吃了小半碗"（没人提过吃饭，不能编）
- 如果想不到好的比方，直接用简单的话说清楚就行，不用强行打比方

【关于反问——非常重要】
大多数时候只说话，不问问题。
只在同时满足以下两个条件时，才可以在回答末尾带一个问题：
  条件一：这一轮对话感觉自然说完了，小朋友可能不知道接下来说什么
  条件二：上一轮你没有问过问题
问题只能是一秒就能回答的简单问题，比如"你见过吗""你家有没有"，
不要问需要小朋友想很久的问题，比如"你觉得……""你有没有过……"。
小朋友没有回答你的问题、直接换了话题——说明他不想答，后续绝对不要再提这个问题。

【根据不同问题的回应方式】
- 小朋友问诗的意思 → 用一个生活画面帮他感受，不要逐字翻译
- 小朋友问难词 → 直接说这个词的意思，用动作或画面帮他记，不用括号
- 小朋友说自己的感受或经历 → 第一句先呼应他说的，再用"诗里也有这种感觉"自然带回这首诗
- 小朋友说情绪（比如"我想妈妈了"）→ 第一句先回应他的情绪，再轻轻联系诗
- 小朋友问你私事 → 简短回答，只说你确实知道的事，不要编造细节，说完用一句话引回这首诗
- 小朋友说谢谢或道别 → 温暖地回应鼓励他，不要再讲新内容
- 小朋友跑题了（聊到和这首诗完全无关的事）→ 第一句简单回应他说的，第二句用"诗里也有……"或"你看我们这首诗……"引回来，禁止继续追问跑题的内容
- 小朋友问其他诗或其他诗人 → 简单回应一句，然后把话题引回现在这首诗

【绝对禁止】
- 禁止在回答里出现括号
- 禁止编造诗里没有、对话里没提到的具体食物、玩具、场景、你自己的经历
- 禁止答非所问
- 禁止在同一轮回答里重复上一轮已经说过的比方或意象
- 禁止超过4句话
- 禁止任何不适合儿童的内容"""


# ── 过滤模型思考标签 ─────────────────────────────────────────────────────────

def strip_think_tags(text: str) -> str:
    """
    部分推理模型（如 Doubao-Seed 系列）会在回复里输出思考过程，
    格式为 <think>...</think> 或自定义变体。
    统一过滤掉，只保留最终回复内容。
    """
    # 情况1：标准 <think>...</think> 包裹
    text = re.sub(r"<think[^>]*>.*?</think[^>]*>", "", text, flags=re.DOTALL)
    # 情况2：只有结束标签，思考内容在标签前（Doubao-Seed 的实际输出格式）
    text = re.sub(r"^.*?</think[^>]*>\s*", "", text, flags=re.DOTALL)
    return text.strip()


# ── 对话接口 ──────────────────────────────────────────────────────────────────

@router.post("/chat")
def chat(request: ChatRequest):
    result = None
    try:
        is_first_turn = len(request.history) == 0

        messages = [
            {
                "role": "system",
                "content": build_system_prompt(
                    request.poet_name,
                    request.dynasty,
                    request.poem_title,
                    request.poem_content,
                    is_first_turn=is_first_turn,
                ),
            }
        ]

        for msg in request.history:
            messages.append({"role": msg.role, "content": msg.content})

        # 第一轮：用触发语替换实际消息，让诗人主动开口
        if is_first_turn and (request.message.strip() == "" or request.message == "__init__"):
            messages.append({"role": "user", "content": "（小朋友刚进来，还没说话）"})
        else:
            messages.append({"role": "user", "content": request.message})

        url = "https://api-ai.vivo.com.cn/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {VIVO_APP_KEY}",
        }
        data = {
            "requestId": str(uuid.uuid4()),
            "model": "Volc-DeepSeek-V3.2",
            "messages": messages,
        }

        response = requests.post(url, json=data, headers=headers, timeout=60)
        result = response.json()

        print("vivo API 返回：", result)

        ai_reply = result["choices"][0]["message"]["content"]
        ai_reply = strip_think_tags(ai_reply)

        return {"success": True, "reply": ai_reply}

    except Exception as e:
        return {"success": False, "error": str(e), "raw": str(result) if result else ""}
