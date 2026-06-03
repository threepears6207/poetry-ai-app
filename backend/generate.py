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
【任务三：锁定整首诗的整体场景环境——极其重要】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
在设计任何分镜之前，先判断这首诗的整体发生环境，ALL帧必须符合这个环境：

判断规则：
- 田野农耕类（如悯农）→ scene_context = "田野户外"，所有帧在田间，禁止出现室内
- 咏物自然类（如咏鹅）→ scene_context = "池塘水边户外"，所有帧在池塘边，禁止出现室内
- 思乡羁旅类（如静夜思）→ scene_context = "室内卧室"，可向窗外看
- 登高览景类（如登鹳雀楼）→ scene_context = "楼台户外"，所有帧在户外
- 只有诗中有明确的场景切换描写，才允许不同帧有不同的大环境

自然元素一致性锁定（outdoor_elements）：
- 咏物诗中被描写动物的数量：第一帧出现几只就锁定几只，后续帧数量必须一致
- 水体特征：颜色（绿色/碧蓝）、大小（小池塘/大湖）锁定后保持一致
- 背景远景：第一帧确定的背景元素（柳树/山脉/村庄）后续帧可见时必须保持一致
- outdoor_elements 字段写入这些一致性约束，格式如："绿色池塘（荷叶点缀）；三只白鹅（固定数量）；远处柳树"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【任务四：确定反复出现的室内建筑元素样式（仅室内诗适用）】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
仅当 scene_context 含有"室内"时才填写 recurring_elements，否则填空字符串。

严格限制：
- 只能描述诗句场景中实际需要的家具
- 床榻描述中若未提及帐帷帘幔，整组图中严禁出现任何帐帷、床帘、悬挂布料
- 已定义的样式就是唯一正确样式，不得自行添加装饰
- 户外诗 recurring_elements 必须填空字符串""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【任务五：设计每句诗的分镜场景】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【镜头变化规则】
相邻两句镜头类型必须不同

当 has_character=false（咏物诗）时，可用镜头类型：远景 / 中景 / 近景 / 特写
- 禁止使用"主观视角"
- "特写"：极近距离聚焦动物/植物局部（如鹅颈弯曲特写、鹅掌划水特写），背景为模糊的户外环境

当 has_character=true 时，可用镜头类型：远景 / 中景 / 近景 / 主观视角
- 主观视角：以人物眼睛为镜头，画面中完全不出现主角正面或身体，只显示其视线所及的场景；此镜头下室内所有家具均在镜头背后不得出现在画面中；场景描述中必须注明"本帧为主观视角，室内家具均在镜头背后不出现在画面中"

【整体场景一致性规则——极其重要】
每一帧的 scene 描述必须符合 scene_context 定义的整体环境：
- 户外场景：禁止在任何一帧出现室内元素（窗框、床、桌椅等）
- 每一帧中出现的自然元素必须与 outdoor_elements 中定义的一致（数量、颜色、样式）

【人物站位规则——极其重要】
每张图必须同时写明：
1. 人物在空间中的具体位置
2. 双手位置
❌ 禁止只写姿态不写位置

【情绪外化规则——重要】
抽象情绪和心理活动必须转化为可见的视觉符号：

疑惑/怀疑类（如"疑是"——真实地把甲误认为乙）：
✅ 人物头顶右上方飘着手绘风格大问号"？"，眉头微皱，头略歪
❌ 严禁用问号的情况：以"知多少""几何""何处""几时""多少"结尾的感叹性诗句，禁止使用问号；改用叹号"！"或通过场景色调表达

劳动者在田间产生感慨/反思（如"谁知盘中餐"）——特殊规则：
✅ 人物仍在田间劳动，双手握锄弯腰，头部旁有白色半透明云朵气泡，气泡内画出被感慨的事物（如冒热气的白米饭碗）；禁止切换到室内主观视角

思念/乡愁类：
✅ 人物头部旁有白色半透明云朵气泡，气泡内画出故乡场景（茅草屋、炊烟、家人剪影）

悲伤/忧愁类：
✅ 眼角有小水滴泪珠，背景色调偏冷蓝

喜悦类：
✅ 嘴角上扬露齿，背景有蝴蝶或花瓣飘落

【光线描述规则】
只描述光照射在什么物体上呈现什么颜色，不描述光的几何形状

场景描述控制在65字以内，全部是可以直接画出来的具体视觉内容。

━━━━━━━━━━━━━━━━━━━━━━━
严格按照以下JSON格式输出，不要有任何额外文字：
{{
  "has_character": true或false,
  "character_desc": "五项完整人物描述（无人物则为空字符串）",
  "scene_context": "整体场景环境（如田野户外/池塘水边户外/室内卧室）",
  "outdoor_elements": "户外一致性约束（如绿色池塘；三只白鹅；远处柳树），室内诗填空字符串",
  "recurring_elements": "室内建筑/家具样式（仅室内诗填写，户外诗填空字符串）",
  "frames": [
    {{"index": 0, "line": "诗句1", "scene": "场景描述", "shot_type": "远景/中景/近景/特写/主观视角"}},
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
    character_part = ""
    if has_character and character_desc:
        character_part = (
            f"画面主角外貌在整组图中完全固定，本图必须严格遵守以下描述不得偏离：（{character_desc}），"
            f"发型性别服装颜色绝对不可改变，人物风格为中国儿童绘本水彩插画，"
        )

    # 室内元素约束（仅室内诗有值）
    elements_part = ""
    if recurring_elements:
        elements_part = (
            f"以下室内建筑/家具元素若出现在本图中，样式必须与整组图保持一致：（{recurring_elements}）；"
            f"这些元素属于室内空间，窗外庭院、室外地面、天空等区域严禁出现这些室内元素，"
            f"床榻周围不得出现说明中未提及的帐帷、帘幔、蚊帐或任何悬挂布料，"
        )

    # 户外一致性约束（仅户外诗有值）
    outdoor_part = ""
    if outdoor_elements:
        outdoor_part = (
            f"整组图为户外场景，以下自然元素在整组图中必须保持一致：（{outdoor_elements}）；"
            f"禁止在任何一帧出现室内元素（窗框、床榻、桌椅等），"
        )

    # 主观视角：室内家具不可见（仅 has_character=True 时才会有主观视角）
    shot_exclusion = ""
    if shot_type == "主观视角" and has_character:
        shot_exclusion = (
            "本图为主观视角镜头，摄像机位于室内朝外望，"
            "室内所有家具均在镜头背后不在画面视野范围内，"
            "画面中只显示窗框边缘和窗外景物，严禁在画面任何位置放置室内家具，"
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

# 五位主要诗人：形象描述 + 性格气质（结合生平）
POET_PROFILES = {
    "李白": {
        "desc": (
            "约45岁，男性，身着白色宽袖道袍系青色腰带（受道教影响爱着道袍），"
            "腰间挂一只酒葫芦，黑色长发半披散用白色布带随意束起，"
            "面容英俊棱角分明，中等偏高身材，体格健壮（少年习剑）"
        ),
        "personality": (
            "豪迈不羁、浪漫飘逸，眼神飞扬自信带着几分醉意，嘴角上扬，"
            "姿态潇洒随意，仿佛随时要仰头大笑，气质如谪仙临世"
        ),
    },
    "杜甫": {
        "desc": (
            "约52岁，男性，身着深灰色粗布交领长衫系深棕色布腰带，"
            "黑发夹杂白丝以木簪束于头顶，面容清瘦沧桑布满风霜，"
            "中等身材略显佝偻（晚年多病）"
        ),
        "personality": (
            "忧国忧民、沉郁顿挫，双眉紧锁，眼神深沉悲悯，"
            "神情专注凝重，仿佛心中装着天下苍生之苦，气质厚重如大地"
        ),
    },
    "苏轼": {
        "desc": (
            "约45岁，男性，身着深蓝色宽袖长衫系棕色腰带，"
            "头戴东坡巾（特有的方形软帽），黑色短须，面容圆润丰满，"
            "体型略微丰腴，手持折扇"
        ),
        "personality": (
            "旷达乐观、幽默豁达，嘴角常带温和笑意，眼神睿智而温暖，"
            "举手投足间透着从容洒脱，仿佛任何困境都能一笑而过"
        ),
    },
    "白居易": {
        "desc": (
            "约58岁，男性，身着素白交领长衫系棕色布腰带，"
            "头发灰白以木簪简单束起，面容慈祥圆润，"
            "中等身材略显发福，手持书卷"
        ),
        "personality": (
            "平易近人、温厚慈祥，眼神亲切温和，面带慈父般的微笑，"
            "气质朴实无华，仿佛邻家长辈，让人一见便感到亲近安心"
        ),
    },
    "王维": {
        "desc": (
            "约40岁，男性，身着淡青色素雅交领长衫系米色腰带，"
            "黑色长发以竹簪整齐束于头顶，面容清秀白皙，"
            "中等身材清瘦（长期修行）"
        ),
        "personality": (
            "禅意淡泊、静谧悠远，眼神深邃平静如古井，面带淡淡微笑，"
            "气质超然如入定的禅者，举止轻缓优雅，仿佛与山水融为一体"
        ),
    },
}


class PoetAvatarRequest(BaseModel):
    poet_name: str
    dynasty: str = "唐"


def load_poets_cache() -> dict:
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
    desc = profile.get("desc", f"约40岁，男性，{dynasty}代文人，中等身材，面容温和")
    personality = profile.get("personality", "温和有学问，神态亲切")
    return (
        f"{dynasty}代著名诗人{poet_name}的人物肖像儿童插画，"
        f"人物外貌严格遵守：{desc}，"
        f"神态气质：{personality}，"
        f"人物居于画面中央偏右，四分之三侧面半身像，"
        f"背景为与诗人风格相符的简洁场景"
        f"（李白配月下山崖/酒壶，杜甫配战乱后的茅屋，苏轼配赤壁江景，白居易配书房，王维配山林禅境），"
        f"中国传统儿童绘本插画风格，水彩笔触，色彩柔和温润，"
        f"人物造型圆润可爱但保留成人气质，线条细腻，"
        f"整体氛围温暖亲切，国风古典美感，画面干净，无文字无水印"
    )


@router.post("/generate/poet_avatar")
def generate_poet_avatar(request: PoetAvatarRequest):
    """
    生成诗人人物形象插画，进入诗词详情页时调用。
    同一诗人只生成一次，之后命中缓存秒回。

    请求示例：{"poet_name": "李白", "dynasty": "唐"}
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

    result = call_image_api(prompt)

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
