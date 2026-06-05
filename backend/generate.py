import json
import re
import os
import uuid
import time
import hashlib
from pathlib import Path
from typing import List

import requests
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

VIVO_APP_KEY = os.getenv("VIVO_APP_KEY")

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
IMAGES_DIR = STATIC_DIR / "images" / "poems"
CACHE_FILE = STATIC_DIR / "poem_images_cache.json"

IMAGES_DIR.mkdir(parents=True, exist_ok=True)


# ── 请求模型 ──────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    poem_id: str = ""
    poem_title: str = ""
    poem_content: List[str] = []
    poet_name: str = ""
    dynasty: str = ""
    tags: List[str] = []
    force_regenerate: bool = False   # 传 true 时跳过缓存强制重新生成


# ── 共享风格 ──────────────────────────────────────────────────────────────────

SHARED_STYLE = (
    "中国传统儿童绘本插画风格，水彩笔触，色彩柔和温润，"
    "人物造型圆润可爱，线条细腻流畅，背景层次丰富，"
    "整体氛围温暖治愈，国风古典美感，"
    "横版构图，适合手机横屏全屏展示，画面干净，无文字无水印"
)


# ── 缓存工具函数 ──────────────────────────────────────────────────────────────

def get_cache_key(poem_id: str, poem_title: str) -> str:
    """
    优先用 poem_id 作为缓存 key；没有 poem_id 时用诗名 md5 兜底。
    """
    if poem_id:
        return poem_id
    return hashlib.md5(poem_title.encode("utf-8")).hexdigest()


def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache: dict) -> None:
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"缓存写入失败（不影响功能）：{e}")


def download_image(url: str, save_path: Path) -> bool:
    """
    把外部图片 URL 下载到本地，返回是否成功。
    """
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(resp.content)
            return True
    except Exception as e:
        print(f"图片下载失败：{e}")
    return False


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

请严格按顺序完成以下任务，最终输出一个JSON。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【第一步：读懂全诗再动笔——诗意理解分析】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
在设计任何分镜之前，必须先完成以下理解工作并写入JSON：

1. 逐句准确翻译（translation）：用白话文准确翻译每一句，注意：
   - 区分实写（描写真实发生的场景/动作）和虚写（比喻/夸张/联想/感慨）
   - 实写句对应画面直接呈现该场景
   - 虚写句不能直接画字面内容，要找到能表达这种感受的视觉方式

2. 人物空间位置追踪（character_position）：全诗中人物（如有）在哪里、在做什么、位置如何变化
   - 这个追踪必须保证相邻两帧的人物位置不能无故跳变
   - 例如：李白全程在船上，汪伦全程在岸上，两者不能互换位置

3. 叙事弧线（narrative_arc）：一两句话说清这首诗在讲什么样的故事/情感历程

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【第二步：判断是否需要人物】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 有人物：诗句里有人物动作词（举头、低头、锄禾、独坐、遥望等）或第一人称视角
❌ 无人物：全诗只写自然景物、动物、植物

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【第三步：设计人物形象（有人物时必做）】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
推断依据：诗中明确描写的人物 > 诗人身份和朝代 > 情感基调
朝代服饰：唐（宽袍大袖）、宋（素雅简洁）、明（领高袖窄）

character_desc必须同时包含五项：
① 具体年龄数字 ② 性别 ③ 服装精确颜色+款式 ④ 发型细节 ⑤ 体型特征

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【第四步：判断整体场景环境】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
写入 scene_context（如"水边码头，无切换"/"室内为主，可向窗外看"）

户外一致性元素（outdoor_elements）：被描写主体的数量、水体颜色、背景远景，确定后保持一致。室内诗填空字符串。

室内反复出现的建筑元素（recurring_elements）：仅室内诗填写，床榻不得自行添加帐帷帘幔。户外诗填空字符串。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【第五步：基于诗意理解，设计每句诗的分镜场景】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【前提：必须基于第一步的理解来设计】
- 虚写句不能直接画字面内容
- 人物位置必须与第一步的空间位置追踪一致，不能无故跳变
- 每帧必须与叙事弧线的当前节点对应

【镜头类型语义定义——按内容选择，不能机械轮换】
远景：宏大场景，展示整体空间；⚠️ 远景时若有人物，人物高度不得超过画面总高度的10%
中景：人物动作与周围环境的互动，人物与环境各占一半重要性
近景：聚焦人物细腻情感或局部动作
特写：极度放大局部细节（仅咏物诗）
主观视角：第一人称展示视线所见景色，画面中不出现视角主人公自身（脸/手/身体），场景中本来存在的其他人物和事物可以正常出现

❌ 禁止为凑类型多样性而选错镜头；内容适合性绝对优先

【人物站位与双手规则——极其重要】
每张图必须写明：人物具体位置 + 双手位置和姿态
⚠️ 人物只有两只手两条手臂，不得让人物同时做需要三只以上手的动作
⚠️ 人物位置必须与上一帧的位置衔接合理（在船上的人不能突然跳到岸上）

【scene描述质量规则】
✅ 只包含诗句中明确出现的元素或场景逻辑必然存在的背景
❌ 禁止添加诗中没有的装饰性元素
❌ 虚写句中的比喻/夸张不画成实体

【诗意词汇语义纠正】
- "生紫烟"：山间升腾的紫色雾气，山体本身不是紫色
- "疑是银河落九天"：壮阔瀑布的比喻，画瀑布本身
- "疑是地上霜"：室内不画真实霜晶，用月光将地板映成冷白色

【情绪外化规则】
疑惑/怀疑类（真实把甲误认为乙）：头顶飘大问号"？"
❌ 感叹性诗句禁止用问号，改用"！"或场景色调
劳动者感慨/反思：保持劳动姿态，头部旁飘思维气泡内含感慨事物
思念/乡愁类：白色半透明云朵气泡，内画所思念的具体场景（注意气泡内容要与所思念的人/地相关，而非泛泛的欢乐场面）
悲伤/忧愁类：眼角小泪珠，色调偏冷蓝
喜悦类：嘴角上扬，眼神明亮；户外可加蝴蝶/花瓣，室内只用表情
❌ "若有所思/表情柔和悠远"等无法具体画出的描述一律禁止
❌ 人物脸上出汗仅用于劳动/热天场景，不用于感动/情感场景

场景描述控制在65字以内，全部是可以直接画出来的具体视觉内容。

━━━━━━━━━━━━━━━━━━━━━━━
严格按照以下JSON格式输出，不要有任何额外文字：
{{
  "narrative_arc": "一两句话描述全诗的故事/情感历程",
  "line_analysis": [
    {{"line": "诗句1", "translation": "准确白话翻译", "writing_type": "实写或虚写", "character_position": "此时人物在哪里在做什么（无人物则填空）"}},
    {{"line": "诗句2", "translation": "...", "writing_type": "...", "character_position": "..."}}
  ],
  "has_character": true或false,
  "character_desc": "五项完整人物描述（无人物则为空字符串）",
  "scene_context": "整体场景环境描述",
  "outdoor_elements": "户外一致性约束，室内诗填空字符串",
  "recurring_elements": "室内建筑/家具样式，户外诗填空字符串",
  "frames": [
    {{"index": 0, "line": "诗句1", "scene": "场景描述（含人物具体位置+双手姿态+情绪外化+视觉内容）", "shot_type": "远景/中景/近景/特写/主观视角"}},
    {{"index": 1, "line": "诗句2", "scene": "场景描述", "shot_type": "远景/中景/近景/特写/主观视角"}}
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
        content = re.sub(r"```json|```", "", content).strip()
        plan = json.loads(content)
        print(f"整体规划结果：\n{json.dumps(plan, ensure_ascii=False, indent=2)}")
        return plan

    except Exception as e:
        print(f"整体规划失败，使用降级方案：{e}")
        return {
            "has_character": False,
            "character_desc": "",
            "scene_context": "",
            "outdoor_elements": "",
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
    outdoor_elements: str = "",
    prev_scene: str = "",
) -> str:
    # 远景特殊约束：人物渺小，不得与山等高
    scale_constraint = ""
    if shot_type == "远景" and has_character:
        scale_constraint = (
            "此帧为远景，人物在画面中极其渺小（高度不超过画面总高度的10%），"
            "画面主体是宏大的自然环境或建筑景观，人物只是其中一个微小的点缀，"
        )

    # 人体解剖约束（加入character_part）
    character_part = ""
    if has_character and character_desc:
        character_part = (
            f"画面主角外貌在整组图中完全固定，本图必须严格遵守以下描述不得偏离：（{character_desc}），"
            f"发型性别服装颜色绝对不可改变，人物只有两只手两条手臂（解剖正确），"
            f"人物风格为中国儿童绘本水彩插画，"
        )

    # 室内元素约束（仅室内诗填写）
    elements_part = ""
    if recurring_elements:
        elements_part = (
            f"以下室内建筑/家具元素若出现在本图中，样式必须与整组图保持一致：（{recurring_elements}）；"
            f"这些元素属于室内空间，窗外庭院、室外地面、天空等区域严禁出现这些室内元素，"
            f"床榻周围不得出现说明中未提及的帐帷、帘幔、蚊帐或任何悬挂布料，"
        )

    # 户外一致性约束（仅户外诗填写）
    outdoor_part = ""
    if outdoor_elements:
        outdoor_part = (
            f"整组图为户外场景，以下自然元素在整组图中必须保持一致：（{outdoor_elements}）；"
            f"禁止在任何一帧出现室内家具（床榻、桌椅等），"
        )

    # 主观视角约束（区分室内/户外，只限制视角主人公自身，不禁止场景中应有的其他人）
    shot_exclusion = ""
    if shot_type == "主观视角":
        if recurring_elements:
            # 室内诗：摄像机在室内，家具在镜头后方
            shot_exclusion = (
                "本图为第一人称主观视角，展示人物视线方向所见的景色，"
                "画面中不出现视角主人公自身（脸、手、身体）；"
                "室内家具在镜头后方，不出现在画面中；"
            )
        else:
            # 户外诗：只展示所见景色，不添加任何室内元素
            shot_exclusion = (
                "本图为第一人称主观视角，展示人物视线方向所见的景色，"
                "画面中不出现视角主人公自身（脸、手、身体）；"
                "场景中本来存在的其他人物、建筑、自然景物可以正常出现；"
                "不添加任何室内元素（窗框、家具等）；"
            )

    # 情节连贯（户外诗不加室内警告）
    continuity_part = ""
    if prev_scene:
        indoor_warning = "室外的动物和植物必须处于窗外空间不得进入室内，" if recurring_elements else ""
        continuity_part = (
            f"与上一画面情节连贯（上一幕场景：{prev_scene}）；"
            f"注意：上一幕中的生物、植物、装饰物不会自动出现在本画面，"
            f"本画面严格按当前场景描述独立绘制，{indoor_warning}"
        )

    shot_part = f"采用{shot_type}构图，" if shot_type else ""

    return (
        f"{dynasty}代古诗《{poem_title}》儿童插画，"
        f"{elements_part}"
        f"{outdoor_part}"
        f"{shot_exclusion}"
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
    为古诗每句话生成一张横版配图。
    已生成过的诗直接返回本地缓存，不重复调用模型。
    """
    if not request.poem_content:
        return {"success": False, "error": "poem_content 不能为空"}

    # ── 命中缓存：直接返回，不调模型 ──────────────────────────────────────────
    cache_key = get_cache_key(request.poem_id, request.poem_title)
    cache = load_cache()

    if cache_key in cache and not request.force_regenerate:
        print(f"《{request.poem_title}》命中缓存，直接返回")
        cached = cache[cache_key]
        cached["from_cache"] = True
        return cached

    # ── 未命中缓存：正常生成流程 ──────────────────────────────────────────────
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
    outdoor_elements = plan.get("outdoor_elements", "")
    planned_frames = plan.get("frames", [])

    print(f"有人物：{has_character}")
    print(f"人物形象：{character_desc}")
    print(f"整体场景：{plan.get('scene_context', '')}")
    print(f"户外一致性元素：{outdoor_elements}")
    print(f"固定室内建筑元素：{recurring_elements}")

    frames = []
    errors = []

    # 为这首诗创建本地图片目录
    poem_img_dir = IMAGES_DIR / cache_key
    poem_img_dir.mkdir(parents=True, exist_ok=True)

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
            outdoor_elements=outdoor_elements,
            prev_scene=prev_scene,
        )
        print(f"Prompt：{prompt}")

        result = call_image_api(prompt)

        if result["success"]:
            # 把外部 URL 的图片下载到本地，避免外部链接过期
            local_filename = f"frame_{i}.jpg"
            local_path = poem_img_dir / local_filename
            local_url = f"/static/images/poems/{cache_key}/{local_filename}"

            if download_image(result["image_url"], local_path):
                image_url = local_url
                print(f"第{i+1}句图片已保存到本地：{local_url}")
            else:
                # 下载失败则暂时用外部 URL，不阻断流程
                image_url = result["image_url"]
                print(f"第{i+1}句图片下载失败，使用外部URL")

            frames.append({
                "index": i,
                "line": line,
                "scene": scene,
                "shot_type": shot_type,
                "image_url": image_url,
                "duration_ms": 3000,
            })
        else:
            errors.append({"index": i, "line": line, "error": result["error"]})
            print(f"第{i+1}句生成失败：{result['error']}")

    # ── 兜底：全部失败时返回明确错误，不让前端空白 ────────────────────────────
    if not frames:
        return {
            "success": False,
            "error": "所有诗句配图均生成失败，请检查 API 配置或稍后重试",
            "poem_title": request.poem_title,
            "frames": [],
            "errors": errors,
        }

    # ── 写入缓存 ───────────────────────────────────────────────────────────────
    result_data = {
        "success": True,
        "poem_title": request.poem_title,
        "has_character": has_character,
        "character_desc": character_desc,
        "recurring_elements": recurring_elements,
        "total_lines": len(request.poem_content),
        "frames": frames,
        "errors": errors,
        "from_cache": False,
    }

    if cache_key:
        cache[cache_key] = result_data
        save_cache(cache)
        print(f"《{request.poem_title}》已写入缓存，key={cache_key}")

    return result_data


# ══════════════════════════════════════════════════════════════════════════════
# 诗人形象生成接口
# ══════════════════════════════════════════════════════════════════════════════

POETS_DIR = STATIC_DIR / "images" / "poets"
POETS_DIR.mkdir(parents=True, exist_ok=True)
POETS_CACHE_FILE = STATIC_DIR / "poets_cache.json"

POET_PROFILES = {
    "李白": {
        "desc": "约45岁，男性，身着白色宽袖道袍系青色腰带，腰间挂酒葫芦，黑色长发半披散用白色布带随意束起，面容英俊棱角分明，中等偏高身材体格健壮",
        "personality": "豪迈不羁、浪漫飘逸，眼神飞扬自信带着几分醉意，嘴角上扬，姿态潇洒，气质如谪仙临世",
    },
    "杜甫": {
        "desc": "约52岁，男性，身着深灰色粗布交领长衫系深棕色布腰带，黑发夹杂白丝以木簪束于头顶，面容清瘦沧桑，中等身材略显佝偻",
        "personality": "忧国忧民、沉郁顿挫，双眉紧锁，眼神深沉悲悯，神情凝重，气质厚重如大地",
    },
    "苏轼": {
        "desc": "约45岁，男性，身着深蓝色宽袖长衫系棕色腰带，头戴东坡巾，黑色短须，面容圆润丰满，体型略微丰腴，手持折扇",
        "personality": "旷达乐观、幽默豁达，嘴角常带温和笑意，眼神睿智而温暖，举止从容洒脱",
    },
    "白居易": {
        "desc": "约58岁，男性，身着素白交领长衫系棕色布腰带，头发灰白以木簪简单束起，面容慈祥圆润，中等身材略显发福，手持书卷",
        "personality": "平易近人、温厚慈祥，眼神亲切温和，面带慈父般微笑，气质朴实无华",
    },
    "王维": {
        "desc": "约40岁，男性，身着淡青色素雅交领长衫系米色腰带，黑色长发以竹簪整齐束于头顶，面容清秀白皙，中等身材清瘦",
        "personality": "禅意淡泊、静谧悠远，眼神深邃平静，面带淡淡微笑，气质超然如入定的禅者",
    },
}


class PoetAvatarRequest(BaseModel):
    poet_name: str
    dynasty: str = "唐"


def call_image_api_portrait(prompt: str) -> dict:
    """专用于诗人形象生成，使用竖版尺寸（接近225:270 = 5:6比例）"""
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
            "size": "1024x1280",   # 竖版 4:5，接近前端展示尺寸225×270（5:6），前端等比例缩小即可
        },
    }

    try:
        response = requests.post(url, json=data, headers=headers, params=params, timeout=60)
        result = response.json()

        if result.get("code") != 0:
            return {"success": False, "error": result.get("message", "图像生成失败"), "image_url": ""}

        images = result.get("data", {}).get("images", [])
        image_url = images[0].get("url", "") if images else result.get("data", {}).get("image", "")

        if not image_url:
            return {"success": False, "error": "返回图片URL为空", "image_url": ""}

        return {"success": True, "image_url": image_url, "error": ""}

    except requests.exceptions.Timeout:
        return {"success": False, "error": "图像生成超时，请重试", "image_url": ""}
    except Exception as e:
        return {"success": False, "error": str(e), "image_url": ""}
    if POETS_CACHE_FILE.exists():
        try:
            with open(POETS_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_poets_cache(cache: dict) -> None:
    try:
        with open(POETS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"诗人缓存写入失败：{e}")


def build_poet_avatar_prompt(poet_name: str, dynasty: str, profile: dict) -> str:
    desc = profile.get("desc", f"约40岁，男性，{dynasty}代文人长衫，黑色发髻束于头顶，面容温和，中等身材")
    personality = profile.get("personality", "温文尔雅，神态亲切，气质儒雅")
    return (
        f"{dynasty}代著名诗人{poet_name}的人物肖像儿童插画，"
        f"人物外貌严格遵守：{desc}，"
        f"神态气质：{personality}，"
        f"人物正面朝向观者，站立半身像，居于画面中央，"
        f"背景简洁，以与诗人气质相符的淡色调渐变为主，不喧宾夺主，"
        f"中国传统儿童绘本插画风格，水彩笔触，色彩柔和温润，"
        f"人物造型圆润可爱但保留成人气质，线条细腻，"
        f"整体氛围温暖亲切，国风古典美感，画面干净，无文字无水印"
    )


@router.post("/generate/poet_avatar")
def generate_poet_avatar(request: PoetAvatarRequest):
    """
    生成诗人人物形象插画，进入诗词详情页时调用。
    同一诗人只生成一次，之后命中缓存秒回。
    """
    poet_name = request.poet_name.strip()
    if not poet_name:
        return {"success": False, "error": "poet_name 不能为空"}

    cache = load_poets_cache()
    if poet_name in cache:
        print(f"{poet_name}诗人形象命中缓存，直接返回")
        cached = cache[poet_name]
        cached["from_cache"] = True
        return cached

    profile = POET_PROFILES.get(
        poet_name,
        {
            "desc": f"约40岁，男性，{request.dynasty}代文人长衫，黑色发髻束于头顶，面容温和有学问，中等身材",
            "personality": "温文尔雅，神态亲切，气质儒雅",
        }
    )

    print(f"开始生成{poet_name}的诗人形象")
    prompt = build_poet_avatar_prompt(poet_name, request.dynasty, profile)
    print(f"Prompt：{prompt}")

    result = call_image_api_portrait(prompt)
    if not result["success"]:
        return {"success": False, "error": result["error"], "poet_name": poet_name}

    local_filename = f"{poet_name}.jpg"
    local_path = POETS_DIR / local_filename
    local_url = f"/static/images/poets/{local_filename}"

    if download_image(result["image_url"], local_path):
        avatar_url = local_url
        print(f"{poet_name}形象已保存到本地：{local_url}")
    else:
        avatar_url = result["image_url"]

    response_data = {
        "success": True,
        "from_cache": False,
        "poet_name": poet_name,
        "dynasty": request.dynasty,
        "avatar_url": avatar_url,
    }

    cache[poet_name] = response_data
    save_poets_cache(cache)
    print(f"{poet_name}诗人形象已写入缓存")

    return response_data
