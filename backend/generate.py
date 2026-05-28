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


# ── 共享风格 ──────────────────────────────────────────────────────────────────

SHARED_STYLE = (
    "中国传统儿童绘本插画风格，水彩笔触，色彩柔和温润，"
    "人物造型圆润可爱，线条细腻流畅，背景层次丰富，"
    "整体氛围温暖治愈，国风古典美感，"
    "横版构图，适合手机横屏全屏展示，画面干净，无文字无水印"
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

请完成以下任务并输出JSON：

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【任务一：判断是否需要人物】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 有人物：诗句里有人物动作词（举头、低头、锄禾、独坐、遥望等）或第一人称视角（疑是、思故乡）
❌ 无人物：全诗只写自然景物、动物、植物，无任何人物动作或视角

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【任务二：设计人物形象（有人物时必做）】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
人物形象必须根据以下信息综合推断，禁止套用固定模板：

推断依据（按优先级）：
1. 诗中是否明确描写了人物（如"锄禾日当午"→农夫）
2. 诗人本身的身份和朝代（如李白是唐代浪漫主义诗人；杜甫是忧国忧民的现实主义诗人）
3. 诗的情感基调（羁旅思乡→旅途中的文人；田园劳作→朴素农夫；闺怨→年轻女性）

朝代服饰参考：
- 唐代：宽袍大袖，颜色较鲜艳，男性常着圆领袍或交领长衫
- 宋代：服饰趋于简洁素雅，男性常着直裰或道袍
- 明代：领子较高，袖口较窄，颜色深沉
- 其他朝代自行判断贴合历史

character_desc必须同时包含五项（缺一不可）：
① 具体年龄数字（如"约40岁"）
② 性别
③ 服装精确颜色+款式（如"深灰色宽袖交领长衫系棕色布腰带"）
④ 发型细节（如"黑色发髻盘于头顶以木簪固定"）
⑤ 体型特征（如"中等身材略显消瘦"）——防止每张图人物胖瘦不一

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【任务三：确定场景内反复出现的建筑元素样式】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
只锁定那些会在多张图里反复出现的具体建筑/家具的样式，不锁定整个场景：

目标：当同一扇窗、同一张床、同一面墙在不同分镜中出现时，必须样式一致。
方法：提前定义这些元素的具体样式，如"木格推拉窗，窗框深棕色"、"矮脚木床，床头有雕花"。

注意：这不是限制场景只能在室内——当镜头随诗句移向窗外庭院、远处夜空时，新场景的内容可以自由发挥；只是当那扇窗再次出现时，它的样式必须和之前一致。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【任务四：设计每句诗的分镜场景】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【镜头变化规则】
相邻两句镜头类型必须不同：远景 / 中景 / 近景 / 主观视角

【人物站位规则——极其重要】
每张图必须同时写明：
1. 人物在空间中的具体位置（如"站在木格推拉窗旁"、"坐在矮脚木床左侧床沿"）
2. 双手位置（如"双手扶窗沿"、"双手背于身后"、"右手扶窗框左手垂于身侧"）
❌ 禁止只写姿态不写位置（"人物低头"→ 模型不知道在哪，会随机放人物，可能站在床上）

【情绪外化规则——重要】
抽象情绪和心理活动必须转化为可见的视觉符号，不能只靠表情传达：

疑惑/怀疑类（如"疑是"）：
✅ 人物头顶右上方飘着一个手绘风格的大问号"？"，眉头微皱，头略微歪向一侧

惊喜/发现类：
✅ 人物头顶飘着"！"符号，眼睛睁大，嘴微张

思念/乡愁类：
✅ 人物头部旁有白色半透明云朵气泡，气泡内画出故乡场景（茅草屋、炊烟、家人剪影）

悲伤/忧愁类：
✅ 人物眼角有小水滴泪珠，背景色调偏冷蓝，可有细雨丝

喜悦类：
✅ 人物嘴角上扬露齿，背景有蝴蝶或花瓣飘落

❌ 禁止：若有所思、沉浸在思绪中、表情柔和悠远（这些无法画出来）

【场景视角自由扩展规则】
镜头可以随诗句内容自由移动，不受室内限制：
- 人物望向窗外时：镜头切换到人物背影+窗外院子/夜空的组合画面
- 诗句描写远处景物时：可以用远景或主观视角展示窗外全景
- 场景可以从室内移到室外，只要和诗句内容吻合

【光线描述规则】
只描述光照射在什么物体上呈现什么颜色，不描述光的几何形状：
✅ 月光将地面木板染成冷白色、月光从木格窗斜射进来照亮地面一片
❌ 地面出现方形/矩形光块（会画出实体方块）

【比喻不等于实体规则】
诗中比喻在室内场景不能画成实体：
- 室内"疑是地上霜"→ 描述"月光将地板映成银白色"，不要在室内地板画霜晶堆
- 室外场景→ 可以画真实霜晶/雪覆盖地面
- 场景描述中禁止出现"如同""宛如""好像"等比喻词

场景描述控制在65字以内，全部是可以直接画出来的具体视觉内容。

━━━━━━━━━━━━━━━━━━━━━━━
严格按照以下JSON格式输出，不要有任何额外文字：
{{
  "has_character": true或false,
  "character_desc": "五项完整人物描述（无人物则为空字符串）",
  "recurring_elements": "反复出现的建筑/家具样式描述（如窗的样式、床的样式）",
  "frames": [
    {{"index": 0, "line": "诗句1", "scene": "场景描述（含人物具体位置+双手姿态+情绪外化+视觉内容）", "shot_type": "远景/中景/近景/主观视角"}},
    {{"index": 1, "line": "诗句2", "scene": "场景描述", "shot_type": "远景/中景/近景/主观视角"}}
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
        print(f"整体规划结果：\n{json.dumps(plan, ensure_ascii=False, indent=2)}")
        return plan

    except Exception as e:
        print(f"整体规划失败，使用降级方案：{e}")
        return {
            "has_character": False,
            "character_desc": "",
            "recurring_elements": "",
            "frames": [
                {"index": i, "line": line, "scene": line, "shot_type": "中景"}
                for i, line in enumerate(poem_content)
            ]
        }


# ── 第二阶段：构建单张图的 Prompt ─────────────────────────────────────────────

def build_image_prompt(
    scene: str,
    shot_type: str,
    poem_title: str,
    dynasty: str,
    character_desc: str,
    has_character: bool,
    recurring_elements: str,
    prev_scene: str = "",
) -> str:
    character_part = ""
    if has_character and character_desc:
        character_part = (
            f"画面主角外貌必须严格固定为（{character_desc}），"
            f"人物风格为中国儿童绘本水彩插画，"
        )

    elements_part = ""
    if recurring_elements:
        elements_part = (
            f"本图若出现以下建筑/家具元素，样式必须与整组图保持一致：（{recurring_elements}），"
        )

    continuity_part = ""
    if prev_scene:
        continuity_part = f"承接上一画面（{prev_scene}），"

    shot_part = f"采用{shot_type}构图，" if shot_type else ""

    return (
        f"{dynasty}代古诗《{poem_title}》儿童插画，"
        f"{elements_part}"
        f"{continuity_part}"
        f"{shot_part}"
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
            "size": "2560x1440",
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
        image_url = (
            images[0].get("url", "")
            if images
            else result.get("data", {}).get("image", "")
        )

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
    """
    if not request.poem_content:
        return {"success": False, "error": "poem_content 不能为空"}

    print(f"\n《{request.poem_title}》开始生成，共 {len(request.poem_content)} 句")
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
    recurring_elements = plan.get("recurring_elements", "")
    planned_frames = plan.get("frames", [])

    print(f"有人物：{has_character}")
    print(f"人物形象：{character_desc}")
    print(f"固定建筑元素：{recurring_elements}")

    frames = []
    errors = []

    for i, frame_plan in enumerate(planned_frames):
        line = frame_plan.get(
            "line",
            request.poem_content[i] if i < len(request.poem_content) else ""
        )
        scene = frame_plan.get("scene", line)
        shot_type = frame_plan.get("shot_type", "中景")
        prev_scene = planned_frames[i - 1].get("scene", "") if i > 0 else ""

        print(f"\n── 第{i+1}句：{line} ──")
        print(f"镜头：{shot_type} | 场景：{scene}")

        prompt = build_image_prompt(
            scene=scene,
            shot_type=shot_type,
            poem_title=request.poem_title,
            dynasty=request.dynasty,
            character_desc=character_desc,
            has_character=has_character,
            recurring_elements=recurring_elements,
            prev_scene=prev_scene,
        )
        print(f"Prompt：{prompt}")

        result = call_image_api(prompt)

        if result["success"]:
            frames.append({
                "index": i,
                "line": line,
                "scene": scene,
                "shot_type": shot_type,
                "image_url": result["image_url"],
                "duration_ms": 3000,
            })
        else:
            errors.append({"index": i, "line": line, "error": result["error"]})
            print(f"第{i+1}句生成失败：{result['error']}")

    return {
        "success": len(frames) > 0,
        "poem_title": request.poem_title,
        "has_character": has_character,
        "character_desc": character_desc,
        "recurring_elements": recurring_elements,
        "total_lines": len(request.poem_content),
        "frames": frames,
        "errors": errors,
    }
