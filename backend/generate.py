from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import os
import uuid
import time
import requests

router = APIRouter()

VIVO_APP_KEY = os.getenv("VIVO_APP_KEY")


# ── 请求模型 ──────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    poem_id: str = ""
    poem_title: str = ""
    poem_content: List[str] = []
    poet_name: str = ""
    dynasty: str = ""
    tags: List[str] = []


# ── 共享风格（所有图一致）────────────────────────────────────────────────────

SHARED_STYLE = (
    "宫崎骏吉卜力风格的中国古风儿童插画，"
    "角色造型圆润可爱，大眼睛，色彩明亮饱和，线条流畅简洁，"
    "背景细腻唯美，整体温暖治愈，"
    "横版构图，适合手机横屏全屏展示，画面干净，无文字无水印，"
    "色调统一，光线方向一致"
)


# ── 第一阶段：整首诗统一规划 ─────────────────────────────────────────────────

def plan_poem_sequence(
    poem_title: str,
    poem_content: List[str],
    poet_name: str,
    dynasty: str,
    tags: List[str],
) -> dict:
    tags_str = "、".join(tags) if tags else "无"
    lines_str = "\n".join([f"{i+1}. {line}" for i, line in enumerate(poem_content)])

    system_prompt = (
        "你是一个专业的中国传统儿童绘本分镜师。"
        "你的任务是为古诗设计连续的插画分镜，像动画一样有承接关系。"
        "严格按照JSON格式输出，不要输出任何其他内容。"
    )

    user_prompt = f"""古诗：《{poem_title}》
作者：{dynasty}代{poet_name}
意象标签：{tags_str}
诗句：
{lines_str}

请完成以下任务：
1. 判断这首诗是否有人物出现（判断标准：诗句里有明确的人的动作或视角，如"举头""低头""锄禾"等）
2. 如果有人物，给出统一的人物形象描述（性别、服装、发型），要求圆润可爱的儿童插画风格面孔，整组图必须用同一个形象
3. 为每一句诗设计一个场景描述，要求：
   - 必须包含该句诗里出现的每一个名词和动作作为视觉元素
   - 月光、霜光、阳光等是光线效果，不是实体球，要描述为"光线洒在地面上""地面泛着银白色光芒"等光线打在物体上的效果
   - 相邻场景之间要有连续性，像动画分镜一样自然过渡，镜头可以推拉移动但场景不能突然跳变
   - 场景描述控制在40字以内

严格按照以下JSON格式输出，不要有任何额外文字：
{{
  "has_character": true或false,
  "character_desc": "人物形象描述，没有人物则为空字符串",
  "frames": [
    {{"index": 0, "line": "诗句1", "scene": "场景描述1"}},
    {{"index": 1, "line": "诗句2", "scene": "场景描述2"}}
  ]
}}"""

    url = "https://api-ai.vivo.com.cn/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {VIVO_APP_KEY}",
    }
    data = {
        "requestId": str(uuid.uuid4()),
        "model": "Volc-DeepSeek-V3.2",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()

        import re
        content = re.sub(r"```json|```", "", content).strip()

        import json
        plan = json.loads(content)
        print(f"整体规划结果：{plan}")
        return plan

    except Exception as e:
        print(f"整体规划失败，使用降级方案：{e}")
        return {
            "has_character": False,
            "character_desc": "",
            "frames": [
                {"index": i, "line": line, "scene": line}
                for i, line in enumerate(poem_content)
            ]
        }


# ── 第二阶段：构建单张图的 Prompt ─────────────────────────────────────────────

def build_image_prompt(
    scene: str,
    poem_title: str,
    dynasty: str,
    character_desc: str,
    has_character: bool,
    prev_scene: str = "",
) -> str:
    character_part = ""
    if has_character and character_desc:
        character_part = f"画面主角：{character_desc}，"

    continuity_part = ""
    if prev_scene:
        continuity_part = f"承接上一画面（{prev_scene}），"

    return (
        f"{dynasty}代古诗《{poem_title}》儿童插画，"
        f"{continuity_part}"
        f"{character_part}"
        f"场景：{scene}，"
        f"{SHARED_STYLE}"
    )


# ── 第三阶段：调用图像生成 API ────────────────────────────────────────────────

def call_image_api(prompt: str) -> dict:
    url = "https://api-ai.vivo.com.cn/api/v1/image_generation"
    params = {
        "module": "aigc",
        "request_id": str(uuid.uuid4()),
        "system_time": int(time.time()),
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {VIVO_APP_KEY}",
    }
    data = {
        "model": "Doubao-Seedream-4.5",
        "prompt": prompt,
        "parameters": {
            "size": "2560x1440",  # 16:9 横屏，像素满足最低要求
        },
    }

    try:
        response = requests.post(
            url, json=data, headers=headers, params=params, timeout=60
        )
        result = response.json()

        if result.get("code") != 0:
            return {
                "success": False,
                "error": result.get("message", "图像生成失败"),
                "image_url": "",
            }

        images = result.get("data", {}).get("images", [])
        image_url = images[0].get("url", "") if images else result.get("data", {}).get("image", "")

        if not image_url:
            return {"success": False, "error": "返回图片URL为空", "image_url": ""}

        return {"success": True, "image_url": image_url, "error": ""}

    except requests.exceptions.Timeout:
        return {"success": False, "error": "图像生成超时，请重试", "image_url": ""}
    except Exception as e:
        return {"success": False, "error": str(e), "image_url": ""}


# ── 配图生成接口 ──────────────────────────────────────────────────────────────

@router.post("/generate/image")
def generate_image(request: GenerateRequest):
    """
    为古诗每句话生成一张横版配图，图片之间有连续性，像动画分镜。

    请求示例：
    {
        "poem_id": "poem_002",
        "poem_title": "静夜思",
        "poem_content": ["床前明月光", "疑是地上霜", "举头望明月", "低头思故乡"],
        "poet_name": "李白",
        "dynasty": "唐",
        "tags": ["月亮", "思乡"]
    }
    """
    if not request.poem_content:
        return {"success": False, "error": "poem_content 不能为空"}

    print(f"\n《{request.poem_title}》开始生成，共 {len(request.poem_content)} 句")

    # 第一阶段：整体规划
    print("── 第一阶段：整体规划分镜 ──")
    plan = plan_poem_sequence(
        poem_title=request.poem_title,
        poem_content=request.poem_content,
        poet_name=request.poet_name,
        dynasty=request.dynasty,
        tags=request.tags,
    )

    has_character = plan.get("has_character", False)
    character_desc = plan.get("character_desc", "")
    planned_frames = plan.get("frames", [])

    print(f"有人物：{has_character}，人物形象：{character_desc}")

    frames = []
    errors = []

    for i, frame_plan in enumerate(planned_frames):
        line = frame_plan.get("line", request.poem_content[i] if i < len(request.poem_content) else "")
        scene = frame_plan.get("scene", line)
        prev_scene = planned_frames[i-1].get("scene", "") if i > 0 else ""

        print(f"\n── 第{i+1}句：{line} ──")
        print(f"规划场景：{scene}")

        prompt = build_image_prompt(
            scene=scene,
            poem_title=request.poem_title,
            dynasty=request.dynasty,
            character_desc=character_desc,
            has_character=has_character,
            prev_scene=prev_scene,
        )
        print(f"图像 prompt：{prompt}")

        result = call_image_api(prompt)

        if result["success"]:
            frames.append({
                "index": i,
                "line": line,
                "scene": scene,
                "image_url": result["image_url"],
                "duration_ms": 3000,
            })
        else:
            errors.append({"index": i, "line": line, "error": result["error"]})
            print(f"第{i+1}句图像生成失败：{result['error']}")

    return {
        "success": len(frames) > 0,
        "poem_title": request.poem_title,
        "has_character": has_character,
        "character_desc": character_desc,
        "total_lines": len(request.poem_content),
        "frames": frames,
        "errors": errors,
    }
